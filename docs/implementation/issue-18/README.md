# Issue #18: route and escalate from obtained evidence

Ordinary API and CLI requests select routes automatically. Explicit `--route
text_rag`, `--route graph` with typed arguments, and `--route investigation`
remain available for demonstrations and controlled comparisons. Public receipts
distinguish overrides from automatic choices.

Starting revision/review fixed point: `664541a`. The first implementation and
frozen comparison checkpoint is `8f63213`. The [issue](issue.json),
[parent specification](parent-spec.json), [plan](run-plan.md) and
[pre-call protocol](protocol.md) define the accepted scope and evaluation seams.

## Workflow and responsibilities

The application proposes typed graph queries only for complete, conservative
question patterns: biological parents/children/ancestors/descendants,
relationship history, crime/justice or pregnancy/death history, and connections
between named characters. Character names/aliases must resolve against reviewed
identities. Additional clauses, unsupported thematic questions and unresolved
names use text or clarification. This grammar deliberately covers a subset of
natural language; matching a family word somewhere in a question is insufficient.

Eligibility requires admitted claim coverage for the requested direction,
participants and event kind, together with the configured capability. Raw
extraction counts and roster membership do not establish coverage. Every query
still runs through the actual read-only typed graph tool and its source-bound
publication checks. Graph results retain qualified coverage, roles, direction and
source support; empty results do not prove the absence of a story connection.

The selected conventional text policy retrieves and generates the first text
answer. Its validated outcome and unanswered parts provide the model's explicit
evidence assessment. This assessment is not an independent support score. An
answered outcome needs no investigator, regardless of question complexity. A
reviewed interpretation, unresolved reference or stopped request is retained.
For an evidence gap, explicit rules require additional unexamined captured
material relevant to a topic or supported graph capability, a published snapshot,
and sufficient remaining shared authority. At most one investigation is admitted.

The investigator has model discretion over declared text/graph tools and final
coverage. It receives initial text evidence and unanswered parts, retains one
publication and the same budget, and cannot grant itself capabilities or reset
limits. If it fails or loses earlier cited support, the initial supported partial
answer is retained with the attempted investigation and its expense. Graph
queries that obtain no usable evidence fall back to the same text pipeline when
the request can continue.

Selection and eligibility use explicit rules and incur no router-model call.
The text answer supplies evidence assessment without a separate checker call.
The investigator is the only controller with model tool-selection discretion.
This keeps its additional cost visible in the counterfactual comparison.

## Configuration and accounting

`config/routing-default.json` versions the escalation setting and minimum
remaining time; select it through `ASK_PHIL_ROUTING_POLICY`. The selected
conventional policy remains `config/text-baseline.json`; existing fusion,
expansion and combined configurations continue to work inside the text route.

Automatic default limits allow eight model operations, four tools and 24 HTTP
operations while preserving the existing 1,200-byte context ceiling and $0.15
request reservation cap. Existing explicit serving/offline settings constrain
automatic requests unless an operator explicitly supplies `automatic_serving` or
`automatic_offline_evaluation`. The legacy comparison uses its separately frozen
4,000-byte/$0.20 operating point; the ordered supplement uses $0.30. These differ
from the default operating point.

The `routing` appendix records the requested route, automatic/override selection,
eligibility, checks, fallback/escalation reasons, actual stages, graph findings,
before/after budgets, timings, per-stage accounting and final stop reason. The
same complete response is stored and emitted as the actual MLflow root output.
Initial text variants/windows/context remain in `text_pipeline` after escalation;
the investigator records its initial context IDs and acquired final context.

Request totals include every stage's reported input, output, embedding usage and
cost. Individual provider receipts remain in the text/investigation records.
If one stage has unavailable usage or cost, the corresponding total is null;
known stages remain inspectable. Text fusion/expansion are conventional stages,
and answer caching is disabled for the route comparison. Indexing and source
review expenses are recorded separately from serving operations.

## Evidence

The focused tests exercise all four real graph families, sufficient text,
unsupported graphs, shared-budget escalation, exhaustion, malformed output,
partial-answer retention and missing usage. The original affected API run retains
its policy-compatibility failure; the repaired public rule and isolated API
regression pass. The continuation adds captured-identity admission and actual
API fallback regressions. Validation results are recorded separately from the
source-based development comparison below.

