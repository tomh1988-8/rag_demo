# Issue #4: incomplete evidence and false premises

**The scoped response-policy acceptance now passes with the Sol cloud profile.**
The [cloud record](cloud/README.md) preserves the failed attempts, prompt repair,
independent reviews, full 13-case rerun and five actual CLI/API checks. The final
software suite passes **85 tests**. The runs cost **$0.10890587** in total, leaving
**$4.89109413** under the verified non-resetting $5 key limit.
Use `config/openrouter-sol.json` for this accepted slice; the Qwen smoke failed
citation validation and GLM remains untested. See [private setup](../openrouter-setup.md).
This is exposed development evidence, not held-out reliability or broad canon
coverage. Close #4 only after its code and evidence are published and the exact
remote tree is verified. The local-model results below remain historical failures.

Implementation starts from `936f265d614345a3209e7f955f1aa82fa9f95a28` on
`main`. Scope is [issue #4](https://github.com/tomh1988-8/rag_demo/issues/4).

The already approved seams are the conversation API/CLI, exposed outcome and
citation rules, evidence resolution, and evaluation/scorer contracts. Real
PostgreSQL/pgvector and MLflow exercise integrations; only the external model
HTTP boundary is substituted in deterministic tests. No new seam approval is
needed. Live model observations are separately labelled development evidence.

Implement one reviewed case and red/green behavior at a time: partial answers;
clarification and abstention; false premises versus explicit negatives; attributed
conflicts; date uncertainty; separate quality dimensions. Expectations are authored
from retained evidence before generating responses. Synthetic sources test policy,
not EastEnders canon. Review, full-suite validation and publication follow.

Existing snapshot fingerprints and immutable saved response shapes must survive.
New passage provenance is optional for older single-source snapshots. Empty context
must yield a deterministic, coverage-qualified abstention without a model call.

## Development record

The targeted red/green cycles observed the following failures before implementation:

| Slice | Red | Green |
| --- | --- | --- |
| Partial answer | Returned `failed`, not `partial` | 1 API test passed |
| Clarification | Accepted a clarification with no missing choice | 4 partial/clarification/abstention cases passed |
| False premise / explicit negative | Qualifications rejected; synthetic source label rejected | 2 API cases passed |
| Conflicting accounts | Per-passage source provenance rejected | 1 API case passed; 6 provenance tests passed |
| Timing | All four precision outcomes returned `failed` | 4 API cases passed |
| Empty context | External model was called | 1 API case passed with no LLM span and zero answer tokens |
| Separate quality scores | Scorer import failed | 4 scorer cases passed, including null denominators |

Then the complete conversation test file passed **23 cases**, including all four
outcomes through the real HTTP CLI and original-response lookup. Exposed rules
passed **17 cases** after the live-discovered schema regressions, including old
receipt shape and independent JSON Schema validation. The final Docker suite passed
**66 tests**, with zero failures/errors/skips: [log](docker-tests.log),
[JUnit results](tests.xml). Ruff and mypy passed (23 source files).

The first Docker build exposed missing build-context allowlist entries for the
evaluation runner and historical receipt fixture; these were corrected before the
successful builds. No full-suite test run failed. Docker's old orphan-container
notice and Starlette's upstream test-client deprecation warning are nonfatal.

## Public outcome and provenance contract

`status` is `answered`, `partial`, `clarification`, `insufficient_evidence` (abstain),
or `failed` (provider/contract failure). Partial and clarification outcomes name
`unanswered` parts. Supported/partial answers need unique citations to whole spans
actually in assembled context. Absence of retrieval/usable context never proves a
negative; empty context bypasses generation with a fixed coverage-qualified reply.

`qualifications` records neutral `detail`, `kind`, and supporting `evidence_ids`.
Kinds are false premise, explicit negative, conflict and timing. A conflict requires
two distinct cited passages and a partial outcome; its unresolved question remains
visible. Timing additionally carries exact/approximate/relative/unknown precision.
The prompt requires the same material qualifications in the persona wording.
These are structural guarantees plus evaluated semantic behavior, not a claim that
schema validation can prove an arbitrary sentence true.

Passages may override the snapshot's source with their own captured attribution.
Citation resolution returns that canonical source, never an invented model label.
Absent optional fields remain absent, preserving v1 hashes and original responses.
Synthetic fixtures use `support_status: synthetic_fixture`; they are not canon.
This is a small extension of manual captured fixtures, not the source-import or
structured correction workflow owned by later tickets.

## Evaluation protocol

[References v2](../../../data/references/answer-policy-v2.json) are exposed development
labels established from the existing arrival clause and authored synthetic accounts
before model runs. Groups keep derivatives together. They cover a supported answer,
partial answer, missing fact, unclear subject, false premise, explicit negative,
conflict, four timing categories, missing day precision and empty assembled context.
No human review, representative quality or independent canon verification is claimed.
The independent Spec reviewer corrected v1's overly restrictive false-premise outcome:
correcting the year and giving the supported purpose can fully answer that question.
V1 and its interrupted capture remain preserved; v2 is used for subsequent runs.

`scripts/evaluate_answer_policy.py capture --output <new-file>` uses the actual
answer service with offline expenditure categorisation. Set `DATABASE_URL` to a
local development database, `ASK_PHIL_OLLAMA_URL` if needed, and optionally
`MLFLOW_TRACKING_URI` (default `sqlite:///artifacts/issue-4-mlflow.db`). It loads and
indexes the declared fixtures, caps capture at 13 cases by default, performs no
automatic retries, and saves actual responses/traces without receipt capabilities.
Selecting a cloud profile makes bounded paid calls through the shared trial ledger.

Review the frozen outputs separately, including persona and appendix. Each review
records claim correctness against references, groundedness in supplied context,
claim-to-citation support, coverage of every required fact/qualification, and outcome
appropriateness. `score --capture <file> --reviews <file> --output <new-file>` rejects
stale response/reference hashes and missing facts, computes each dimension separately
with explicit assessed/unassessed counts, and logs artifacts/metrics to the capture's
MLflow run. Zero denominators are unavailable. Review labels are not generated by
the answer model and are not per-answer confidence scores. Human-calibrated judges
and broader held-out comparison remain #9.

## Historical local results and unresolved local-model regressions

| Capture | Scope | Result |
| --- | --- | --- |
| [v1](local-policy-v1.json) | Four completed cases; fifth inference interrupted | Obsolete prompt exemplar and optional fields allowed incomplete drafts. [Interruption record](interrupted-v1.json) preserves the checkpoint/unknown cancelled usage; MLflow run marked killed. |
| [v2](local-policy-v2.json) | All 13 exposed development cases | 12 served technical failures; one correct deterministic empty-context abstention. Timing precision was optional in the generated schema, and the conflict response hit the 256-token ceiling. |
| [v3](local-policy-v3.json) | Six targeted cases after schema/budget fixes | Three appropriate outcomes out of six; one served citation-support failure. Ambiguous subject, missing fact and false-premise behavior remain unacceptable. This subset is not a full-matrix rebaseline. |

V2's [reviews](reviews-v2.json) and [scores](scores-v2.json) give completeness **2/20**
and answerability **1/13**. Correctness, groundedness and citation support are
unavailable: the served responses contain no domain claims. Rejected drafts are
retained for diagnosis but are not treated as served claims.

V3's [independent agent reviews](reviews-v3.json) and [scores](scores-v3.json) report:

| Dimension | Passed / assessed | Unassessed |
| --- | --- | --- |
| Correctness against reviewed retained references | 10 / 10 | 1 |
| Groundedness in supplied context | 10 / 11 | 0 |
| Required-fact completeness | 5 / 10 | 0 |
| Claim-to-citation support | 10 / 11 | 0 |
| Appropriate response outcome | 3 / 6 | 0 |

These dimensions deliberately remain separate. Truthful arrival facts do not make
answering an unresolved pronoun appropriate. The multipart appendix upgrades
"arrives ... to open" into "Phil opened": the completed act's correctness is
unassessable here, and its citation does not support it. This is a **served critical
false-citation regression**. The conflict appendix shows disagreement, but the
persona does not explicitly retain its unresolved status. Phil replies also revert
to third person, and synthetic labels are missing from prose despite being present
in evidence metadata. These are failures, not accepted behavior.

[Reviewed regressions](../../../data/references/answer-policy-regressions-v1.json)
preserve the exact response/trace identities, source distinctions and unresolved
dispositions. Keep all derivatives with their original event groups. No served
unsupported-negative assertion was observed; a rejected draft misclassified missing
evidence and attached an irrelevant citation. Do not dilute the known failures in
aggregate metrics or move exposed examples into a held-out split.

Historical local runtime bounds are one answer call, no retries, whole-span context ≤1200 UTF-8
bytes, model context 4096, output ≤512 tokens, and a 180-second network-operation
timeout. That timeout is not a guaranteed wall-clock deadline or account spending cap. The
512 ceiling follows observed truncation; old 256-token receipts remain valid. Local
API cost is zero, excluding hardware, electricity and hosting. Capture runs overlapped
some Docker builds, so these timings are not a controlled performance comparison.

Both completed captures and their separate review/score artifacts are logged to local
MLflow. Existing API/MLflow containers are still the prior #3 runtime; newly built
#4 images were tested, but no acceptance deployment/restart of this failing candidate
is claimed. The disposable test database and all model/data volumes are retained.

## Cloud acceptance and handoff

The [cloud summary](cloud/summary.json) and [review](cloud/review.md) supersede the
old acceptance status in [the local validation snapshot](validation.json).
[Regressions v2](../../../data/references/answer-policy-regressions-v2.json) retains
all historical failures and links every affected case to the accepted Sol rerun.
It also preserves both defects in the first Sol matrix: marking a missing date
fully answered and falsely asserting that publication/broadcast calendar dates
differ from an unknown story date. A targeted repair and complete rerun pass with
unchanged reference labels. Persona, neutral qualifications and synthetic source
labels were independently reviewed.

The temporary cloud API passed restart/receipt checks and was stopped. Existing
issue-3 Docker containers still use the local model. No cloud deployment is claimed.
After publication and closure, #5 is the recommended next issue; #9 and #10 also
become unblocked. Wait for the next implementation instruction. Representative
comparisons and judge calibration remain #9, with full release acceptance in #21.
