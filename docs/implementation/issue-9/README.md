# Issue #9: calibrated quality comparisons

The implemented workflow has now run against actual public API conversations and
human-approved synthetic support controls. It captures and reviews six answer
dimensions separately, compares controlled development runs, and retains judge
decisions, source identities, costs and self-hosted MLflow artifacts. The measured
Janine and garage failures remain visible; both answer configurations fail their
critical quality gate. This ticket establishes the evaluation workflow, while
full-product answer acceptance remains #21.

Implementation starts at `07a4be2f405051da8ce5edf46957a2590f657d40`.
Both live captures used published revision
`e21e43d39b48c7a18800c67b80c233ced6da2765` and application fingerprint
`69b746440ddd0be345175581ce3e178b8f85a8bb088e92e39d8aefea0dda081c`.
The [publication receipt](publication.json) retains the initial verified software
publication and the final acceptance publication/closure state.

## Actual development comparison

[Baseline](baseline-capture-v2.json) and [candidate](candidate-capture.json) each
contain 14 public API responses: seven previously exposed cases repeated twice,
covering three story groups. The pinned Sol model, prompt, source snapshot, k=3
retrieval and 1,200-byte context configuration are identical. Only reasoning effort
changes, from medium to low. Both runs disable answer caching, use separate
namespaces, and start fresh sessions except the explicit Phil follow-up sequence.
No held-out answers were opened.

Independent AGENT [baseline annotations](baseline-annotations.json) and
[candidate annotations](candidate-annotations.json) inspect the original question,
every answer and qualification, required facts, actual context and citations.
They preserve unassessed claims and distinguish source-based agent review from
human adjudication. Deterministic [baseline scores](baseline-review.json) and
[candidate scores](candidate-review.json) bind those reviews to exact responses
and references. Missing labels produce null values.

[The controlled comparison](comparison.json) reports the same six case-macro
means for both configurations; the paired change is zero in every dimension:

| Dimension | Mean in each run | Assessed cases per run |
| --- | --- | --- |
| Correctness | 0.8889 | 3 |
| Grounding | 0.9028 | 3 |
| Completeness | 0.5000 | 4 |
| Citation support | 0.8889 | 3 |
| Answerability | 0.7143 | 7 |
| Relevance | 0.7143 | 7 |

These means exclude unassessed case dimensions. They are not a claim-level
accuracy estimate. Two repeats give observed ranges, not confidence intervals;
three story groups do not establish broad model reliability. Janine's grounding
varies from 2/3 to 3/4 across repeats because the partial response adds a supported
context-limitation statement. Both repeats still fail the original task.

Retrieval and context results explain different failures. The required Janine
passage is retrieved at rank 3 in every run but omitted from final context. The
session resolver also wrongly rewrites Frank's pronoun to Janine, causing a
false-premise correction of an originally correct question. The garage question
receives an unnecessary clarification with no retrieval: its shared-surname
character reference is unresolved. Neither outcome supplies its required fact.
The Phil arrival/follow-up answers pass source review; the ambiguous/isolated
questions appropriately clarify, and the mobile-number question abstains.
[The regression register](regressions.json) preserves the failures and follow-ups.

Stage timings come from the actual MLflow spans, with missing stages left null.
Answer-model spans exist for eight responses per run; their observed means are
3,202.9 ms baseline and 2,583.1 ms candidate. The captures were sequential small
development runs, so the difference does not establish a latency improvement.

## Calibrated support judge and observed limits

Tom explicitly approved all eight unchanged synthetic labels and the specified
OpenRouter payloads and costs with “continue, i approve”. The [approval receipt](approval.json)
and [human review package](label-review.md) record that approval before paid work.
Historical automatic denials are superseded permission events.

[Calibration](judge-calibration.json) freezes rubric `all-assertions-supported-v1`
and the low-reasoning pinned Sol profile. All 24 planned observations complete:
20 paid calls and four missing-context no-call results. Calibration and validation
each cover four examples in separate story groups, including positive, negative
and unavailable labels. All six boolean labels agree, all unavailable inputs stay
unavailable, and the observed eight repeats, four order probes and four verbosity
probes show no decision changes. Both partitions have zero false passes. This
supports only the declared small synthetic scope.

