# Answer execution deepening

The user selected the top recommendation from the 18 October 2026 architecture
review and authorized implementation, a commit on the current branch and a push
to GitHub. The starting revision is
`5bbf3a4`.

## Accepted scope

Concentrate the text and Family tree answer lifecycle in one deep module.

- One answer interface owns route selection, category admission, execution-budget
  activation, trace identity, response assembly, trace finalization and receipt
  persistence. Serving and offline evaluation retain distinct category limits;
  the text and graph routes share their category's concurrency allowance.
- Keep text retrieval, captured-context selection, model accounting, answer
  validation, persona wording and stopped-answer behavior behind that interface.
- Keep explicit typed Family tree queries, deterministic wording, biological-only
  evidence, coverage limitations and zero inference calls. Graph requests must
  work without text-model configuration, including after failed text setup.
- Preserve pinned snapshot/publication identities, conversation references,
  capability checks, cancellation, saved private receipts and actual MLflow
  output. Existing source-selection errors retain their public error behavior.
- Preserve HTTP/CLI request and response schemas, historical response defaults,
  prompts, source/reference inputs, the private key and shared spending ledger.

Comparison-evidence binding and refresh-journal ownership remain separate
architecture candidates. This work does not implement another product ticket
or claim improved model quality.

## Test seams

Use the already-confirmed conversation HTTP/CLI and routing/bounded-execution
seams in [the testing strategy](../../design/testing-and-evaluation.md).
PostgreSQL/pgvector and local MLflow are real. Controlled external-model adapters
provide slow/failing responses without paid inference. Tests observe returned
answers, retained receipts and traces rather than private route call order.

The first tracer holds a text answer open and asks the Family tree route under
the same concurrency limit. It checks a saved stop outcome, zero graph/model work
and successful graph execution after the slot is released.

## Module and interface

`ask_phil.answering.AnswerService.ask` owns both answer routes. Callers pass the
existing request and optional category/turn/history/budget; they no longer choose
or initialize a second answering module. `prepare` retains the indexing operation
used by the existing maintainer and evaluation commands.

`TextAnswer` and `FamilyAnswer` are internal route implementations. Each retains
one pinned source and returns immutable `AnswerContent`, which contains evidence,
wording and observed model accounting. Only the outer module builds the public
`AnswerRecord`, flushes its actual trace and stores its private receipt. Route
implementations do not own concurrency pools, finalization or persistence.

One pool per category belongs to each answering module instance (one per HTTP
application). The text and graph routes share that pool; serving and offline
evaluation have separate pools. This does not add a distributed concurrency
limit. The direct typed graph-query operation keeps its existing bounded tool
contract.

One tracking destination is selected per application: the explicit argument,
then `MLFLOW_TRACKING_URI`, then the existing local default. Both construction
paths use it so graph trace readback retains the environment fallback when text
models are supplied.

Text models and retrieval configuration are initialized lazily under a lock.
Failed text setup leaves Family tree answers usable and releases the category
slot. Graph answers still require neither embedding nor answer-model setup.
PostgreSQL, local MLflow and the existing external-model adapter seams remain;
there is no new storage abstraction.

## Verification

The shared-admission tracer first failed because a Family tree answer ran while
the only serving slot was held by a text answer. It then passed through the same
HTTP interface, including exact MLflow output and original receipt readback.
Another integration check exercises the same answer interface with a held
offline text request: serving graph work remains available, a second offline
request stops, deadline completion releases the slot, and offline graph work resumes.
The existing model-free graph test also exercises graph answering after failed
text-model configuration. A review regression first exposed eagerly validated
supplied settings preventing application construction; supplied settings now
remain unvalidated until text or indexing access. Another tracer first failed
to find graph output in the environment-configured MLflow backend; both
construction paths now honor the same destination.

The final full suite passed **308 tests**, with zero failures, errors or skips,
in 933.866 seconds. It ran once after the review fixes. Strict mypy passed all
71 files; Ruff and formatting checks passed. Both independent review axes have
zero remaining findings. The suite reports the existing Starlette/httpx
deprecation and JUnit record-property warning categories.

The [validation record](validation.json) binds these results to the exact tested
source hashes and application fingerprint. All 19 public HTTP paths and 56
schemas match the starting revision. The answer prompt and all 42 frozen source,
reference, configuration and domain-document inputs remain unchanged. The
[software test report](software-tests.xml) and [independent reviews](review.md)
retain the supporting evidence.

Separate readback of the final tests' real MLflow storage captured **10 traces
and 24 spans** across shared serving admission, serving/offline isolation, failed
supplied text configuration and environment-selected tracking. The
[retained traces](runtime-traces.json) preserve actual root outputs, response
identity and execution records. Their controlled fixture ancestry, citations and
retained text were checked independently of schema validity.

Validation required zero paid model calls. The private key and shared trial
ledger are unchanged: **$0.361573** spent and zero unsettled reservations.

To reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
.venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
