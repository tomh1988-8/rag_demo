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

## Live acceptance awaiting authorization

No paid model calls have run for #8. Automatic approval review rejected the capture
command and its evidence-backed reassessment: it requires trusted authorization
for this specific external destination and paid spend, and did not accept the
repository's historical $5 trial authorization as sufficient. No workaround was
attempted. The shared ledger remains **$0.208899**, zero unsettled reservations.

The concrete proposed sample is [conversation development v1](../../../data/references/conversation-v1.json):
nine real CLI/API turns plus a reset, with six factual generations expected and
three zero-model clarifications. It uses only retained public Wikipedia passages
and the fixed fictional-character questions, the existing OpenRouter/OpenAI Sol
profile and the same non-resetting ledger. Its maximum is twelve paid calls and
$0.25 additional reported inference spend within the original $5 cap. The alias
introduction was amended before execution so the later father question has an
unambiguous subject; this is disclosed in the frozen dataset.

After specific approval, start the local API with the retained core-profile
database and `ASK_PHIL_MODELS=config/openrouter-sol.json`, then run:

```sh
uv run python scripts/evaluate_conversation.py capture \
  --api-url http://127.0.0.1:8008 \
  --output docs/implementation/issue-8/serving-matrix.json
```

The recorder retains private session/read receipts under ignored `artifacts/`
and publishes only response/trace/evidence records. Independently review every
actual factual claim, context support, citations, required facts, persona wording,
clarification, selection and reset; then score hash-bound `QualityReview` annotations
using the recorder's `score --capture ... --reviews ... --output ...` mode. Serving
generation costs remain serving; offline review has separate MLflow artifacts and
zero answer-model calls. Do not mark #8 complete or close it before this review.

All cases are exposed development data; no human adjudication, held-out calibration
or complete canon claim applies. A passing software suite does not fill the missing
live-model acceptance result.
