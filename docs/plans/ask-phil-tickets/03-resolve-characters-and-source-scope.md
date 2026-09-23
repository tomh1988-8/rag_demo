# 03: Resolve characters and keep sources in scope

Draft for breakdown review; not approved or published.

Spec story references: 10, 13, 14, 19, 56, 57, 58, 76, 78.

## What to build

A viewer can ask about a character using a supported alias and obtain main-series evidence about the intended fictional person. A maintainer can ingest a small representative source set and inspect the identity mappings, retained passages, and exclusions that determine what the viewer can ask.

## Acceptance criteria

- [ ] Ingest representative Wikipedia narrative material through ordinary HTML parsing and retain source identity, revision/content, sections or spans, and capture information. Keep the captured-input workflow available for reproducible tests.
- [ ] Use Wikidata primarily for identity links and TVmaze for episode metadata through representative JSON records; narrative claims must not gain corroboration status merely because identifiers or metadata agree.
- [ ] Resolve reviewed character aliases consistently across import and questions; distinguish fictional characters from performers and make unresolved identity ambiguity visible through the API and CLI.
- [ ] Filter scope at passage level when a page mixes main-series material with spin-offs, podcasts, performer details, or production context; keep relevant pre-1990 history for eligible characters.
- [ ] Expose retained versus excluded content and parsing losses for inspection, separately from later semantic extraction errors.
- [ ] Measure passage/record retention, omissions, duplication, exclusion errors, identity accuracy, and provenance on reviewed HTML/JSON fixtures, then demonstrate the resulting alias-based answer.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 01: Answer one sourced question locally

