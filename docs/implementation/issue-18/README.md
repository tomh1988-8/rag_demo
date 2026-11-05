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

## Corrected completion status

Issue #18 was initially closed too soon: two runs promised by the frozen ordered
protocol were unfinished and were incorrectly called optional. The issue was
reopened. **Both missing runs are now executed and independently reviewed**;
publication and final tracker readback remain to be recorded before closing again.
The initial [closure account](README-initial-closure.md), [receipt](publication.json)
and [reopening record](reopening.json) remain intact. Their completion claim is
superseded by this report and the [follow-up protocol](reopening-protocol.md).

## Completed development comparison

[Comparison v2](comparison-v2.json) contains **56 actual responses**: 44 legacy
responses and all **12 ordered responses across six arms**. No planned arm remains
unexecuted. All 54 earlier observations are preserved without repeated inference.
The same seven exposed questions overlap five story groups; repeat deliveries and
source cohorts are not additional independent questions. No held-out acceptance
labels or answer caches are used. The source labels are agent reviews, not human
canon or broad release acceptance.

The 26-passage legacy cohort exercises the four graph families and the multi-part
evidence gap. Fusion configurations report `fanout_budget`; expansion reports
`source_has_no_ordered_sentences`. Those are fallback observations, not active
fusion/window results.

| Arm | Strict task success | Context facts | Paid calls | Reported cost | Mean full transport |
| --- | --- | --- | --- | --- | --- |
| Selected text baseline | 6/7 | 6/7 | 7 | $0.018330 | 4.757 s |
| Fusion | 6/7 | 6/7 | 7 | $0.011627 | 4.209 s |
| Expansion | 6/7 | 6/7 | 7 | $0.013067 | 4.434 s |
| Combined | 6/7 | 6/7 | 7 | $0.012427 | 4.912 s |
| Automatic, baseline text | 7/7 | 7/7 | 5 | $0.014934 | 4.445 s |
| Automatic, combined text | 3/3 | 3/3 | 5 | $0.008913 | 5.918 s |
| Explicit graph subset | 4/4 | 4/4 | 0 | $0.000000 | 1.265 s |
| Explicit investigation subset | 2/2 | 3/3 | 5 | $0.013060 | 11.673 s |

Automatic baseline completes the observed missing family fact through one bounded
investigation. Sufficient text and unsupported themes require no investigation.
Four text-only arms retain their missing-Peggy completeness failures. Explicit
graph answers use no paid generation; the forced-investigation subset exposes
the extra discretion/cost on a sufficient task. Per-case changes, categories,
measurements and the illustrative five-group bootstrap remain in the report.

The separate 147-passage ordered cohort exercises active fusion and windows. All
six arms share source/index/publication, application, model/settings, original
questions, prompts and per-request limits: eight model operations, four tools,
24 HTTP operations, 180 seconds, 4,000 context bytes and a $0.30 reservation.

| Arm | Strict task success | Context facts | Paid calls | Reported cost | Mean full transport |
| --- | --- | --- | --- | --- | --- |
| Selected text baseline | 2/2 | 2/2 | 2 | $0.009507 | 5.773 s |
| Fusion | 2/2 | 2/2 | 4 | $0.008780 | 9.470 s |
| Expansion | 1/2 | 1/2 | 2 | $0.011682 | 7.001 s |
| Combined | 1/2 | 1/2 | 4 | $0.009212 | 9.999 s |
| Automatic, baseline text | 2/2 | 2/2 | 2 | $0.006386 | 7.278 s |
| Automatic, combined text | 1/2 | 1/2 | 5 | $0.024316 | 11.426 s |

The new automatic-combined parentage answer is supported by the exact born-to
sentence. The date answer remains **partial**: active windows retain the later
Louise/Keanu pregnancy account and omit the frozen Christmas Day 2005 fact.
Investigation attempts a text search; adding the returned passages would exceed
the shared 4,000-byte context ceiling. It stops with `context_limit` and retains
the initial supported partial answer, including all expense. The existing context
is 2,764 bytes; the stop concerns adding material, not already exceeding the cap.

That is an **executed quality failure**, with 1/2 strict task success for the new
arm. It is not missing evaluation work or a funding failure. The unspecified
pregnancy remains a reference limitation. Expansion, combined and automatic
combined each lose the expected date; **baseline stays selected**. The twelve
accepted prefix variants preserve the original questions. Source/citation reviews
pass all 93 legacy assertion units and all twelve ordered compound-answer units;
these different assertion denominators are not pooled. All 56 qualification/
relevance reviews pass, including honest partial outcomes. Full required-fact
success is stricter and retains every miss.

## Budgets and the premature stop

The first phase stopped at 57 calls because the experiment reserved eight calls
for the next request under an agent-set 64-call ceiling. It did not run out of
money. Closing the issue and relabelling the unfinished arm as optional were
incorrect; [reopening](reopening-protocol.md) explicitly revised that agent-set
ceiling to 73, carrying forward all 57 calls and reserving at most two further
requests. The original $5 non-resetting trial and $0.75 ticket dollar ceilings
were unchanged, as were all application/request limits and earlier records.

The two completed requests actually used **five calls / $0.0243161**. Observed
cumulative usage is **62 calls**, below even the earlier 64-call count. This
finishes the frozen plan; no earlier paid question was repeated or tuned.

[Final expense](expense-v2.json) records **$0.1622391** reported serving inference
for all 56 responses. Conservative rounding advances the original ledger from
$0.975588 to **$1.137848**, with zero unsettled reservations. External indexing
and offline-review inference cost $0; local infrastructure cost is unmeasured.
Fourteen local MLflow review runs retain bound annotations and separate quality
dimensions. The 4,000-byte results do not establish 1,200-byte default quality.

## Identity, recovery and trace integrity

The ordered corpus never admitted Phil/Kathy identities; its parentage claims are
correctly held. Original v1 labels incorrectly expected graph eligibility. The
[versioned correction](../../../data/references/routing-ordered-v2.json) records
actual ineligibility without weakening admission or rewriting old responses/raw
scores. The two new observations use those v2 labels; their presence supersedes
the historical note that no v2 paid observations existed. All four graph families
remain separately exercised by the legacy cohort.

The original interrupted ordered files and damaged exports remain unchanged.
[Recovery](runtime-ordered-recovered-v1/recovery.json) checks original PostgreSQL
and MLflow equality and explicitly labels CLI readback of copied documents with
new capabilities in a disposable database. Historical last-flushed progress
counters are distinct from reconciled expense. [Integrity v2](capture-integrity-v2.json)
verifies all 56 original root outputs/archive hashes and recorded original or
labelled recovered readbacks. All 44 legacy requests also retain exact model
messages, final context, routes, outcomes and citations under current-code
[replay](repair-replay.json), with zero paid inference.

## Software and independent review

[Validation v2](validation-v2.json) retains the successful **715-test** native run
and **ten Docker contracts** because all **301 tested software inputs** remain
byte-identical. No application, maintained recorder, test, dependency or policy
configuration changed in this follow-up. The archived recorder changes only
three cumulative-call guards/metadata and binds the new protocol. Strict mypy
with project roots, Ruff and formatting pass for all 184 checked files, including
that recorder. All 98 original data files and 150 protected inputs retain hashes.

Both [follow-up review axes](review-v2.md) independently verify the new source
reviews, reference/response bindings, original CLI/root equality, accounting,
limits and fair comparison identities. Earlier software/logging failures, source
label mistakes, the premature closure and all current quality misses remain in
[versioned regressions](regressions-v2.json). Completion of this ticket does not
pass the full-product, cache or held-out acceptance obligations in #25/#21.
