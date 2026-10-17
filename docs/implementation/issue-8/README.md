# Issue #8 — grounded follow-ups and reset

The conversation API retains reviewed character references and at most one pending
user clarification question per retained turn. It never reads previous assistant
answers, feedback, saved responses or evaluation records to answer a question.
Every factual turn retrieves and assembles evidence again from its pinned source
snapshot. Missing or ambiguous identities receive a deterministic clarification
with no retrieval, generation or invented citations. Recorded usage is zero for
those skipped operations; completed factual turns retain actual measured usage.

## Use

```sh
uv run ask-phil chat
# Questions, follow-ups, /reset, /quit; EOF also exits.

uv run ask-phil start-session artifacts/session.json
uv run ask-phil ask 'When did Phil Mitchell first arrive in Walford?' \
  --session artifacts/session.json
uv run ask-phil ask 'What did he open?' --session artifacts/session.json
uv run ask-phil reset artifacts/session.json
```

`--snapshot` on `chat` or `ask` selects a retained snapshot. Otherwise each turn
pins the active publication. The original standalone `ask` path remains available.
Session receipt files are created exclusively with mode 0600; keep them private.
They contain session and future feedback bearer capabilities. Their tokens are
not embedded in answer traces or published evaluation captures.

HTTP: `POST /v1/sessions` returns a new session receipt. Use its `session_token`
as a Bearer header for `POST /v1/sessions/{id}/turns`, `GET /v1/sessions/{id}`,
and `POST /v1/sessions/{id}/reset`. Turn bodies use the existing bounded question
and optional snapshot contract. Missing, wrong and expired credentials return
404. Clients cannot supply history, fabricated assistant messages or turn IDs.

## State and identity contract

- Retain the last eight turn references. Resolve pronouns against the most recent
  retained named turn, preserving all plausible identities. Do not infer gender
  or extract new reference facts from generated answers. Reviewed names/aliases
  use catalogue IDs. Unsupported relation/event deixis may require a full question.
  Free-text partial names require clarification; a unique partial name can select
  a pending choice. Full reviewed aliases work regardless of case. Performer names
  never create character-reference state. Object pronouns need retained context;
  naming a subject does not establish who an unnamed object is.
  A relationship question does not establish a relative's identity: later turns
  must name the character. This context barrier prevents confusing a relative
  with the named owner of the relationship.
- Context expires after thirty idle minutes. Session access expires two hours
  after creation, including across API restarts. New sessions prune expired rows;
  expired rows are inaccessible before pruning. Reset immediately removes all
  reference/pending-question context and increments its generation.
- Concurrent turns and reset serialize per session in PostgreSQL. Turn numbers
  remain monotonic through reset; each turn also has a unique UUID. Each immutable
  response/trace records session, turn, generation, resolved question and the
  reference turn used. Source publication remains pinned per request.
- A separate random feedback capability lasts thirty days from creation. Its
  SHA-256 is stored separately from short-lived context and survives reset and
  session expiry. The later #22 submission path must additionally verify that
  the immutable response belongs to that session. Feedback submission is not
  implemented by #8. This capability neither authorizes new turns nor reads history.
- Saved original responses retain their existing per-response read capabilities.
  Reset changes no historical response, trace, evidence or evaluation identity.
  Retained response/MLflow records remain maintainer evidence, never answer memory.

## Verification and limits

[Reviewed development cases](cases.md) precede implementation. The confirmed
conversation API/CLI and public reference/state rules are the test seams; real
PostgreSQL/pgvector and MLflow run with controlled external model responses.
The misleading-history fixture intentionally serves a wrong date, then verifies
the next request's source retrieval, prompt and factual answer independently.
These software checks do not establish semantic model quality.

The implementation began at `f864d3570170a65b986ba0a090247f7a1167c033`.
[Independent review](review.md) has zero remaining Standards and Spec findings
at product revision `2c99a56`. Twenty public reference/state rules pass, including
the review repairs. [The regression register](regressions.json) preserves those
failures, the conservative scope, and earlier #7 retrieval/context limitations.

## Software results

