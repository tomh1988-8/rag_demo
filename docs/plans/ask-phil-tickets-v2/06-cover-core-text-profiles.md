# 06: Answer from all 20 core character profiles

Status: approved and published as [GitHub #7](https://github.com/tomh1988-8/rag_demo/issues/7), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S05, S11, S12, S13, S14, S15, S16, S19, S38, S41, S42, S55, S56, S57, S62, S64, S76, S80, S86, S88. Checklist evidence owner for: AD-03.4, RAG-01.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S05, S11, S12, S13, S14, S15, S16, S19, S38, S41, S42, S55, S56, S57, S62, S64, S76, S80, S86, S88.

## What to build

Use the established import and text-answer paths for the complete agreed roster rather than creating separate feature tickets for each family. A user can ask representative questions about each core character; a maintainer can inspect source coverage, freshness and gaps. This establishes broad text coverage before claiming broad checked graph coverage.

## Acceptance criteria

- [ ] Process Phil Mitchell, Grant Mitchell, Peggy Mitchell, Sharon Watts, Ben Mitchell, Ian Beale, Kathy Beale, Cindy Beale, Lucy Beale, Bobby Beale, Martin Fowler, Kat Slater, Stacey Slater, Alfie Moon, Pat Butcher, Janine Butcher, Dot Cotton, Denise Fox, Max Branning and Linda Carter through the same import process.
- [ ] Include evidenced supporting characters and relevant earlier history without expanding the definition of the curated core roster. Record this as a prominence-based selection, not a proven ranking or exhaustive canon.
- [ ] Produce a per-character inventory of captured sources, identity resolution, relevant content retention, source-check dates, known coverage and gaps. Examine duplicates and inconsistent accounts across pages; a recent fetch alone does not establish current storyline completeness.
- [ ] Through the API and CLI, demonstrate at least one independently reviewed sourced question for each core profile and representative cross-profile and missing-evidence cases. Measure retrieval/context sufficiency on these cases without claiming exhaustive character histories.
- [ ] Use bounded, restartable import batches under configured limits. Reuse the generic pipeline so adding a further character does not require a family-specific code path.
- [ ] Expand reviewed cases with stable story-event groups before splitting overlapping biographies or paraphrases. Keep deterministic fixture/integration checks separate from budgeted real-source/model results and publish failures alongside coverage.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-01, AD-03.4 | Twenty-profile coverage and source-quality inventory with explicit missing, duplicate, conflicting and stale material. |
| AD-03.1, RAG-02, AD-10.4 | Per-character public answers, retrieval/context results and reviewed coverage-gap regressions. |

Recheck when: Roster/source changes, new snapshot, identity/alias rules, content filters or retrieval changes.

## Blocked by

- #3 — Generate a grounded Ask Phil answer: The text-RAG answer path must be working.
- #6 — Refresh and recover a captured snapshot: The real-source pipeline must publish reproducible snapshots before roster expansion.

