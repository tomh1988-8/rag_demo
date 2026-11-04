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
`automatic_offline_evaluation`. The comparison uses its separately frozen
4,000-byte/$0.20 operating point. These are different operating points.

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
regression pass. Final full-suite, independent review and live development
comparison results are recorded below when complete.
