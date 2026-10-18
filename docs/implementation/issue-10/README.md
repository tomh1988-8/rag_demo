# Issue #10: bounded read-only execution

Implements [issue #10](https://github.com/tomh1988-8/rag_demo/issues/10) from
starting revision `f1ecc315eeb5e9a14843d6f56c401882b3250cde`. The confirmed
conversation, retrieval, bounded-execution and evaluation seams are reused.

Answering has one declared retrieval capability, fixed parameterized SQL and
read-only PostgreSQL retrieval connections. Source loading, refresh and indexing
remain maintainer operations. Models receive data and an output schema, without
an action dispatcher, SQL executor, shell or browser. Hostile passages cannot
change these capabilities. Invalid vectors, changed/unknown/duplicate evidence,
invalid citations and model action requests fail outside the prompt.

Production model clients use a transport restricted to their configured origin
and exact method/path pairs. Local access permits only model listing, embedding
and chat; OpenRouter permits key-limit verification, the configured model's
endpoint metadata and chat. Redirects, environment proxies and automatic retries
are disabled. Untrusted questions or passages cannot select another resource.

## Limits and cancellation

`ASK_PHIL_EXECUTION_POLICY` optionally selects a strict JSON `ExecutionPolicies`
document. Omitted settings retain finite defaults; unknown fields, write
capabilities, nonfinite values and nonzero retry settings are rejected.

| Control | Serving | Offline evaluation | Online evaluation |
| --- | --- | --- | --- |
| Admitted model attempts | 2 | 2 | 1 |
| Retrieval tools | 1 | 1 | 0 |
| Model HTTP requests, including metadata | 8 | 8 | 8 |
| Execution seconds | 180 | 180 | 30 |
| Request spending ceiling | $0.15 | $0.15 | $0.15 |
| Concurrent requests per service/judge instance | 4 | 1 | 1 |
| Automatic retries | 0 | 0 | 0 |
| Whole-passage context bytes | 1,200 | 1,200 | No retrieval |

Serving's two model attempts include the query embedding. A call is counted when
admitted, even if provider preflight subsequently fails. The HTTP count describes
actual transport attempts, including metadata. Provider accounting identifies
paid inference reservations separately. Trusted test transports substitute the
external boundary; the real HTTP tests exercise the production transport.

The transport limits each request to 16,000 bytes, decoded responses to 262,144
bytes, and model content retained for validation to 32,768 bytes. Draft/citation
schemas impose tighter answer limits. Judge data is at most 12,000 bytes and 20
passages. The configured provider output-token limit remains in force.

The monotonic deadline covers model verification, retrieval and generation. Each
network operation covers its entire response, including a slowly streamed body.
HTTP disconnect and explicit `ExecutionBudget` cancellation close active model
connections and prevent subsequent calls. Supported excerpts remain available
with citations on limit/cancellation outcomes; the recorded reason distinguishes
limits from missing evidence. Provider/malformed-output failures remain failed
answers with safe messages and retained context where available.

Database connection attempts have a five-second timeout; snapshot/vector reads
also have query/lock timeouts of at most five seconds, reduced to the remaining
request time. Conversation writes have finite query/lock timeouts. Deterministic
receipt finalization has a separate five-second query/lock window.
Shared spending-ledger waits/queries are also bounded to five seconds or the
remaining execution time, with cancellation-aware progress checks. Local parsing,
trace export and durable finalization are outside network cancellation: the
execution deadline is not a hard end-to-end HTTP delivery guarantee. A failed
storage/trace backend can prevent delivery; configuration and unavailable-index
errors retain their existing HTTP behavior.

Closing a connection does not promise that a remote provider immediately stops
computing or billing. Every paid call conservatively reserves its maximum input
and output charge before work. Unknown usage retains the reservation. Reported
cost settles it; an overrun stops further work. The persistent non-resetting $5
ledger is shared across serving and all evaluations, and the verified provider
lifetime key limit remains the billing authority. Local zero API cost excludes
hardware and hosting. Concurrency is per instance, rather than a distributed
quota; the provider ledger protects spending across processes.

## Credentials and later feedback

Credential-shaped text is redacted from question and model-output boundaries;
the configured provider key is also removed by exact matching. Source imports
reject credential-shaped captures, and answering rejects unsafe legacy snapshots
or model settings before tracing them. Validation errors omit submitted values.
Provider errors never expose raw bodies. These controls minimize recognizable
credentials; arbitrary personal information is not automatically classified.

Online evaluation is disabled by default. `SupportJudge.assess_online` returns
disabled, pending (no slot), skipped (limits/cancellation), failed or completed
results with its own execution accounting. It cannot acquire answering tools or
block serving. This ticket supplies the admission/result contract; #23 implements
the durable automatic worker, queue retention, sampling and lag reporting.

The #22 feedback boundary must reuse the existing expiring session feedback
capability, verify response ownership, and apply redaction before storage or
judge input. Its initial integration contract is 500 comment characters / 1,000
UTF-8 bytes and ten submissions per minute per feedback context, with opaque
identifiers and static validation errors. Feedback writes remain deterministic;
comments cannot dispatch actions or change canon. #22 implements and exercises
that new endpoint, retention and rate accounting; no feedback endpoint is claimed
by #10. #23 retains finite independent online quotas and the shared provider cap.

## Verification

TDD began with a missing budget interface, then a missing API limit contract.
The disconnect regression observed an external model connection left running;
the malformed-vector regression exposed an uncaught empty result, and the
credential regression exposed an unredacted synthetic token. Each was retained
and repaired at the existing public seam. Subsequent focused checks passed:
44 execution/provider/evaluation tests, 31 answer/provider tests and eight
execution/retrieval tests. Strict mypy checks 58 files and Ruff passes.

All model services in these software checks are controlled external substitutes;
PostgreSQL/pgvector, HTTP disconnects and MLflow storage are real. Synthetic
instructions and credentials are labelled tests, not actual secrets or canon.
No paid calls or model-quality claim are needed for this enforcement slice.
Final independent review, the complete suite and revision-bound receipts are
recorded alongside this file before publication.
