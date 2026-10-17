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
Separate live results, software artifacts and review findings are recorded below
when completed. All conversation cases are exposed development data; no human
adjudication, held-out calibration or complete canon claim applies.