The [full final suite](software-tests.xml) passes **182 tests**, zero failures,
errors or skips, in 393.99 seconds. Ruff and strict mypy (46 source files) pass.
[Validation](validation.json) binds the software report to the tested product
revision, exact source/test/script/dependency/model-profile/reference hashes and
the existing shared budget. The existing upstream Starlette/httpx TestClient
deprecation is the only warning. Software tests used no paid model calls.

The suite covers fresh retrieval after deliberately misleading output, actual
MLflow retrieval/context/generation spans, clarification/selection, reset and
unchanged historical responses, idle/absolute expiry, anonymous feedback lifetime,
session isolation/recreation, concurrent turns, bounded truncation and real CLI
HTTP transport, including interactive chat. Twenty focused reference/state cases
include all independent review failures. The remaining live result is explicit.

## Live acceptance

The user explicitly approved the live sample and publication after the initial
approval-review rejections. [The final matrix](serving-matrix.json) records nine
real CLI/API responses plus a reset: six factual generations and three deterministic
clarifications. It uses the unchanged core-profile snapshot and Sol profile.

[Independent Spec labels](answer-reviews.json) and [separate scored dimensions](answer-quality.json)
pass **15/15** actual factual assertions for correctness, grounding and citation
support, **7/7** required facts and **9/9** appropriate outcomes, with zero critical
failures. Clarifications have no factual denominator. The additional Kat/Zoe
assertions were reviewed against their actual passages, not accepted merely because
citations resolve. [Persona review](live-review.md) checks Phil's I/my phrasing,
identity preservation, alias resolution and uncertainty separately.

[Actual MLflow readback](execution-review.json) confirms all nine traces and 36
spans: every factual turn freshly retrieves the selected required passage and
supplies sufficient context; all three clarifications skip retrieval and generation
with zero usage/cost. Model inputs contain only system instructions and the current
resolved question with captured evidence. Private bearer capabilities are absent.
[Public lifecycle readback](lifecycle.json) confirms reset, another session's denied
access, unchanged original responses, resolvable citations and state/response
persistence after an actual API restart.

Six paid serving calls cost **$0.0237656**, below the approved $0.25 slice limit.
The existing non-resetting $5 ledger totals **$0.232666** after upward rounding,
with zero unsettled reservations. [Summary](summary.json) separates serving from
the offline review, which uses zero answer-model calls and a separate MLflow run.
Application elapsed times range 1.73–7.55 seconds, median 4.61 seconds, across this
one mixed sequence; these exclude complete CLI wall time and are not a controlled
performance comparison. No source, test or script changed after the 182-test run.

The two related story groups remain exposed development data. These observations
do not establish held-out reliability, human adjudication, independent canon
corroboration, exhaustive persona range or full serious-harm acceptance. Earlier
#7 Janine/context and explicit garage co-ownership gaps remain under #24/#9.

To reproduce with the retained database, existing key and preserved shared ledger,
start the API with `ASK_PHIL_MODELS=config/openrouter-sol.json` and use fresh output
paths (the retained capture cannot be overwritten):

```sh
uv run python scripts/evaluate_conversation.py capture \
  --api-url http://127.0.0.1:8008 --output artifacts/conversation-new.json
uv run python scripts/evaluate_conversation.py score \
  --capture artifacts/conversation-new.json --reviews artifacts/conversation-new-reviews.json \
  --output artifacts/conversation-new-quality.json
```

Review each new response against the frozen references and actual source/context
before scoring it. The recorder retains private session/read receipts under ignored
`artifacts/`; published captures contain only response/trace/evidence records.

## Publication

[Published implementation 1991e3b](https://github.com/tomh1988-8/rag_demo/commit/1991e3bf1e5a404137b1b8cb178a15bf85ebc6cf)
exactly matches local acceptance commit `319de84`, tree
`e3641ea170aef7c0dfeee95f55c95af94671200f`. The published objects were fetched,
both tree IDs matched and `git diff --exit-code` passed before closure.
[Issue #8](https://github.com/tomh1988-8/rag_demo/issues/8) is closed as completed;
all eight checked criteria and the closure state were read back.
[The receipt](publication.json) records verification and acceptance. The authenticated
GitHub connector published without forcing because native Git lacks push credentials;
both histories are retained locally. Earlier automatic approval denials are historical.
#9 is recommended next; another ticket requires the next implementation instruction.
