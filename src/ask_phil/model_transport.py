"""Cancellable HTTP to declared model resources; no redirects, proxies or retries."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionStopped, current_execution


class ModelTransport(httpx.BaseTransport):
    """Bridge synchronous model SDKs to cancellable, deadline-bound network I/O.

    Only the configured origin and exact method/path pairs are available. A
    request deadline covers connection, headers and the entire response body,
    including a peer that keeps sending bytes just before each read timeout.
    """

    def __init__(self, base_url: str, resources: tuple[tuple[str, str], ...]) -> None:
        self.origin = httpx.URL(base_url)
        self.resources = frozenset(resources)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        budget = current_execution.get() or ExecutionBudget(ExecutionLimits())
        if (
            (request.url.scheme, request.url.host, request.url.port)
            != (self.origin.scheme, self.origin.host, self.origin.port)
            or request.url.username
            or request.url.password
            or request.url.query
            or (request.method, request.url.path) not in self.resources
        ):
            budget.stop("endpoint_denied")
        budget.http_call()
        if len(request.content) > 16000:
            budget.stop("input_limit")
        try:
            return asyncio.run(self._request(request, budget))
        except ExecutionStopped:
            raise
        except httpx.TimeoutException:
            budget.stop("timeout")
        except (httpx.HTTPError, OSError, ValueError):
            budget.stop("provider_failure")
        raise AssertionError("Unreachable")

    async def _request(self, request: httpx.Request, budget: ExecutionBudget) -> httpx.Response:
        async with self._cancellation(budget):
            async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                # Recreate a replayable non-streaming SDK request. No key is ever logged here.
                outgoing = httpx.Request(
                    request.method,
                    request.url,
                    headers=request.headers,
                    content=request.content,
                    extensions=request.extensions,
                )
                response = await client.send(outgoing, stream=True)
                try:
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > 262144:
                            budget.stop("malformed_output")
                    return httpx.Response(
                        response.status_code,
                        headers=[
                            (name, value)
                            for name, value in response.headers.multi_items()
                            if name.lower() not in {"content-encoding", "content-length"}
                        ],
                        content=bytes(chunks),
                        extensions=response.extensions,
                    )
                finally:
                    await response.aclose()

    @asynccontextmanager
    async def _cancellation(self, budget: ExecutionBudget) -> AsyncIterator[None]:
        task = asyncio.current_task()
        assert task is not None

        async def watch() -> None:
            while not budget.cancellation.is_set():
                await asyncio.sleep(0.02)
            task.cancel()

        watcher = asyncio.create_task(watch())
        try:
            async with asyncio.timeout(budget.remaining_seconds):
                yield
        except TimeoutError:
            budget.stop("timeout")
        except asyncio.CancelledError:
            budget.stop("cancelled")
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)


def local_transport(base_url: str) -> ModelTransport:
    return ModelTransport(
        base_url, (("GET", "/api/tags"), ("POST", "/api/embed"), ("POST", "/api/chat"))
    )


def cloud_transport(model: str) -> ModelTransport:
    return ModelTransport(
        "https://openrouter.ai",
        (
            ("GET", "/api/v1/key"),
            ("GET", f"/api/v1/models/{model}/endpoints"),
            ("POST", "/api/v1/chat/completions"),
        ),
    )
