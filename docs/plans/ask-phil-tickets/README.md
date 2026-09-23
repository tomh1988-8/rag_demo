# Ask Phil: superseded ticket breakdown (version 1)

Status: superseded on 23 September 2026 by the [checklist-based version 2](../ask-phil-tickets-v2/README.md). This earlier proposal is retained for history; its 19 issue bodies were never published. Use version 2 for the current review and eventual publication.

Source: the [agreed specification](../../specs/ask-phil.md), the confirmed design and testing strategy, the domain glossary, and active architecture decisions. The source spec is currently local, so the issue drafts omit a tracker parent reference.

The repository has no application code to prefactor. Each ticket delivers a narrow working behavior through the relevant public application path and includes its own reviewed cases, unit/integration checks, and component/end-to-end evaluation. Existing confirmed test boundaries remain in force.

Exact models/providers, versions, numerical limits, and informed acceptance thresholds remain setup/pilot choices. The first slice requires reviewed seed cases and conservative configured limits; testing and evaluation are not postponed to the final ticket.

## Proposed slices

1. **[Answer one sourced question locally](01-answer-one-sourced-question.md)**  
   **Blocked by:** None; can start immediately.  
   **What it delivers:** Run a narrow text-RAG path from a reviewed captured source through PostgreSQL, FastAPI, and the CLI, returning Phil's answer, citations, and a recorded baseline.

2. **[Handle incomplete evidence and false premises](02-answer-with-incomplete-evidence.md)**  
   **Blocked by:** 01.  
   **What it delivers:** Return supported partial answers, challenge evidenced false premises, and abstain honestly when the captured corpus cannot answer.

3. **[Resolve characters and keep sources in scope](03-resolve-characters-and-source-scope.md)**  
   **Blocked by:** 01.  
   **What it delivers:** Import a small real source set, resolve aliases to characters, and exclude performer, spin-off, and podcast material from answers.

4. **[Refresh the corpus without losing provenance](04-refresh-versioned-corpus.md)**  
   **Blocked by:** 03.  
   **What it delivers:** Run a manual Prefect refresh, publish a usable snapshot, and keep answers reproducible through reruns and failed imports.

5. **[Ground follow-ups and reset conversations](05-ground-followups-and-reset.md)**  
   **Blocked by:** 02, 03.  
   **What it delivers:** Resolve conversational references, ask useful clarification questions, retrieve fresh evidence for each answer, and reset the session.

6. **[Inspect calibrated evaluations of chat answers](06-inspect-calibrated-answer-evaluations.md)**  
   **Blocked by:** 02.  
   **What it delivers:** Run reviewed chat cases through the API and inspect separate deterministic scores and calibrated LLM judgments in MLflow.

7. **[Answer biological family questions from checked claims](07-answer-biological-family-questions.md)**  
   **Blocked by:** 03.  
   **What it delivers:** Extract a small set of parentage claims, admit supported relationships, and answer ancestry/descendant questions with graph evidence.

8. **[Review disputed claims and explain corrections](08-review-disputes-and-corrections.md)**  
   **Blocked by:** 04, 07.  
   **What it delivers:** Inspect held claims, apply supported corrections, and keep current answers, earlier evidence, and unresolved disagreements consistent.

9. **[Explain family and romantic relationship histories](09-explain-relationship-histories.md)**  
   **Blocked by:** 07.  
   **What it delivers:** Answer step/adoptive ties and marriage, separation, divorce, affair, and remarriage questions with supported histories and timing.

10. **[Explain story events, crimes, and justice roles](10-explain-events-and-justice-roles.md)**  
   **Blocked by:** 07.  
   **What it delivers:** Answer shared-event questions while separating actual crime commission, accusation, trial, conviction, imprisonment, and other participant roles.

11. **[Trace evidenced connections between characters](11-trace-character-connections.md)**  
   **Blocked by:** 09, 10.  
   **What it delivers:** Explain bounded paths through supported relationships and shared events, with evidence and meaning preserved at each step.

