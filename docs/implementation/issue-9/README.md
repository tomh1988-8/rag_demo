# Issue #9: calibrated quality comparisons

Implementation starts at `07a4be2f405051da8ce5edf46957a2590f657d40`.
The ticket remains **open**. Software implementation and deterministic checks
are separate from the pending live comparison and human-reviewed calibration.

The workflow adds grouped, versioned references; six separately reviewed answer
dimensions; paired development comparisons with repeat ranges; public API capture
with fresh session state; a narrow context-support judge; and self-hosted MLflow
artifacts. Existing retained-capture scoring stays available. Relevance is
unavailable on old reviews unless it was actually annotated.

The [protocol](protocol.md) defines metrics, scorer inputs, cadence, critical
gates, baseline-informed threshold selection and limits on interpretation.
[The split manifest](splits.json) keeps historical cases in development and the
two synthetic judge story groups separate. Final held-out comparison is reserved
for later acceptance. [The human review package](label-review.md) records eight
proposed support labels; approval is still pending.

## Software validation

All **248 tests pass**, with zero failures, errors or skips, using native Python
and disposable real PostgreSQL plus MLflow. Strict mypy passes all 53 source
files, and Ruff passes. Both independent review axes have zero remaining
software findings. The [validation record](validation.json) binds the full
[test report](software-tests.xml) to unchanged implementation/input hashes and
the [independent review](review.md). External model HTTP is substituted in routine
software tests; these results make no model-quality claim.

The earlier full-suite run was interrupted after 121 passes to apply review
fixes. Its separate [report](software-tests-before-review.xml) is retained and
excluded from final validation.

## Execution state

The first live pilot captured two factual API responses before a recorder error
on a deterministic clarification. The recorder confused configured k=3 with the
clarification's zero retrieval work. The public API regression now covers that
case, and preserves both repeats and downloadable MLflow artifacts. The failed
pilot remains in [baseline-capture.json](baseline-capture.json), with its exact
[reference manifest](baseline-capture.references.json). Its two paid calls cost
$0.009182; the preserved shared ledger is $0.241848 with no unsettled reservations.

Automatic approval review rejected the corrected paid capture because it sends
questions and source passages to OpenRouter without explicit authorization for
this payload/destination. The user was asked to approve the seven frozen
development questions with their retrieved passages and the synthetic support
examples, using the pinned OpenAI endpoint under the existing shared $5 cap and
at most $1 per command. That answer remains pending. No corrected capture or
judge calls have been made after the rejection.

The eight human support labels were also requested separately. Until the user
reviews them, the fixture records `human_reviewed: false`; the judge command
refuses calibrated execution. Synthetic controls cannot establish broad canon
quality even if they pass.

## Run the workflow after the pending inputs arrive

Use `.venv/bin/python scripts/evaluate_quality.py --help` for all arguments.
The live serving APIs must use the exact reviewed source publication and the
specified profile. The medium-reasoning baseline and low-reasoning candidate
share the model, prompt, corpus and retrieval/context settings. Their separate
local servers can use ports 8009 and 8010. Use fresh output paths and namespaces.

```sh
export MLFLOW_TRACKING_URI=sqlite:///artifacts/issue-9-mlflow.db
.venv/bin/python scripts/evaluate_quality.py capture --model-profile config/openrouter-sol.json --namespace issue9-baseline-v2-development --api-url http://127.0.0.1:8009 --output docs/implementation/issue-9/baseline-capture-v2.json --max-cost-usd 1
.venv/bin/python scripts/evaluate_quality.py capture --model-profile config/evaluation-sol-low.json --namespace issue9-candidate-development --api-url http://127.0.0.1:8010 --output docs/implementation/issue-9/candidate-capture.json --max-cost-usd 1
```

Review assertions, facts and outcomes against the frozen references and actual
context. Record relevance independently. Bind every review to the exact response
and expanded reference fingerprints; inspect safe-but-incomplete answers as
failures of completeness/expected answerability where applicable.

```sh
.venv/bin/python scripts/evaluate_quality.py score --references docs/implementation/issue-9/baseline-capture-v2.references.json --capture docs/implementation/issue-9/baseline-capture-v2.json --reviews artifacts/issue9-baseline-reviews.json --output docs/implementation/issue-9/baseline-review.json
.venv/bin/python scripts/evaluate_quality.py score --references docs/implementation/issue-9/candidate-capture.references.json --capture docs/implementation/issue-9/candidate-capture.json --reviews artifacts/issue9-candidate-reviews.json --output docs/implementation/issue-9/candidate-review.json
.venv/bin/python scripts/evaluate_quality.py judge --references data/references/support-judge-v1.json --model-profile config/evaluation-sol-low.json --output docs/implementation/issue-9/judge-calibration.json --max-cost-usd 1
.venv/bin/python scripts/evaluate_quality.py compare --baseline-capture docs/implementation/issue-9/baseline-capture-v2.json --baseline-review docs/implementation/issue-9/baseline-review.json --candidate-capture docs/implementation/issue-9/candidate-capture.json --candidate-review docs/implementation/issue-9/candidate-review.json --changed-factor answer_settings --judge-calibration docs/implementation/issue-9/judge-calibration.json --software-tests docs/implementation/issue-9/software-tests.xml --output docs/implementation/issue-9/comparison.json
```

Scoring retained answers uses no answer-model calls. Semantic judge calls use the
existing private key and shared persistent ledger; no separate spending account
or retry loop is introduced. A failed judge preserves known billing or unknown
usage/reservation state. Public artifacts exclude private response/session tokens.

## Acceptance still required

Complete the corrected live baseline/candidate capture, independent source-based
answer reviews, human label adjudication, actual judge false-pass/sensitivity
analysis, and MLflow comparison/readback. Link the final software XML and code
identity. Update checklist evidence from actual results, verify publication and
then close the ticket. The current prototype and protocol do not pass those
runtime checks by themselves. Fusion ablations, real cache experiments and the
automatic online-feedback workflow remain their respective later tickets.
