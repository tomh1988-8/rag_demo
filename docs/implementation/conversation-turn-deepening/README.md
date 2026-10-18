# Character-reference turn deepening

Implements the architecture review's top recommendation, selected by the user on
18 October 2026. The fixed point is
`11019d661b77f3dc9ff0032e1cafe13d33c67f19`. The user authorized implementation,
review, a commit on the current branch and publication to GitHub.

## Accepted scope

Concentrate the complete authorized conversation turn in one module so the HTTP
caller no longer coordinates database locking, turn allocation, reference-state
advancement, clock use and saving.

- Authorize and serialize each turn before invoking answer execution. Allocate
  its identity and supply the bounded, unexpired character references internally.
- Return the answer only after its reference state commits. Answering, write or
  commit exceptions must not advance the turn or extend its reference lifetime;
  a subsequent request can proceed after the failure is resolved.
- Require returned conversation metadata to match the allocated turn. Keep only
  the permitted question references, pending clarifications and reference barriers.
- Preserve session and feedback capabilities, reset, idle and absolute expiry,
  bounded history, monotonic turn numbers, saved answer receipts, recorded model
  usage and traces, and the public HTTP/CLI behavior.
- Keep real PostgreSQL and the existing external-model adapter seam in tests.

This change concerns module depth and locality. The retained original-question
rewrite, shared-surname and context-budget failures in the issue #9 regression
register require separate behavior changes.

## Module and interface

`ask_phil.sessions.ConversationSessions` owns create, inspect, reset, feedback
authorization and the complete `ask` operation. It replaces `SessionStore`;
locking, saving and clock access are private implementation details. `SessionState`
is an inspectable value rather than a public turn-building procedure.

The `ask` interface accepts the session capability, question and existing answer
execution callable. Callers do not supply turn identity, retained history or a
database connection. The callable receives the allocated turn and history; the
existing `AnswerService.ask` and HTTP error-translating callable both satisfy its
typed contract. No abstract storage adapter is introduced.

`ConversationReference.retained` owns how resolution becomes reference memory,
beside the resolution rules. In particular, a character relationship question does
not establish the unnamed relative's identity. Generated claims never become
character references. `CONTEXT.md` records this domain distinction.

Saved answer receipts remain separate from short-lived reference memory. A storage
failure after answer execution can leave its separately saved receipt, as before;
the failed turn is not returned, its reference update rolls back, and the module
does not retry model execution.

## Verification

Tests use the already-confirmed conversation and external-model seams in the
[testing strategy](../../design/testing-and-evaluation.md). PostgreSQL/pgvector
and MLflow are real; external model responses are controlled and add no paid calls.

The initial tracer test failed because the deepened turn interface did not exist,
then passed after implementation. It verifies follow-up identity, reference
retention and original receipt resolution through the module's interface.

The relationship-follow-up test replaces a test that manually combined resolver
and session-state procedures. Existing resolver checks and public conversation
tests remain. New HTTP checks exercise failed answering and inject both immediate
write failure and deferred commit failure in a disposable PostgreSQL database,
then verify unchanged reference state and successful recovery through HTTP.

The final check results and tested source hashes are recorded in
[validation.json](validation.json), the full suite in
[software-tests.xml](software-tests.xml), and the two independent review axes in
[review.md](review.md).

The final full suite passed **253 tests**, with zero failures, errors or skips, in
535.37 seconds. All 35 focused conversation/reference checks passed, followed by a
successful final turn-interface check using public HTTP receipt readback. Strict
mypy passed all 54 source files; Ruff and formatting checks passed. Both independent
review axes have zero findings. The full HTTP routes and OpenAPI schemas exactly
match the starting revision, and all 56 frozen test-input hashes match the final
source and dependencies. Validation required zero paid model calls.

To reproduce, set `ASK_PHIL_TEST_DATABASE_URL` to a disposable PostgreSQL admin
connection, then run:

```sh
.venv/bin/pytest -q -p no:cacheprovider tests/test_conversation_api.py tests/test_conversation_rules.py
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/pytest -q -p no:cacheprovider
```