12. **[Keep Phil's voice faithful to the evidence](12-preserve-facts-in-phil-voice.md)**  
   **Blocked by:** 06.  
   **What it delivers:** Validate Phil-style answers against neutral facts and uncertainty, including self-serving wording and respectful treatment of serious harm.

13. **[Investigate with bounded text and graph tools](13-investigate-with-bounded-tools.md)**  
   **Blocked by:** 02, 11.  
   **What it delivers:** Run an explicit agentic route that combines captured text and typed graph evidence, stops at limits, and shows its actual tools and findings.

14. **[Route questions and escalate on evidence gaps](14-route-and-escalate.md)**  
   **Blocked by:** 13.  
   **What it delivers:** Choose eligible routes automatically, check their evidence, and escalate within limits while reporting quality, cost, and fallbacks.

15. **[Cover the Mitchell and Watts core characters](15-cover-mitchell-watts-characters.md)**  
   **Blocked by:** 08, 09, 10.  
   **What it delivers:** Ingest and audit Phil, Grant, Peggy, Sharon, and Ben, then demonstrate representative sourced relationship and event answers.

16. **[Cover the Beale and Fowler core characters](16-cover-beale-fowler-characters.md)**  
   **Blocked by:** 08, 09, 10.  
   **What it delivers:** Ingest and audit Ian, Kathy, Cindy, Lucy, Bobby, and Martin, including evidence for family ties and crime-versus-justice distinctions.

17. **[Cover the Slater and Moon core characters](17-cover-slater-moon-characters.md)**  
   **Blocked by:** 08, 09, 10.  
   **What it delivers:** Ingest and audit Kat, Stacey, and Alfie, then demonstrate relationship histories and honest handling of uncertain event dates.

18. **[Cover the remaining connected core characters](18-cover-other-connected-characters.md)**  
   **Blocked by:** 08, 09, 10.  
   **What it delivers:** Ingest and audit Pat, Janine, Dot, Denise, Max, and Linda, preserving supporting connections and visible coverage gaps.

19. **[Demonstrate the complete evaluated Ask Phil workflow](19-validate-complete-ask-phil-demo.md)**  
   **Blocked by:** 05, 12, 14, 15, 16, 17, 18.  
   **What it delivers:** Run the full 20-character experience, verify all three routes and refresh/follow-up behavior, and publish reproducible quality, latency, and cost results.

## Dependency review

- The initial frontier contains ticket 01. Thereafter, begin any ticket whose declared blockers are complete; the numbering is a dependency order, not a requirement to work linearly.
- Source refresh and the first graph capability can proceed after identity/scope handling. Their combined behavior is checked by the disputed-claim ticket.
- Relationship histories and shared events extend the biological-claim slice independently, then enable bounded connection queries.
- Conversation support and judge calibration proceed independently of graph implementation. The persona slice uses the calibrated answer checks.
- The four named coverage cohorts share the same ingestion/review prerequisites and do not block one another or automatic-routing development.
- The final ticket depends on the completed conversation, persona, routing, and coverage branches. It verifies the integrated result and comparisons; required tests/evaluations already accompany every preceding slice.

All 98 numbered spec stories are mapped to at least one draft; each draft lists its story references. This is a planning coverage check, not evidence that the behavior is implemented or passes evaluation.

## Publication after approval

Use the configured GitHub tracker for `tomh1988-8/rag_demo`. Publish one issue per approved ticket in dependency order, applying `ready-for-agent` and translating the draft blocker numbers into real issue identifiers and the platform's available native blocking relationships.

Use each draft's title and body beginning at 'What to build'; omit the local draft status and planning story-reference metadata. Add a Parent section only if an actual source issue exists at publication time. Do not close or modify a parent issue.

Historical publication note: this proposal predates the installed GitHub plugin. Authenticated repository/issue reads now work through that plugin; see version 2 for the current publication workflow and remaining capability checks. No issues from this proposal were created.

## Review requested

Does the granularity feel right, or is it too coarse/fine? Does each dependency genuinely gate its ticket? Should any ticket be merged or split?

The invoked [to-tickets skill](../../../.agents/skills/to-tickets/SKILL.md) requires: "Iterate until the user approves the breakdown." Approval concerns this proposed breakdown, not a reopening of the agreed design or test boundaries.