## Development comparison

[The comparison](comparison.json) binds **54 actual responses** to their frozen
references, source/model/policy settings, original contexts and source reviews.
Seven unique questions cover five exposed story groups; repeated deliveries and
the two overlapping source cohorts are not additional independent questions.
There is one observation per case/arm, with answer caching disabled throughout.
The source labels are agent reviews, independently checked on the Spec axis,
not human canon adjudication or held-out acceptance.

The 26-passage legacy cohort exercises all four graph query families and the
multi-part evidence gap. Its original conventional policy configurations remain
visible: fusion falls back with `fanout_budget`, while sentence expansion reports
`source_has_no_ordered_sentences`. These results measure that fallback operating
point. They do not establish active fusion or source-window quality.

| Legacy arm | Completed tasks | Context facts | Paid calls | Reported cost | Mean full transport |
| --- | --- | --- | --- | --- | --- |
| Selected text baseline | 6/7 | 6/7 | 7 | $0.018330 | 4.757 s |
| Fusion configuration | 6/7 | 6/7 | 7 | $0.011627 | 4.209 s |
| Expansion configuration | 6/7 | 6/7 | 7 | $0.013067 | 4.434 s |
| Combined configuration | 6/7 | 6/7 | 7 | $0.012427 | 4.912 s |
| Automatic, baseline text | 7/7 | 7/7 | 5 | $0.014934 | 4.445 s |
| Automatic, combined subset | 3/3 | 3/3 | 5 | $0.008913 | 5.918 s |
| Explicit graph subset | 4/4 | 4/4 | 0 | $0 | 1.265 s |
| Explicit investigation subset | 2/2 | 3/3 | 5 | $0.013060 | 11.673 s |

Routing selects admitted biological, relationship, crime/justice and connection
graphs without a router-model call. The complex-looking sufficient-date question
stays with text, and the unsupported theme abstains without further investigation.
All four conventional arms miss Peggy's parentage in the multi-part family task.
Automatic investigation obtains that missing support and answers both parts.
The simple forced-investigation counterfactual spends additional decisions on an
already sufficient task. These observations support explicit eligibility and
limit rules, with model discretion confined to gathering missing evidence.

The paired routed improvement is one question out of seven, all within one of
five story groups. An illustrative exact group-bootstrap interval is 0–27.3
percentage points; the selected sample is too small for a general routing-quality
claim. [Per-case paired changes](comparison.json), categories, sample counts,
minimum/median/maximum latency and full stage accounting remain available.
The automatic biological-parent request uses the actual CLI, whose process and
transport overhead is included; other requests use HTTP directly.

The separate 147-passage ordered cohort exercises active faithful fusion and
sentence windows on two source-reviewed questions, using the same answer model,
application, source/index and policies in every completed arm. It uses the frozen
$0.30 reservation rather than the legacy $0.20 setting; both use 4,000 context
bytes. Keep these cohorts separate.

| Ordered arm | Completed tasks | Context facts | Paid calls | Reported cost | Mean full transport |
| --- | --- | --- | --- | --- | --- |
| Selected text baseline | 2/2 | 2/2 | 2 | $0.009507 | 5.773 s |
| Fusion | 2/2 | 2/2 | 4 | $0.008780 | 9.470 s |
| Expansion | 1/2 | 1/2 | 2 | $0.011682 | 7.001 s |
| Combined | 1/2 | 1/2 | 4 | $0.009212 | 9.999 s |
| Automatic, baseline text | 2/2 | 2/2 | 2 | $0.006386 | 7.278 s |

All eight generated query variants preserve the original question with reviewed
scope prefixes. Expansion drops the expected Christmas Day 2005 passage and
retains a later pregnancy account involving Louise and Keanu. Both affected
answers accurately describe their cited relative sequence but miss the frozen
required date. The question's unspecified pregnancy is also a reference
limitation. Preserve these failures; **baseline remains the selected policy**.
All 93 legacy factual assertion units and all ten ordered compound-answer units
pass source/citation review; these different assertion denominators are not pooled.
All 54 outcome/qualification and relevance reviews pass, including honest partial
answers. Full required-fact task success remains stricter.

