# Independent code review

Fixed point: `a9303b4c2678fa9df1e5bd0524a3b7eabbf999ae`.
Initial diff: `git diff a9303b4...8c7dd56`.
Commit: `8c7dd56 Implement bounded text fusion and source windows (#24)`.
Both axes then reviewed the working-tree repair diff against that checkpoint.
The [frozen final inputs](software-inputs.json) identify the reviewed implementation
submitted to the final complete suite.

The reviewers were independent read-only sub-agents. They did not edit files,
rerun the full suite or make paid model calls. Standards sources were AGENTS.md,
CONTEXT.md, applicable ADRs, the confirmed testing/evaluation strategy,
pyproject.toml and the code-review smell baseline. Spec sources were the retained
live issue #24 and parent #1, S117–S121. Final-suite and publication work follows
review and was not treated as a missing code requirement.

## Standards

No documented-standard violations or meaningful baseline smells found in the
initial diff. The tests exercise the confirmed public boundaries, use real
PostgreSQL/pgvector and substitute at external model-service boundaries. Fusion
expectations use independently worked examples. Sentence windows retain captured
revision provenance and resolvable citations, consistent with ADRs 0004 and 0006.

The evaluation records separate retrieval, context, answer quality and expenditure;
preserve negative results; and explicitly limit conclusions to exposed development
cases, as required by `docs/design/testing-and-evaluation.md`.

The repair review found no remaining Standards findings. The regressions test
observable query-validation and API-appendix behavior at the agreed seams.
`with_final_context` centralizes context accounting and retained/dropped
reconciliation without introducing a meaningful baseline smell.

**Standards: 0 findings; baseline smells: 0 findings.**

## Spec

**No remaining Spec findings.** No additional missing requirements or scope creep
found. Three confirmed defects are repaired:

- **P2 — date drift admitted as faithful.** The spec requires “distinct faithful
  variants” and drifting generation to use “original-query fallback.” Originally,
  `Was Phil imprisoned in 1990-1992?` admitted
  `EastEnders: Was Phil imprisoned in 1990, 1992?`, changing a range into an endpoint
  list. The repaired validator preserves punctuation and rejects this proposal.
  Independently replayed all sixteen recorded proposals: complete decisions remain
  unchanged. [Original failure](date-range-red.xml), [passing checks](date-range-green.xml).
- **P3 — retained evidence reported as dropped.** The spec requires “an honest
  text-route appendix” retaining “truncation, fallback.” The classification API case
  originally reported `phil-test-0000-0` in both `final_context_ids` and
  `dropped_evidence_ids`. Shared final-context reconciliation now removes retained
  canonical IDs from the dropped list and records exact final IDs/serialized size
  at assembly and final answer reconciliation. [Original failure](appendix-overlap-red.xml),
  [19 passing public regressions](review-regressions-green.xml).

- **P2 — exhausted budget with more supporting spans than citation capacity.**
  The spec requires exhausted limits to preserve partial/abstain behavior. An
  API request with 22 expanded spans and one model operation originally returned
  HTTP 500. The shared citation limit now produces an assertion-free abstention
  when complete support cannot fit, while preserving the full context. The
  reviewer independently checked 20 spans produce a cited partial reply and
  21/22 produce uncited abstention without mutating original support.
  [Original failure](citation-cap-red.xml), [37 passing affected cases](citation-cap-green.xml).

The preserved public regressions fail before these repairs and pass afterward.
The reviewer independently confirmed final reconciliation leaves all sixteen
preserved runtime context records unchanged.

The source audit rebuilt the 147-passage snapshot and checked sufficient-span
labels, 156 context/citation spans, actual answer support, sixteen original root
outputs and answer-model question/context inputs. Comparison controls match,
caching is disabled, recorded limits hold, and individual receipts total
**24 calls/$0.061936**. Review used no paid calls.

Both Ben-context losses and the three strict Stella completeness misses remain
transparent negative development results. Baseline selection, label limitations
and unexecuted holdout status are reported honestly; they are not additional
implementation defects.

**Summary: Standards 0 findings; Spec 0 remaining findings, with two P2 findings
and one P3 repaired and independently verified.**

The [repair replay](review-repair-replay-v2.json) binds all sixteen unchanged context
records and sixteen unchanged query decisions to the final implementation.
The paid captures remain tied to their original application and checkpoint
`8c7dd56`; deterministic replay is not fresh answer generation or a claim of new
model-quality measurements on the repaired revision.

## Interrupted verification investigation

The first complete-suite attempt stopped after 155 recorded cases (one failure,
five setup errors) with inconsistent capture hashes and one invalid JSON result.
These failures occurred before the changed fusion/window pipeline; source,
fixture, storage validators and dependency pins were unchanged. All original
source-file hashes match. Independent read-only checks passed 40 serial and 80
concurrent Pydantic parses, two fresh fixture builds/revalidations and 12
PostgreSQL JSONB round-trips checking 240 capture strings/hashes. A fresh-process
conversation-file run passed all 16 cases. The cause remains unproven; no source
or validator change was inferred or made. Both the original failure and pytest's
interruption cleanup diagnostic are retained. The final retry uses a bounded
local diagnostic hook to preserve failing source bytes if the anomaly recurs.
