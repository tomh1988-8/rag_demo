# Issue #25: versioned text-answer caching

Status: implementation, measured development workload and validation complete.
Issue #25 is closed after [verified publication](https://github.com/tomh1988-8/rag_demo/commit/81b7bd0465c71807ed217d0891ddb3ac9534c466).
[The completion receipt](publication.json) records the user's explicit approval, exact
remote-tree equality, all 210 software inputs and 101 original data files, and the
closed tracker with all nine criteria checked. The earlier publication rejection
is retained as [historical evidence](publication-pending.json) and superseded by approval.

The [ticket](https://github.com/tomh1988-8/rag_demo/issues/25) and preserved
[acceptance criteria](spec.json) require exact, eligible conventional-text reuse in
PostgreSQL with evidence compatibility, fresh serving identities, truthful accounting,
and the existing feedback/online-evaluation loop.

Implementation is `804c5ee`, with independently reproduced review repairs in
`d66b017`. The workload recorder's local-model support and strict typing are in
`082b240`/`a7a0780`. The fixed review point is the user's selected `1fefa2f`. Final recorder label clarification
is `4d584c1`; application/test sources are identical to the live-capture revision.
[Usage and policy](../../answer-cache.md) describe conservative normalization,
eligibility, versioned keys, expiry/capacity, retirement, disabling and fallback.

## Software and public contracts

Tests use the six previously confirmed boundaries: real PostgreSQL/pgvector,
conversation API and HTTP CLI, published snapshot/rollback, MLflow, Prefect and
evaluation reports. Controlled substitutes are confined to external model services.
No source data or private user inputs are rewritten.

The [repeat red/green](repeat-red.xml) and [initial passing repeat](repeat-green.xml)
demonstrate fresh identities with retained context/citations and zero new inference.
Other recorded cycles cover [explicit bypass](bypass-red.xml),
[retirement](retirement-red.xml), [invalid entries](invalidation-red.xml),
[graph fallback exclusion](graph-bypass-red.xml),
[online cohorts](online-cohorts-red.xml) and [metric arithmetic](workload-metrics-red.xml).
Green counterparts retain the executed repairs.

The initial native database attempt lacked pgvector; its [setup failure](database-setup-failure.xml)
is preserved. Subsequent checks use the project's pgvector Docker database with a
fresh disposable database per test. An early contract run had two test-setup failures
(equal frozen eviction times and misplaced retirement assertions); those were
corrected and [rerun successfully](fixture-repairs.xml). The initial focused run's
one feedback-summary failure was the newly added generation-count field missing
from the independent expected dictionary; the expected count remains four.

[Independent review](review.md) records one Standards and three Spec findings,
their failing public cases and nine passing repairs, with zero findings remaining.
The Docker contracts pass **12 cases** in [the actual run](docker-contracts.log).
The [full native suite](software-tests.xml) passes **765 tests**, zero failures, errors
or skips (16 warnings; exit zero). [Strict mypy](mypy.log) passes 192 files, with
[Ruff](ruff.log), [formatting](format.log) and Compose validation. The final image
packages the recorder; [207 packaged input hashes](docker-input-verification.json)
match the frozen sources. Build/maintainer files are outside that hash scope.

## Workload and scope

[The frozen protocol](runtime-protocol.json) separates development cache measurements
from retrieval/model-quality comparisons and held-out data. The plan has two cold
questions, four exact warm repetitions and one unresolved-session control. It uses
a fresh database/namespace and one original captured Phil arrival paragraph.
The paragraph is selected without rewriting source text; the full original capture,
reviewed character identity, source spans, index and publication are retained.

Automatic approval review rejected the proposed paid OpenRouter capture before
execution because the trusted instructions did not authorize its specific payload,
destination and spend. The shared ledger remains **$1.137848**, zero unsettled
reservations. The safer workload uses local Ollama only. Its first attempt stopped
before generation because the answer model was absent. The configured model was
then downloaded and its pinned answer/embedding digests verified. That failure and
setup evidence are retained; no paid result is repeated or approval rejection bypassed.

Local measurements establish the exercised cache capability and record actual
local-model outputs. They do not establish cloud latency/cost, representative model
quality, human canon adjudication, independent source corroboration or held-out release
acceptance. The project owner accepts measured release thresholds in final issue #21.
Semantic paraphrase matching remains a later opt-in extension with reviewed near-miss
data, hard compatibility filters and calibrated false-hit gates; no Redis is required.

[Actual local captures](runtime-local-v2/captures.json) retain seven distinct response
and trace identities: **six eligible requests, four hits, two misses and one bypass**.
Thus eligible hit rate is **4/6**, all-request coverage **4/7**, and warm hit rate **4/4**.
The [reviewed summary](runtime-local-v2/reviewed-summary.json) reports cold mean
end-to-end latency **108.63 s** (two requests) and warm mean **1.56 s** (four requests).
External API expense is **$0**, while hardware/electricity/hosting cost is unmeasured.
All four hits preserve their matching cold answer, context, source, publication,
configuration and generation; unsupported answer-text reuse and incompatible reuse
are each **0/4 reviewed hits**. This exposed sample is too small to set release gates.

The [independent source review](runtime-local-v2/reviews.json) supports **6/6 factual
reply texts**, while recording **0/6 first-person persona passes** (two generation
groups) and **3/6 correct qualification types**. The business answer and its two
hits incorrectly label a positive business fact `explicit_negative`.
[Both quality failures](regressions.json) remain visible rather than being counted
as complete-output quality passes. A hit faithfully repeats its original failures.

[Automatic online results](runtime-local-v2/online-report.json) show **7/7 selected
and code-assessed**, including four hit, two fresh-generation and one deterministic
clarification deliveries. Semantic online assessments are **0**, explicitly unscored.
The report's three distinct UUID origin groups comprise **two actual model generations
and one deterministic clarification**, as the [measurement notes](runtime-local-v2/measurement-notes.json)
explain. The workload recorder now labels that grouping explicitly and separately
reports the two new answer-model calls. This clarification re-scores retained outcomes
without repeating inference; the earlier ambiguous summary remains historical.

## Preservation and publication

[Frozen software inputs](software-inputs.json) contain 210 maintained source,
test, script and configuration hashes. [Original-data verification](original-data-verification.json)
confirms all 101 data files from `1fefa2f` are unchanged. The user's existing README
change, untracked skills/setup documents, skills lock and private PDF stay outside
the issue commits. The [validation summary](validation.json) separates software, source-based quality,
lineage and unmeasured costs. Publication is read back against the intended Git tree
before tracker completion; the final receipt records that verification.
