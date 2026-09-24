# RAG fusion, wider context and repeated-question caching

Researched 23 September 2026 for the user's explicit specification/ticket amendment.

## Terminology and primary sources

**RAG-Fusion** expands a question into several search queries, retrieves for each,
then combines ranked results using reciprocal rank fusion before answer synthesis.
That definition comes from the [RAG-Fusion paper](https://arxiv.org/abs/2402.03367).
RRF combines rankings; it does not supply independent facts or confidence scores.

[LlamaIndex's current fusion example](https://developers.llamaindex.ai/python/framework/integrations/retrievers/reciprocal_rerank_fusion/)
exposes query generation and reciprocal-rank merging through `QueryFusionRetriever`.
It can combine several retrievers; multi-query vector retrieval alone is sufficient
for our initial design. A keyword retriever remains a measured optional extension.

The user's description of adding surrounding information most directly matches
**post-retrieval context expansion**. LlamaIndex's
[sentence-window example](https://developers.llamaindex.ai/python/examples/node_postprocessor/metadatareplacementdemo/)
retrieves focused sentences and supplies neighbouring text to the answer model.
Its [auto-merging retriever](https://developers.llamaindex.ai/python/framework/integrations/retrievers/auto_merging_retriever/)
can instead replace groups of child chunks with their parent context. We choose
bounded sentence windows first and retain the original and expanded span identities.
This addresses the intended wider context while keeping fusion's meaning precise.

A [2026 retrieval-fusion study](https://arxiv.org/abs/2603.02153) reports that raw
recall gains can disappear after reranking and context truncation under its tested
constraints. We therefore require component and final-answer comparisons rather
than treating more retrieved passages as an automatic improvement.

[Redis's semantic-cache documentation](https://redis.io/docs/latest/develop/use-cases/semantic-cache/)
distinguishes exact response reuse, semantic matching of similar questions and
provider prompt-prefix caching. Semantic matching needs threshold calibration and
hard compatibility boundaries. Its [ADK integration guide](https://redis.io/docs/latest/integrate/google-adk/semantic-caching/)
also illustrates limiting reuse to a session's first message and excluding errors.
These are pattern references, not a decision to adopt Redis or ADK.

## Project decisions and placement

The following choices are project-specific engineering decisions informed by those
sources, not claims that the vendors prescribe our architecture.

- Add multi-query RRF and sentence-window expansion to the conventional text route,
  within the existing retrieval, API and evaluation boundaries. No agent loop,
  graph traversal or query-time web lookup is introduced.
- Keep the original single-query baseline. Compare baseline, fusion only,
  expansion only and the combination under comparable context budgets. Include
  query drift, contradictions, misplaced qualifiers and scope leakage in reviewed
  data; save the final context as well as candidate lists.
- Place this complete CLI-to-answer enhancement in plan 23 after text answering, incomplete-evidence handling
  and real-source ingestion. Source ingestion retains ordered, scoped span
  relationships; the fusion ticket owns actual expansion and its evaluation.
- Add plan 24 for an exact-match application answer cache after fusion, snapshot
  refresh and the online review loop. PostgreSQL fits the existing footprint;
  capacity/expiry and compatibility checks are explicit requirements. Redis can
  be reconsidered if measured concurrency or latency warrants another service.
- Cache only eligible standalone text requests initially. Version entries by
  evidence and behavior configuration, retain citations, invalidate incompatible
  entries and issue a new serving identity for every delivery. Feedback and online
  evaluation include cache hits; related deliveries share generation lineage.
- Semantic matching is a later gated extension: paraphrases are useful but similar
  questions can ask about different parents, dates, crimes or allegations. Exact
  matching comes first; neither embedding similarity nor TTL alone proves reuse safe.
- Full-product acceptance requires both additions. The deterministic issue #2 stays
  complete; its fixture and acceptance evidence are unchanged. No fusion/cache
  runtime results are claimed by this planning amendment.

## Evaluation contract

Fusion: independently labelled query fidelity, candidate recall and merged ranking;
source-window scope/provenance; sufficient evidence after truncation; supported
final answers; total calls, tokens, elapsed time and model cost. Fix rank/tie rules
and configured caps before comparisons. Variant failures have an observable fallback.

Caching: hit rate among eligible requests, all-request hit coverage, incorrect/stale
reuse rates with stated denominators, evidence validity, current-request latency/cost,
and new-response feedback/online assessments. Separate cold/warm workload experiments
from cache-disabled quality runs; isolate partitions and never prefill from held-out
labels. Enable semantic matching only after labelled near-miss checks and calibration.
