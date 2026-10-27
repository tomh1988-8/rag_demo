# Full-suite conversation queue correction

The first complete suite at `8163135` ran all 387 cases: 386 passed and one
existing concurrent-conversation case failed with HTTP 503. The original report
is retained in `software-tests-initial.xml`; `concurrency-failure.log` records an
isolated reproduction. PostgreSQL reported a statement timeout while waiting on
the conversation row's `FOR UPDATE` lock. The session module still had its baseline
implementation: the generic five-second SQL limit also limited serialization
behind a legitimate longer answer.

A controlled external-model regression first failed with the second valid request
already finished (503) before the first answer was released. Its initial output is
`concurrency-red.log`. The first model response is held beyond five seconds; a
separate request with a 0.2-second budget must still stop rather than acquire a turn.

The correction uses `FOR UPDATE NOWAIT` and rolls back each failed acquisition
before waiting. An active request retries the row acquisition within its remaining
execution deadline; cancellation wakes that wait. Individual SQL statements retain
the existing five-second cap. Calls without an active request budget retain their
five-second wait. No provider call is retried, and no source facts or trial spend
change. The row lock is held through answer/state commit as before.

Both the deterministic slow-answer/deadline case and the original concurrency case
pass (`concurrency-green.log`). The failed short-budget request does not consume a
turn, and successful concurrent requests retain distinct monotonic identities.
This necessary shared-conversation repair is re-reviewed before the final full run;
its completion report is kept separately from the first failed suite.

The follow-up Spec review identified a narrow race after the polling wait: the
owner could release its row at the moment cancellation/deadline woke the waiter.
A post-wait stop check now re-raises the same safe lock error before retrying.
The controlled API regression passes again (`concurrency-final.log`), and both
independent axes report zero remaining findings on this final guard.
