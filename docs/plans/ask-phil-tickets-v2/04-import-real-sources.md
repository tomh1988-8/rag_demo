# 04: Import real sources with character identity and canon scope

Status: published as [GitHub #5](https://github.com/tomh1988-8/rag_demo/issues/5); fusion/cache scope amendment requested on 23 September 2026. Publication readback is recorded in the manifest. Implementation has not started.

Spec stories: S12, S13, S14, S19, S30, S41, S42, S56, S57, S58, S67, S72, S73, S74, S76, S79. Checklist evidence owner for: AD-03.2, EXT-01.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S12, S13, S14, S19, S30, S41, S42, S56, S57, S58, S67, S72, S73, S74, S76, S79.

## What to build

Bring a representative small set of Wikipedia narratives, Wikidata identity records and TVmaze episode metadata into the captured-evidence path. A maintainer can inspect what was retained, filtered or missing and how it resolves to characters. Use ordinary HTML/JSON ingestion; require demonstrated input needs before introducing specialised extraction services.

## Acceptance criteria

- [ ] Record source roles, permitted uses/attribution, access constraints and freshness expectations. Treat Wikipedia as narrative evidence, Wikidata as identity linkage and TVmaze as metadata; agreement of identifiers or episode dates is not independent plot corroboration.
- [ ] Resolve reviewed aliases to stable character identities while distinguishing performers/recasts. Include supporting characters when evidence requires them and retain relevant pre-1990 history for the eligible roster.
- [ ] Apply main-series scope at passage level, including mixed pages containing spin-off, podcast, performer or production material. Retain exclusions and reasons so lost narrative content can be distinguished from intentional filtering.
- [ ] Preserve source revision, captured content, structured records, passage identifiers and evidence links. Do not convert broadcast/publication/capture dates into event dates.
- [ ] Inspect representative real inputs before fixing parsing rules. On reviewed source fixtures, report retained relevant content, exclusions, missing records, duplicates and provenance integrity separately from semantic extraction. PDF/OCR metrics are not applicable to the initial HTML/JSON inputs.
- [ ] Start from failing alias/scope/retention examples. Unit-test exposed identity and scope rules; integrate real PostgreSQL and API/CLI evidence inspection, using controlled external-source responses including malformed and incomplete input. Keep a separately recorded live compatibility check.
- [ ] Retain ordered passage/span relationships and enclosing source-section identity within each captured revision, including scope exclusions. Later sentence-window expansion must recover legitimate surrounding context without reintroducing excluded spin-off or production material. The later fusion ticket owns expansion behavior and its answer-quality evaluation.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-03.2, RAG-01 | Source inventory, permitted-use/access notes, role distinctions and scope inspection results. |
| EXT-01, AD-03.4 | Reviewed parsing/content-retention and provenance report with missing, duplicate and mixed-canon examples. |

Recheck when: Source formats, terms/access constraints, roster or canon scope, identity mappings, parsing/filtering rules or specialised parser proposals.

## Blocked by

- #2 — Inspect captured source evidence locally: Source adapters need the working captured-evidence inspection and provenance contract; generated answers are not required.

