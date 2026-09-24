# Issue #3 implementation contract

Review baseline: `573a8ad`. Scope: one single-query, uncached text-RAG answer
over a captured source snapshot. Fusion, caches, conversation history and
feedback submission remain separate tickets.

The already approved public seams in `docs/design/testing-and-evaluation.md`
cover this work: text retrieval, conversation API/CLI and evaluation scorers.
Develop one failing public behavior at a time, with real PostgreSQL/pgvector
and controlled external model substitutes; then run a bounded local-model
baseline. A substituted model test is not model-quality evidence.

Initial provider candidate: local Ollama, Gemma 4 E2B QAT and EmbeddingGemma.
The user authorised a current open model suited to this 8 GB CPU machine.
Pin resolved model digests, package versions, prompt and limits in the result.
No paid API calls are authorised by this local-provider configuration.

The user clarified that the laptop model is a development convenience, not a
deployment or serious quality-testing model. Use its fixed seed run as plumbing
and smoke evidence only. Once this end-to-end path works, recommend and configure
a more capable model before substantial extraction pilots or quality acceptance
on representative datasets. Record that model's own baseline; do not carry over
the local model's results. Paid provider setup still requires a locally configured
key and conservative spending controls before its first paid call.

An answer carries resolvable snapshot-bound citations, separately recorded
retrieved passages and assembled context, neutral provenance and measurements,
an actual MLflow trace, and a durable response identifier. Response lookup must
preserve the original persona answer and execution record across app restarts.
Do not expose assessment-write authority.

The reviewed one-passage seed supplies independent development labels. Report
retrieval and context-sufficiency metrics separately, with explicit denominators,
and retain missing usage as missing. This small, exposed seed cannot establish
general answer quality or corpus-wide coverage.
