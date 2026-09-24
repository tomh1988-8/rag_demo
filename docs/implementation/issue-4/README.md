# Issue #4: incomplete evidence and false premises

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
passed **13 cases**, including old receipt shape. Ruff and mypy passed. Final
full-suite and model evidence are recorded below when complete.

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

[References](../../../data/references/answer-policy-v1.json) are exposed development
labels established from the existing arrival clause and authored synthetic accounts
before model runs. Groups keep derivatives together. They cover a supported answer,
partial answer, missing fact, unclear subject, false premise, explicit negative,
conflict, four timing categories, missing day precision and empty assembled context.
No human review, representative quality or independent canon verification is claimed.

`scripts/evaluate_answer_policy.py capture --output <new-file>` uses the actual
answer service with offline expenditure categorisation. Set `DATABASE_URL` to a
local development database, `ASK_PHIL_OLLAMA_URL` if needed, and optionally
`MLFLOW_TRACKING_URI` (default `sqlite:///artifacts/issue-4-mlflow.db`). It loads and
indexes the declared fixtures, caps capture at 13 cases by default, performs no
retries or paid calls, and saves actual responses/traces without receipt capabilities.

Review the frozen outputs separately, including persona and appendix. Each review
records claim correctness against references, groundedness in supplied context,
claim-to-citation support, coverage of every required fact/qualification, and outcome
appropriateness. `score --capture <file> --reviews <file> --output <new-file>` rejects
stale response/reference hashes and missing facts, computes each dimension separately
with explicit assessed/unassessed counts, and logs artifacts/metrics to the capture's
MLflow run. Zero denominators are unavailable. Review labels are not generated by
the answer model and are not per-answer confidence scores. Human-calibrated judges
and broader held-out comparison remain #9.
