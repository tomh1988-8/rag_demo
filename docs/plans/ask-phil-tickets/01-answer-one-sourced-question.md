# 01: Answer one sourced question locally

Draft for breakdown review; not approved or published.

Spec story references: 1, 2, 6, 38, 43, 44, 45, 46, 47, 54, 55, 58, 66, 67, 69, 70, 71, 72, 73, 74, 75, 79, 80, 84, 89, 94, 95, 98.

## What to build

A developer can start the local demonstration, import one reviewed main-series source fixture, ask a supported question in the CLI, and receive a source-backed answer in Phil's initial voice with a neutral execution appendix. Keep this first path deliberately small: one source fixture and a tiny reviewed question set establish the application and evaluation contracts that later slices extend.

## Acceptance criteria

- [ ] Before the first model-driven implementation, prepare independently reviewed source excerpts and expected answer facts, citations, and answerability for the seed questions; candidate demonstration questions are not automatically gold.
- [ ] Run an actual Python/LlamaIndex text-RAG path: captured passage and revision persisted in PostgreSQL/pgvector, relevant context retrieved, and an answer returned through FastAPI to the CLI. The result must not be a hard-coded answer or a mocked internal pipeline.
- [ ] Start the required local services reproducibly with Docker Compose. Record selected package/model/provider versions and require explicit conservative API settings for budgeted live runs; do not invent a fixed monetary commitment in the ticket.
- [ ] Persist resolvable evidence and identify the captured snapshot. The CLI displays the supported answer, citations, actual text route, source-check information, relevant coverage limits, and elapsed time; detailed inspection exposes real trace/usage data, with missing or estimated values labelled.
- [ ] Use Phil's initial speech style while preserving the reviewed facts and qualifications. Keep the appendix neutral and apply no spoiler or audience-reveal restrictions.
- [ ] Run the seed questions as an always-text-RAG baseline, recording context, reference facts, citation checks, initial retrieval results, model configuration, elapsed time, and available serving cost in MLflow. Separate evaluation expenditure from serving expenditure.
- [ ] Demonstrate one complete question and inspect the corresponding captured evidence and evaluation result. Defer broad corpus coverage, graph tools, automatic routing, multi-turn behavior, and advanced judge calibration to their listed slices.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

None (can start immediately).

