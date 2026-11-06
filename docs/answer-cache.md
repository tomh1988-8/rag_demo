# Repeated text answers

The first cache reuses complete, cited conventional text answers in PostgreSQL.
It is enabled for serving and disabled for offline evaluation. The selected text
policy remains baseline; fusion and expanded contexts have their own cache identities.

An eligible request names reviewed characters explicitly, uses the current published
source/index, and has no conversation history, unresolved reference or contextual
pronoun. The first turn of a new session can reuse an answer. Later turns bypass
reuse, even when a name is repeated. Graph execution, graph-to-text fallback,
investigation, clarification, partial/unsupported replies, failures and bounded stops
cannot populate the cache. Explicit text overrides have separate identities from
automatic text selection. Legacy unpublished snapshots continue through normal answering.

Normalization applies Unicode NFC and collapses whitespace. It retains spelling,
case, punctuation, character names, dates, negation, word order and relationship or
criminal-justice roles. It does not equate paraphrases, aliases or retrieval synonyms.
Both the original and resolved request are in the identity.

Compatibility includes the public main-series/current-knowledge scope, complete
source fingerprint, active publication generation and index, text/fusion/context
policy, model and embedding settings, routing policy, persona prompt, output schema,
request limits, application source and relevant installed dependency versions.
Each hit checks the current publication and verifies the pinned artifacts, stored
payload and all retained context spans. Publishing, correcting or withdrawing a
snapshot prevents incompatible reuse. Rolling back creates another generation;
it does not reactivate the old cache entries. TTL is an additional bound.

Only the successful `answered` outcome with valid citations is admitted. This is
the application's declared source support, not independent semantic or canon
verification. Source-based review and online evaluation remain necessary. Raw
feedback cannot edit cached facts, retire an entry or certify correctness.

## Controls

`ASK_PHIL_CACHE_ENABLED=false` disables lookup and population, including in an
already running process. `ASK_PHIL_CACHE_POLICY` selects a JSON policy such as
[the default](../config/answer-cache.json): one-hour TTL, 256 entries and namespace
`serving-v1`. TTL is capped at one day and capacity at 10,000. Successful writes
remove expired/retired rows and evict the least recently used entries globally;
equal access times use the cache key as a deterministic tie. Each namespace has
distinct keys within that bounded PostgreSQL table.

Use `ask-phil ask 'QUESTION' --no-cache`, or send `bypass_cache: true`, to bypass
both reading and population for one request. With local maintainer database access,
`ask-phil retire-cached-answer GENERATION_UUID` retires a reusable generation while
preserving original response receipts. It can subsequently be generated anew.

Cache operations have short SQL/lock timeouts and skip work near the request
deadline. Unavailable storage falls back to normal answering using the same
execution budget. Invalid entries are discarded as misses; cache writes are optional.

## Delivery and assessment

Every delivery has its own response ID, read capability and MLflow serving trace.
A hit retains answer text, citations, source status, original assembled context
and shared generation identity. Entry and original-generation trace links stay
inside the database and owner-accessible serving trace. Session references and
feedback come from the current delivery. The reusable payload contains neither.

`cache` reports hit/miss/bypass, reason and request eligibility. Hits report current
elapsed time, zero new model/embedding tokens and zero model expense. Their text
pipeline contains current context identity with no replayed retrieval stages,
variant calls, model executions or old timings. The original pipeline remains
retained internally for provenance. End-to-end workload timing also includes HTTP,
receipt persistence and feedback registration, beyond the server's answer timing.

Feedback is attached to the new response. Automatic online processing assesses its
preserved context. Reports expose cache-status and fresh-generation delivery
cohorts, selected counts and distinct generations. Semantic results for the same
generation/context/rubric are reused, so repeated deliveries remain separate
interactions without becoming independent factual examples or duplicated judge cost.
Delayed/revised votes change the current delivery's rating and retain revision history.

## Workloads and comparison isolation

All retrieval/model/persona/routing comparison recorders explicitly bypass lookup
and population. Offline requests also bypass automatically. Never prefill a held-out
partition with tuning answers or labels. Use a new empty database or a unique
development namespace for each deliberate cache workload.

`scripts/evaluate_answer_cache.py` records up to twenty planned development requests
against the API and its local MLflow backend. Its `--workload` JSON names a namespace,
`partition: "development"`, and requests containing `case_id`, `phase` (`cold`, `warm`
or `control`), an API `request`, and an optional opaque `session` group. Start the
app with that namespace and the same `--profile`; use `--output` for a new directory.
The recorder preserves every actual result before checking trace/citation equality,
namespace, publication identity, model and cold-cache state. It reserves a bounded
model allowance before requests and stops on unknown expense. Existing directories
are refused to avoid repeating interrupted paid work.

Use `--summarize DIRECTORY --reviews FILE` to score retained results without model
calls. Reviews map case IDs to nullable `supported`/`compatible` labels and a
source-based `review_note`. Code computes arithmetic; it does not invent those labels.
The summary reports cold/warm/control counts, eligible hit rate, all-request coverage,
misses/bypasses, reviewed incorrect/stale reuse, support, current latency and known or
unknown cost, each with its denominator. These observations do not set release gates.

Semantic paraphrase matching remains a later opt-in extension. Enablement needs
reviewed positive/near-miss pairs, hard compatibility filters and calibrated false-hit
gates for character, date, negation, relationship direction, and accusation versus
crime/conviction distinctions. No semantic matching or Redis service is implemented.
