# Issue #24 implementation

Starting revision and code-review fixed point: `a9303b4` on `main`.
Specification: GitHub #24 and parent #1 stories S117–S121.

Use the already confirmed text retrieval, conversation API/CLI and evaluation
scorer seams in `docs/design/testing-and-evaluation.md`. Preserve original source
and reference inputs, private inputs, existing workspace changes and the shared
non-resetting $5 inference ledger. Do not repeat historical paid work.

Implement one red/green behavior at a time: independent RRF examples; ordered,
scope-filtered source windows and citation resolution; bounded faithful query
variants and original-query fallback; actual answer/context and stage accounting;
then real PostgreSQL/pgvector API/CLI regressions and four uncached ablations.
The original single-query policy remains reproducible. No lexical retriever,
parent-passage merging, graph traversal, investigation loop or answer cache is
required by this ticket.

Variant validation is deliberately conservative: retain the original resolved
question and all content-bearing identity, date, negation and intent tokens;
allow only a versioned, explicit retrieval synonym vocabulary and fixed scope prefixes.
Unknown or drifting proposals fall back visibly. Labels and source-based reviews
are separate from the model that generates proposals or answers.

The initial bag-of-words validator was rejected after public counterexamples
showed that reordering can swap subject/object or change negation scope. Preserve
`role-negation-red.xml`; the final policy preserves token order as well as content.

Context expansion uses bounded neighbouring sentences from admitted paragraphs
of the same captured document revision and section. Each derived span retains
its source offsets, hash and stable evidence identity and resolves through the
existing citation endpoint. Merge overlapping windows and apply the serialized
context budget to complete spans. Preserve visible dropped/truncated evidence.

Run focused test files and strict typechecking during development. Before final
verification, perform independent Standards and Spec reviews using code-review.
Repair findings and run the complete software suite once at the end. Record
failures, limitations and revision-linked checklist evidence. Commit the issue
scope on the current branch, publish and verify the exact remote tree before
updating or closing the GitHub issue.
