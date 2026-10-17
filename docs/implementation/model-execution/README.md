# Model execution and accounting

This user-directed architecture change deepens model execution and accounting,
and fixes answer receipts waiting for an unrelated source refresh writer.

## Model execution

`Models.generate_answer` returns one immutable `ModelExecution` containing answer
content, observed token usage, optional provider accounting, safe failure type,
estimated inference cost, cost scope and model limitations. The model module owns
the Ollama counter names and OpenRouter accounting interpretation, including
provider failures after a budget reservation or reported charge. Trace attributes
come from that same result so traces and saved responses use the same measurements.

`Models.skipped_answer` records zero answer tokens and no provider call accounting.
It retains observed query-embedding usage without reusing a prior answer's charge
or token counts. Missing provider measurements remain unknown rather than zero.

Answer execution retains source-supported fact, persona, outcome and citation
rules. It validates the model's draft against its captured context and preserves
measured costs when unusable JSON or invalid citations turn a completed model call
into a failed answer. Receipt fields and historical response defaults retain their
existing values. `TokenUsage` remains importable from `ask_phil.answers`.

The existing Ollama and OpenRouter adapters remain the two concrete model
implementations. OpenRouter's returned accounting no longer imitates Ollama
counter names. Credential checks, the shared persistent trial budget, conservative
reservations and the no-retry policy remain in its adapter.

## Receipt persistence during refresh

Source refresh and recovery retain session advisory lock `728194`. Receipt-table
creation and writes use transaction advisory lock `728195`, so simultaneous first
receipts remain serialized without waiting for source capture or indexing.

The regression holds the real refresh writer open while two concurrent conversation
requests produce and resolve private receipts. It starts with an empty receipt
table and asserts both responses return before the refresh writer is released.

## Verification

Tests use the already-confirmed conversation, source-refresh and external provider
HTTP seams from [the testing strategy](../../design/testing-and-evaluation.md).
PostgreSQL/pgvector and MLflow are real; controlled HTTP responses replace external
models. The provider cases cover successful calls, transport failure, truncated
output, invalid JSON, missing usage, and skipped inference following an earlier
charged call. These checks require no paid model calls.

On 17 October 2026 the full suite passed **153 tests**, with zero failures, errors
or skips, in 238.53 seconds using Python 3.12.3 and the local PostgreSQL/pgvector
container. The existing Starlette/httpx test-client deprecation is the only warning.
Strict mypy passes for all 41 source files, Ruff passes, and the staged-tree secret
scan passes. The public HTTP, answer-record and draft schemas and system prompt
exactly match starting revision `bf4334a`.

The receipt regression first failed with a 15-second timeout while the refresh
writer held its lock, then passed with the independent receipt lock. Targeted
answer-interface and provider-accounting checks also passed before the final run.
Set `ASK_PHIL_TEST_DATABASE_URL` to a disposable PostgreSQL admin connection and
run `.venv/bin/pytest -q -p no:cacheprovider` to reproduce the suite.

## Standards

Independent review of the staged implementation against `bf4334a` found zero
documented-standard violations or actionable baseline smells, and no ADR conflicts.

## Spec

Independent review against the selected architecture candidate, receipt-lock fix
and existing conversation/refresh requirements found zero missing requirements,
unasked behavior or incorrect implementations.

Total findings: Standards 0; Spec 0. Neither axis has an unresolved issue.
