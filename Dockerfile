FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY src ./src
COPY data ./data
COPY config ./config
COPY scripts/evaluate_text_baseline.py scripts/evaluate_answer_policy.py scripts/evaluate_text_corpus.py scripts/evaluate_conversation.py ./scripts/
RUN uv sync --frozen --no-dev --no-editable --cache-dir /tmp/uv-cache
RUN mkdir -p /app/artifacts && chown 10001:10001 /app/artifacts
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV MLFLOW_DISABLE_AGENT_HINT=1
ENV PREFECT_HOME=/app/artifacts/prefect
USER 10001:10001
CMD ["uvicorn", "ask_phil.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test
USER root
RUN uv sync --frozen --no-editable --cache-dir /tmp/uv-cache
COPY tests ./tests
COPY docs/implementation/issue-3/docker-serving.json ./docs/implementation/issue-3/docker-serving.json
COPY scripts/record_family_acceptance.py scripts/record_relationship_acceptance.py scripts/record_event_acceptance.py ./scripts/
COPY docs/implementation/issue-11/claims.json docs/implementation/issue-11/claim-reviews.json ./docs/implementation/issue-11/
COPY docs/implementation/issue-12/raw-claims.json docs/implementation/issue-12/raw-claim-reviews.json docs/implementation/issue-12/reviewed-claims-v2.json docs/implementation/issue-12/reviewed-claim-reviews-v2.json ./docs/implementation/issue-12/
COPY docs/implementation/issue-13/raw-claims.json docs/implementation/issue-13/raw-reviews.json docs/implementation/issue-13/reviewed-claims-v2.json docs/implementation/issue-13/reviewed-reviews-v2.json ./docs/implementation/issue-13/
COPY docs/implementation/issue-16/claim-reviews.json ./docs/implementation/issue-16/
USER 10001:10001
CMD ["pytest", "-q", "-p", "no:cacheprovider"]

FROM base AS runtime
