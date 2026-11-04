# Issue #24: bounded fusion and source context

The conventional text route now supports versioned multi-query reciprocal rank
fusion and captured-source sentence windows through the existing API and CLI.
The selected default remains the single-query baseline: the measured candidates
did not provide a reliable improvement on this development sample.

[Issue #24](https://github.com/tomh1988-8/rag_demo/issues/24) is complete and closed
after [native fast-forward publication](https://github.com/tomh1988-8/rag_demo/commit/a737c7fa6bcb0a30b785c04acb70be339d35e337),
exact remote commit/tree verification and readback of all eight checked criteria.
The [publication receipt](publication.json) and [completed tracker body](tracker-update.md)
retain that readback. The final receipt/handoff changes are documentation only;
the 184 frozen tested inputs remain unchanged.

Starting revision/review fixed point: `a9303b4` on `main`. The [ticket](issue.json)
and [parent specification](parent-spec.json) retain S117–S121. Dependencies #4 and
#5 were read back as closed. [Implementation plan](run-plan.md) and
[pre-call protocol](protocol.md) record the agreed seams and comparison controls.

## Using the policies

Set these variables on the API process, then use `ask-phil ask` normally:

```sh
export ASK_PHIL_TEXT_POLICY=config/text-combined.json
export ASK_PHIL_EXECUTION_POLICY=config/text-comparison-execution.json
```

`text-baseline.json`, `text-fusion.json` and `text-expansion.json` select the other
ablations. With no policy variable, the established baseline and its existing
request limits apply. The comparison execution file supplies the measured 4,000-byte ceiling,
five model operations, three retrievals, 16 HTTP operations, 90 seconds and $0.30
in conservative reservations. The global non-resetting $5 ledger still applies.
The default 1,200-byte context is a different operating point; the 4,000-byte
quality observations below are not a claim about that default ceiling.

Fusion generates at most two distinct faithful variants and retains the resolved
original. A conservative vocabulary and fixed main-series search prefixes
preserve word order, names, dates, roles, intent and negation. Invalid proposals,
failure or insufficient remaining fan-out capacity use visible original-query
fallback. Optional inference has a shorter deadline while calls and unresolved
spending reservations remain charged. There are no model retries.

Each query retrieves at most three vector candidates. RRF uses one-based ranks,
constant 60, evidence identity deduplication and deterministic evidence-ID ties.
The SQL tie is applied before top-k. Original/proposed queries, individual ranked
lists, all fused candidates and per-query ranks remain inspectable.

Expansion takes one neighbouring sentence on each side within the same admitted
document revision and section. It never crosses excluded/held paragraphs. Stable
derived citation IDs retain exact offsets, text hashes and source provenance and
resolve through the existing evidence endpoint. Overlapping windows merge;
complete windows must fit the serialized context budget. Omitting an entire
window keeps a qualification attached to its claim. Legacy sources without
ordered spans fall back visibly. Reviewed source annotations retain complete
canonical evidence rather than acquire a new interpretation through expansion.

The neutral `text_pipeline` appendix records actual variants, rankings, windows,
added spans, truncation/fallback, final context identity and size, stage timings,
individual model executions, query-embedding usage and disabled caching. Answer
generation receives the original/resolved question and the actual final context.
Multiple provider receipts remain individual; request totals include variant
generation, failures and embeddings. Missing usage/cost remains unavailable.
No graph traversal, investigator loop, lexical retriever or live-web context was
added to this route. Sentence segmentation uses a versioned punctuation rule;
abbreviations can split into separate exact spans and increase metadata overhead.

## Measured development comparison

[Frozen references](../../../data/references/text-fusion-v1.json) contain four
real-source development questions, six facts, exact sufficient spans, independent
query-fidelity controls and two unexecuted reserved story groups. All four modes
share the 147-passage source/index, Sol model/settings, answer prompt, original
questions and final-context ceiling. Every response has exact original CLI and
root-trace readback, resolvable citations, and a check of actual answer-model
question/context inputs. MLflow timestamp formatting is normalized through the
captured-source schema when comparing the context-output span.

| Mode | Sufficient context | Context facts | Completed tasks | Literal fact labels | Paid calls | Cost | Mean complete transport |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 3/3 | 6/6 | 4/4 | 5/6 | 4 | $0.0138503 | 6.34 s |
| Fusion | 3/3 | 6/6 | 4/4 | 6/6 | 8 | $0.0181825 | 9.62 s |
| Expansion | 2/3 | 5/6 | 3/4 | 4/6 | 4 | $0.0162524 | 6.77 s |
| Combined | 2/3 | 5/6 | 3/4 | 4/6 | 8 | $0.0136508 | 10.68 s |

Candidate and final-anchor recall and MRR are 1.0 on the three answerable cases;
the unsupported theme has no retrieval/factual denominator. All **31 asserted
story claims** pass source-based correctness, actual-context grounding and
citation-support review. All sixteen outcome/relevance assessments pass; partial
family answers are honest for their supplied context but fail task completion.
This is agent source review, not human canon adjudication or broad reliability.

Expansion's serialized identifiers/source titles consume enough budget to omit
Ben's complete family window. Both failures remain in [the regressions](regressions.json).
The first Stella fact label also requests the nature of Ben's false allegation,
beyond the why/who question. Only fusion repeats that detail; the other three
answers identify the lie and liar but fail the literal completeness label. The
original labels, strict failures and this sensitivity are preserved. Clarify that
label before holdout acceptance. A single extra detail on an exposed case does
not justify activating the slower policy. These observations select baseline;
they do not establish that fusion or expansion can never help another workload.

The [comparison](comparison-summary.json), [stage metrics](stage-metrics.json),
[query review](query-fidelity-review.json), [trace audit](trace-audit.json) and
four response-bound `*-annotations.json`/`*-quality.json` files separate retrieval,
context, answer and expenditure dimensions. Sixteen actual proposed variants pass
independent fidelity review. The [runtime directory](runtime-v1) preserves all
sixteen responses, losslessly compressed raw traces, frozen inputs and four MLflow comparison run IDs;
four separate MLflow review runs contain the source annotations and scores. The
[archive manifest](runtime-v1/artifact-manifest.json) binds compressed archives
to their original bytes. `evaluate_text_fusion.py score` reads either raw or
archived captures; the exact original capture script is archived separately.

The 24 paid calls cost **$0.061936**. The shared ledger moves from **$0.913644** to
**$0.975588**, including conservative rounding, with **zero unsettled reservations**.
Local indexing and source-based review incur no paid inference. These are serving
executions captured in an offline comparison; their receipts retain the actual
serving expenditure category. No existing paid result was repeated. One response
per case/configuration does not estimate stochastic variation. Reserved questions
were not executed; no held-out release or owner-threshold acceptance is claimed.

## Software verification

The final complete suite passes **679 tests**, with zero failures, errors or skips,
in **2,176.53 seconds**. The process exits successfully. Strict mypy checks
**172 files** (including the retained issue #9 helper); Ruff, formatting and
Compose configuration validation pass. The final focused ticket set contains
20 cases; its citation-cap/answer-rule run passes 37 cases. The earlier affected
legacy retrieval, answer and classification run passes 43 cases.

Red/green artifacts preserve independently worked rank examples, duplicate votes,
pre-LIMIT ties, qualification truncation, citation resolution, drift, fan-out,
transport recovery, source classifications and secondary-query failures. Real
PostgreSQL/pgvector, local MLflow and actual CLI HTTP calls are used; routine
substitutes are at external model boundaries.

Both [independent review axes](review.md) have zero remaining findings. Three
confirmed defects were repaired: punctuation-dependent date drift, an appendix
that marked retained canonical evidence as dropped, and HTTP 500 on exhausted
inference when expanded support exceeded citation capacity. The final stop reply
abstains without uncited quotations while preserving the full captured context.
All sixteen recorded query proposals and sixteen complete context records are
unchanged under [deterministic replay](review-repair-replay-v2.json), with no
additional paid calls. The live calls remain bound to checkpoint `8c7dd56` and
application fingerprint
`098b693923b6ad7513c41f14630aa4c12e48271cc1c3b0ba895712b027636cf6`;
replay is not fresh model-quality evidence on the repaired revision.

The interrupted initial suite recorded one failure and five setup errors in
unchanged retained-source parsing/storage, before the fusion/window pipeline.
All original source-file hashes match. Independent serial/concurrent parsing,
fresh fixture and PostgreSQL round-trip probes passed; the isolated conversation
file then passed all 16 cases. The cause remains unproven and is retained in
[the regressions](regressions.json), the interrupted XML/log and the review.
The final complete retry has no source-integrity failure or diagnostic payload.
Prefect emitted its previously observed closed-file logging diagnostic during
shutdown after the passing result; it did not change the exit status.

All **184 frozen software/verification inputs** match the tested bytes. All
**97 original data files** and the user's pre-existing workspace/private inputs
are preserved. The complete private-input audit stays local; the published
[preservation record](preserved-inputs.json) includes counts and tracked data
hashes. [Validation](validation.json), [full XML](software-tests.xml),
[execution log](software-tests.log) and [acceptance map](acceptance-map.json)
record the final checks. Global register counts remain **40 Pass / 11 Pending**;
routing, cache and owner-accepted release/holdout obligations remain subsequent work.
