# Frozen development comparison

The original issue #17 text trace missed the second biological family fact;
earlier core-profile traces also retained context/identity misses. Inspecting
those traces identifies retrieval/context coverage separately from generation.
The comparison below extends that failure analysis to the retained, ordered real
Wikipedia paragraphs in `data/sources/real-sources-v1.json.gz`.

References: `data/references/text-fusion-v1.json`. Four exposed development cases
contain six independently source-labelled facts and exact sufficient source
spans. Labels were written before model capture. This is an implementer source
review, not human adjudication, exhaustive passage relevance or independent canon
corroboration. Wrong character, date, removed/moved negation and swapped-role
controls are separately labelled. Structural scope/qualification/overlap tests
remain explicitly synthetic.

Freeze baseline, fusion-only, expansion-only and combined configurations with
the same 147-passage snapshot, local embedding digest, Sol answer profile, prompt,
four original questions, top-three final anchors and 4,000 serialized context
bytes. Use at most two validated variants, three candidates per query, one-based
RRF with constant 60 and evidence-identity ties, and one neighbouring sentence on
each side. Merge overlapping windows; omit entire over-budget windows.

Every request has at most five model operations (including query embeddings),
three retrieval operations, 16 model HTTP operations, 90 seconds and $0.30 in
conservative reservations. Optional query generation gets at most 30 seconds and
one third of remaining request time. The model profile bounds each completion;
at most two generations per request means at most 16,384 output tokens. All
requests together are bounded by 16 answers and eight variant generations, with
a **$0.50 additional ticket cap**, zero retries and the same non-resetting shared
$5 ledger. Preserve unknown usage and unsettled reservations. Indexing is local
and measured separately. No paid extraction or new judge is needed.

Execute one response per case/configuration through the actual API; use the CLI
for the first case of each configuration. Read back original saved answers,
MLflow root/context/stage data and every cited span. Record complete transport
latency separately from `elapsed_ms`. Caching and automatic online judging are
disabled for these offline comparisons; no existing paid result is repeated.

Report original/candidate recall and fused ranking against the selected positive
passage labels, final-context span coverage/sufficiency after truncation, and
independently source-reviewed answer correctness, actual-context grounding,
citation support, required-fact completeness, relevance and answerability.
Unanswerable questions have no factual/retrieval denominator. Missing values
remain unavailable. Record every generated proposal and its independent fidelity
decision, actual calls/tokens/cost, fallbacks and final context.

Select a versioned development policy only if it has no new critical factual,
scope or citation failure, preserves baseline answerability/support, and improves
at least one required fact or supported final-context fact. If measured outcomes
tie, keep the lower-cost/latency baseline. Retain negative results and scoped
regressions. These are development selection criteria, not owner-accepted release
thresholds. One response per question does not estimate stochastic variation.

The two reserved question/story groups are unexecuted and excluded from tuning,
aggregate denominators and policy selection. A future grouped holdout evaluation
and owner acceptance remain necessary for release claims.