## Interruption, eligibility correction and bounded stop

The original ordered run stopped after four responses. Two trace export files
were empty and the fourth response had not completed verification. Original
PostgreSQL response documents and original MLflow root outputs match all four
saved response hashes. [Recovery](runtime-ordered-recovered-v1/recovery.json)
re-exports the actual traces and resolves citations, with zero inference calls.
It explicitly labels CLI readback of exact document copies in a disposable
database with newly issued read capabilities. Original responses, capabilities,
capture files and damaged exports remain unchanged.
Recovered files retain the original journal's last-flushed progress counters;
the recovery expense record reconciles all four observed responses to 49
cumulative calls and $1.086248 before continuation. Use the final expense report
for the completed comparison, rather than those historical progress fields.

[The continuation protocol](continuation-protocol.md) carries forward every paid
call and the original ledger. Six further responses complete expansion, combined
and automatic-baseline arms. At **57 cumulative paid calls**, the next automatic
request cannot reserve its eight-call maximum under the unchanged 64-call ceiling.
The optional two-response ordered automatic-combined arm stops before execution;
its failed journal and original log remain visible. No allowance is increased or
reset, and no absent response is scored as a success.

The ordered parentage projection also lacked Phil and Kathy in the **captured
reviewed identity catalogue**. Its source-supported claims are correctly held,
so the actual automatic route falls back to text. The v1 eligibility label was
wrong; [v2](../../../data/references/routing-ordered-v2.json) corrects the label
without changing any original response or silently replacing its raw score.
An attempted identity extension was rejected by the existing captured-catalogue
constraint and is retained as failure evidence. No validator was relaxed, no new
identity or graph coverage was admitted, and no paid v2 observation is claimed.
The four graph capabilities are separately demonstrated in the legacy cohort.
New public admission/API regressions and capture preflight prevent this mismatch
from being mistaken for eligible graph coverage in subsequent runs.

All 54 root outputs, archives and recorded CLI readbacks pass the
[integrity check](capture-integrity.json), with the four recovered readbacks
distinguished as above. [Deterministic replay](repair-replay.json) also sends the
44 legacy requests through current API/storage/tools using their recorded
completions at the external HTTP boundary. All model messages, final contexts,
answers, routes, outcomes and citations are unchanged. Replay is software
consistency evidence, with no new model quality/latency observation or paid call.
Its initial export-reader failure remains preserved separately.

## Expense and limits

[Expense](expense.json) records **57 paid calls / $0.137923 reported serving
inference**. Upward reservation settlement rounding adds $0.137942 to the original
ledger, from $0.975588 to **$1.113530**, with zero unsettled reservations. The
non-resetting $5 ledger and the additional $0.75 ceiling remain intact. Local
indexing and source review have zero external inference expense; local compute,
storage and infrastructure cost are unmeasured. Thirteen local MLflow evaluation
runs retain bound source annotations and separate quality dimensions under
[quality-runs](quality-runs).

Every executed request passes its declared operation, tool, HTTP, context and
reservation caps. Stage/provider receipts include all query generation,
checking, fallback and investigation work. Missing usage remains explicit in
the deterministic missing-data regressions. No pricing, latency or quality
result here transfers automatically to the 1,200-byte default operating point.
Full release, held-out thresholds, broader coverage and caching remain subsequent
ticket obligations.

## Software validation

[Validation](validation.json) records **715 passing tests**, zero failures/errors/
skips, in 2,312.754 seconds against disposable real PostgreSQL databases. The
process exits successfully. Strict mypy checks 183 files; Ruff and formatting
pass for `src`, `tests` and `scripts`, and Compose configuration validation passes.
The rebuilt Docker image passes ten
focused routing/admission/API contracts, including the packaged source fixture.
The final [301 frozen software inputs](software-inputs.json) all match.

Both independent [review axes](review.md) have zero remaining findings. The 98
original data files and all 150 protected user/private inputs retain their hashes.
The successful full run retains Prefect's closed-file logging diagnostic during
temporary-server shutdown after the pytest result; it does not change exit status.
Earlier failed/interrupted runs remain available and are not reported as passes.
