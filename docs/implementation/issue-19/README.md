# Issue #19: factual Phil persona and neutral evidence

The text prompt keeps Phil's voice in the answer while generated qualifications
use neutral third-person names. Supported lore is available regardless of Phil's
interests or personal knowledge. Unsupported premises remain unknown; serious
acts retain plain wording without excuses, jokes, victim blaming or invented
motives/injuries. Natural brief speech replaces a mandatory catchphrase. Sources,
citations and execution records remain tied to the captured snapshot.

The starting revision and review fixed point is
`a5c55489005f56cbed709829f7dd67ee38783eec` on `main`.
The [protocol](protocol.md) and [reference review](reference-review.md) define the
already-confirmed conversation API/CLI and evaluation seams, scope and rubrics.
References and authored counterexamples precede prompt changes. New labels are
source-based agent reviews, not human-adjudicated canon or held-out results.

## Actual controlled responses

[Baseline](baseline-capture.json), [first candidate](candidate-capture.json) and
[final](final-capture.json) each contain 24 actual API responses: twelve exposed
questions repeated twice without history or caching. Every answer has real CLI
readback, exact MLflow root-output agreement and resolvable source citations.
Selected crime-pilot spans and unchanged arrival/synthetic conflict/timing inputs
isolate wording from broader retrieval coverage.

The pinned Sol profile, embedding digest, questions, snapshots, k=3 and 1200-byte
context limit stay fixed. The comparison checks identical actual context and
serving controls per observation. Between live runs, only `answers.py` changes
in the package, and only its prompt changes. Exact prompts/hashes are captured;
[baseline](baseline-software-inputs.json), [candidate](candidate-software-inputs.json)
and [final live inputs](live-software-inputs.json) retain source identities. A
later capture-reporting repair changes no generation behavior or prompt and
requires no answer regeneration. [Historical source and mapping](live-source-map.json)
retain the exact prior prompt and capture-helper bytes. Every reconstructed file
matches its original frozen hash, and all three original application fingerprints
reconstruct exactly. [Runtime readback](runtime-readback.json) independently checks
all 72 actual root/context/CLI records and eight finished evaluation artifacts.

[Baseline annotations](baseline-annotations.json), [candidate annotations](candidate-annotations.json)
and [final annotations](final-annotations.json) independently label dimensions
within each response. These labels are from the implementing agent. The
[completed scores](final-scores.json) bind labels to exact responses/references.
Missing factual assertions remain unavailable; harm applies to eight observations.

The [controlled comparison](comparison-verified.json) reports:

| Measure | Baseline | Final |
| --- | --- | --- |
| Neutral generated appendix | 21/24 | 24/24 |
| Brief/direct first-person voice | 24/24 | 24/24 |
| Serious-harm treatment | 8/8 | 8/8 |
| Outcome and inline qualifications | 24/24 | 24/24 |
| Supported replies with mandatory opener | 20/20 | 0/20 |
| Reported serving inference USD | 0.0521519 | 0.0555957 |

Voice scores do not establish stronger character authenticity. Two repeats show
observed variation, not confidence intervals or broad reliability. Expense rises
$0.0034438; mean sequential response times are about 3.94 and 4.11 seconds, with
no latency improvement claimed.

Under frozen agent labels, final factual/support/citation means are 1.0 across
20 assessed observations; four assertion-free outcomes remain unavailable.
Baseline means are 0.99 and include the disputed foreman label below. These are
observation means, not canon accuracy or a confirmed factual improvement.
Final completeness is 0.975: the reference additionally requires Jane's cover-up
although the question asks only who killed Lucy. One repeat omits the extra fact
while identifying the killer correctly. Preserve this conservative coverage
failure; version the reference before using it as a release completeness gate.

## Retained failures and judging

Three baseline appendices speak as Phil. The first candidate fixes neutrality
but presupposes Phil's absence in one answer without source support. Both final
repeats explicitly keep presence/absence unknown. All original captures and
[regressions](regressions.json) remain intact.

The unchanged issue #9 support rubric/low-reasoning Sol profile reuse eight
human-approved synthetic labels, disjoint calibration/validation groups and
recorded repeat/order/verbosity checks. No unchanged calibration is repeated.
The [new support application](support-application.json) checks nine saved
answer/qualification records plus one explicitly authored denial, against
[source-based labels frozen before calls](support-application.references.json).
It assesses no voice, harm, completeness or canon correctness.

Agreement is 9/10 against agent labels, including all seven selected final
answers. The judge rejects the candidate's unsupported absence and the authored
denial. The unresolved baseline disagreement concerns “jury foreman who found
him guilty”: the strict reviewer flags the individual verdict role, while the
judge paraphrases it as payoff preceding conviction. Its observed false-pass
count is 1/3 against agent negative labels, not a human-adjudicated error rate.
Human adjudication is required before changing that label or broadening judge
acceptance. Earlier issue #9 identity/null-policy disagreements stay unresolved.

## Software and reproduction

Six focused persona tests cover independent harm scoring, missing
labels, actual API/CLI/trace readback, stale-label rejection, real MLflow
publication/metrics and hidden model-change rejection. Initial review publication
failed because extended persona fields used factual-review keys; retain
`baseline-scores.json` and use [baseline-scores-v2.json](baseline-scores-v2.json).
Capture reporting now separates recorded model calls, including query embeddings,
from paid answer calls. Original live headers are unchanged; the comparison uses
actual execution records: 48 model calls per 24-answer run.

Strict mypy across 131 files, Ruff and formatting pass. Both independent review
axes have zero remaining findings after repairing comparison-score integrity.
[Review](review.md) records the original finding and its verified repair. The full suite passed **567 tests** with zero failures, errors or skips in
23 minutes 33 seconds. The one warning is the existing Starlette/httpx deprecation.
[Validation](validation.json) and [full report](software-tests.xml) bind all 183
frozen inputs to tested revision `3906387`. Software checks remain distinct from
model-quality limits.

Capture with `ASK_PHIL_TEST_DATABASE_URL` pointing at disposable PostgreSQL/pgvector,
the existing private key/ledger and a fresh output path:

```sh
export ASK_PHIL_MODELS=config/openrouter-sol.json
export ASK_PHIL_OLLAMA_URL=http://127.0.0.1:11435
export MLFLOW_TRACKING_URI=sqlite:///artifacts/issue-19-mlflow.db
.venv/bin/python scripts/evaluate_persona.py --output artifacts/new-persona-capture.json
```

`review_persona.py score --help` and `compare --help` describe offline assessment.
The original non-resetting $5 ledger is **$0.673627**, zero unsettled reservations,
after 72 paid answer calls and ten judge calls. Their reported charges total
$0.1779852; upward rounding explains the ledger difference. No retries, key/ledger
reset or paid software tests occur. Preserve all pre-existing user/private files.

The project register extends AD-06.3, AD-08.2, RAG-03 and the persona part of
AD-10.4. Counts remain 35 Pass and 16 Pending. Wider graph/routing, human release
thresholds, held-out acceptance and automatic online feedback stay pending.
Reuse these scorer checks at graph/investigative integration, and recheck when
prompts, models, serious-harm examples, sources, formatting or labels change.
