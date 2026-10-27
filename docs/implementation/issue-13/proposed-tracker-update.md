## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S24, S25, S29, S30, S33, S34, S38, S39, S58, S59, S60, S61, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Introduce a narrow shared-event/participant query through a reviewed crime and criminal-justice case. A user can ask what happened and who was involved without treating accusation or conviction as proof of actual guilt. This supplies the event-participant path later life-event and connection questions can extend.

## Acceptance criteria

- [x] Review realistic source claims for actual commission, allegation/accusation, arrest, trial, conviction, acquittal, imprisonment and release, using distinct event and participant roles. Include false accusation or false confession counterexamples.
- [x] Require narrative support for actual commission independent of whether the character was caught or punished. Being charged, convicted, jailed, acquitted or present at court alone is not substituted for an assertion of guilt or innocence.
- [x] Keep events, roles, timing and evidence linked. Distinguish exact/approximate/relative/unknown dates and supported changing accounts; ambiguous claims are held or qualified.
- [x] Return shared-event participants and a supported crime/justice explanation through the API and CLI, with typed graph results and citations. An empty legal-history result never establishes that a character did not commit a crime.
- [x] Begin with failing guilt/role counterexamples. Unit-check public role and admission rules and integrate real stored claims, graph queries and user responses. Preserve respectful factual wording for serious harm.
- [x] Report extraction errors by identity, role, direction, negation and timing separately from schema validity and grounding; evaluate final answers for the forbidden guilt conflations. Link reviewed failures to regressions and actual trace artifacts.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| EXT-02, EXT-03, RAG-04 | Independently reviewed crime/justice roles and supported shared-event graph results. |
| AD-06.3, AD-08.4 | False-accusation/confession and guilt-versus-legal-outcome regression results with critical failures explicit. |

Recheck when: Crime/justice role definitions, new evidence/corrections, extraction/admission rules or shared-event queries.

## Blocked by

- #11 — Answer biological family questions from admitted claims: Claim admission, identity and typed graph answers must exist before introducing role-sensitive event answers.

## Implementation and measured acceptance

Published implementation and evidence: [commit 3cde590](https://github.com/tomh1988-8/rag_demo/commit/3cde5901eee0ae5d6fe80412876434a0865a3aa6). [Evidence and usage](https://github.com/tomh1988-8/rag_demo/blob/3cde5901eee0ae5d6fe80412876434a0865a3aa6/docs/implementation/issue-13/README.md), [validation](https://github.com/tomh1988-8/rag_demo/blob/3cde5901eee0ae5d6fe80412876434a0865a3aa6/docs/implementation/issue-13/validation.json), [independent reviews](https://github.com/tomh1988-8/rag_demo/blob/3cde5901eee0ae5d6fe80412876434a0865a3aa6/docs/implementation/issue-13/review.md).

- `EventQuery` exposes bounded shared incidents and their stage-specific participant roles through the read-only API and CLI. Commission requires separately reviewed narrative support; accusation, confession and legal outcomes never establish guilt or innocence. Exact/approximate/relative/unknown timing remains explicit. Empty histories are qualified.
- Seventeen source assertions precede the one extraction pilot. A versioned post-pilot source correction restores five relative qualifiers without changing original labels or raw output. All six excerpt origins, identities, roles and source support were independently checked.
- The raw pilot is schema-valid with four candidates and three exact normalized matches: precision 3/4, recall 3/17, F1 2/7. Three locators resolve and one meets the conservative full-reference-span grounding proxy. Two raw assertions are admitted; the malformed false confession and incomplete commission are held. These quality failures remain regressions.
- The reviewed projection retains all four raw candidates and adds seventeen corrected source-reviewed assertions. Two duplicate supports remain in the typed audit and share prose. This is curated capability, not successful automatic extraction, held-out or canon acceptance.
- [Twenty-four actual API/CLI/session outcomes](https://github.com/tomh1988-8/rag_demo/blob/3cde5901eee0ae5d6fe80412876434a0865a3aa6/docs/implementation/issue-13/runtime-accepted.json) have exact MLflow root/tool and citation readback. The curated phase has nine partial and three insufficient-evidence outcomes; the raw phase has two partial and ten insufficient-evidence outcomes. All seventeen reviewed assertions, five corrected timing qualifiers, false-confession/framing cases, empty/unknown/bounded/context stops, reset and saved-response restart are exercised. Zero forbidden guilt conflations were found.
- The final software suite passed **388 tests**, zero failures/errors/skips. Strict mypy across 90 files, Ruff/formatting and both independent review axes pass with zero remaining findings. The first full run's concurrent-session failure is retained; a controlled slow-model/deadline regression protects its reviewed fix. Source revision `cc34208` and application fingerprints bind all final evidence.
- The one offline model call cost **$0.030536**. Serving made zero inference calls. The preserved shared non-resetting $5 ledger is **$0.417335**, zero unsettled reservations. All 31 original tracked data inputs and 51 pre-existing workspace files were hash-checked unchanged.

Scoped EXT-02/03, RAG-04, AD-06.3 and AD-08.4 results are in the project register, with [retained failures and limitations](https://github.com/tomh1988-8/rag_demo/blob/3cde5901eee0ae5d6fe80412876434a0865a3aa6/docs/implementation/issue-13/regressions-final.json). Wider graph, corrections, held-out and release obligations keep their existing Pending status. #14 is next after closure; another ticket waits for the user's next implementation instruction.