[Application to saved answers](support-application.json) uses the same rubric and
settings, with [independent support-only labels frozen before calls](support-application.references.json).
The [retained acceptance harness](apply_support.py) uses the public judge and
journal interfaces; it regenerates no answers. The judge agrees with 8/8 reviewed
positive labels. Twenty observations have no boolean reference label. It returns
true for four unresolved Janine identities, with reasons saying “Clare” without
resolving the added “Bates” surname, and for four phone abstentions whose frozen
agent review treats them as no-factual-assertion/unavailable. These are eight
decisions requiring review: four identity-adjudication gaps and four null-policy
mismatches. They remain unscored. Twelve missing-context cases stay unavailable
without calls. There are no reviewed negative development labels, so the live
false-pass rate is unavailable.

The context-only judge cannot detect the original-question rewrite or assess
completeness. Broader automatic support use remains pending fresh adjudicated
controls and review in #23; these decisions do not broaden eligibility or replace
independent correctness, relevance or answerability labels. Raw helpfulness votes
and corrections remain human reports, never answer keys.

## Cost and preserved failures

| Expenditure | Paid calls | Reported USD |
| --- | --- | --- |
| Earlier failed capture pilot | 2 | 0.0091820 |
| Completed baseline serving | 8 | 0.0274956 |
| Completed candidate serving | 8 | 0.0247656 |
| Offline synthetic calibration | 20 | 0.0206800 |
| Offline saved-answer support check | 16 | 0.0282900 |
| Issue #9 total | 54 | 0.1104132 |

The continuation costs $0.1012312: $0.0522612 serving and $0.0489700 offline
evaluation. The preserved shared non-resetting $5 ledger is $0.343084, with zero
unsettled reservations; per-call upward rounding explains its slight difference
from reported sums. Every paid command stayed within its approved $1 ceiling.
Independent annotations, deterministic scoring and software tests add no model
calls. The original [failed pilot](baseline-capture.json) and its references remain
retained. Its configured-k/zero-work clarification recorder bug has a passing
public API regression; it is excluded from the completed paired comparison.

## Software, lineage and reproduction

The final [software report](software-tests-live.xml) and [validation/readback record](live-validation.json)
record **248 passed**, zero failures/errors/skips, strict mypy passing 54 files
including the retained harness, Ruff passing, and zero remaining findings on both
independent review axes. They are associated with the same comparison in MLflow.
Routine tests use disposable
real PostgreSQL and MLflow and substitute external-model HTTP. The earlier
248-test [software report](software-tests.xml) and its [historical validation](validation.json)
remain intact; that validation predates human-approval metadata. The interrupted
121-pass report is historical and excluded from final validation. Strict mypy,
Ruff and the two independent review axes are recorded in [review.md](review.md).

The [protocol](protocol.md), [split manifest](splits.json) and
[scorer contracts](../../../data/references/quality-scorer-contracts-v1.json)
define input requirements, cadence, critical gates and the procedure for choosing
numeric thresholds after baseline measurement and before opening fresh held-out
candidate results. No final release threshold or held-out acceptance is claimed.
Fusion ablations, cache experiments and automatic online evaluation remain their
later tickets.

Use `scripts/evaluate_quality.py --help` for capture, score, compare and judge
arguments. The completed command inputs and MLflow run IDs are retained in
[live-validation.json](live-validation.json). Reproduction uses fresh output paths,
namespaces and private session directories because retained artifacts cannot be
overwritten. Scoring and comparison use saved responses without answer calls.
Paid reproduction uses the existing private key and preserved shared ledger,
bounded slice budgets and no automatic retries. Final MLflow readback verifies
seven finished results, 41 declared frozen inputs, 16 related comparison inputs
and all 28 actual stage measurements against the retained local evidence.
