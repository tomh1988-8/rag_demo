## Problem Statement

People returning to EastEnders or exploring its history need accurate, current explanations of family trees, relationships, plot connections, marriages, divorces, deaths, affairs, crimes, criminal justice involvement, and scandals. Relevant information is spread across long character histories, contains changing accounts and uncertain dates, and can confuse biological relationships with social relationships or actual guilt with accusation and conviction. A fluent chatbot answer alone does not let a reader check these distinctions.

The project also needs to demonstrate credible AI engineering: how evidence is captured and extracted, when text retrieval or graph queries are useful, when bounded investigation adds value, and whether routing improves quality and efficiency. That demonstration requires observable execution, a comprehensive software test suite, component and end-to-end evaluations, and reviewed project-specific reference data.

## Solution

Build Ask Phil, a local command-line conversation with Phil Mitchell's speech style, backed by evidence from the main EastEnders television series. Phil's voice changes phrasing, while answers remain accurate, qualified where necessary, and supported by the system's entire available corpus. Self-serving commentary must preserve the facts and must not minimise serious offences or their harm.

Start with 20 curated core characters and evidenced supporting characters, with an expansion process intended eventually to cover most notable characters. Automatically choose conventional text RAG, GraphRAG, or bounded agentic investigation according to available capabilities and evidence. Each answer includes appropriate citations or graph evidence and a neutral appendix reporting what actually ran. Queries use a versioned captured source snapshot; source refresh is a separate workflow. Extend the conventional route with RAG-Fusion and surrounding-context expansion, then add versioned exact-match answer caching for eligible repeated questions.

Collect optional response-level user feedback and use it in automatic online evaluations of real local-demo interactions, with reviewed failures feeding the regression suite. Develop the application through test- and evaluation-driven slices. Unit and integration tests protect public behavior, component evaluations identify failures in extraction and retrieval, and end-to-end evaluations measure the final answer and evidence. Use reviewed custom datasets, calibrated LLM judges where appropriate, MLflow comparisons, and an always-text-RAG baseline.

## User Stories

1. As a returning viewer, I want to ask natural-language questions about EastEnders, so that I can understand its characters and history without reading every character biography.
2. As a viewer, I want Phil-like phrasing, so that the conversation feels connected to the programme.
3. As a viewer, I want the persona to preserve supported facts even when Phil would not know or admit them, so that the character voice does not undermine accuracy.
4. As a viewer, I want serious offences and their harm treated respectfully, so that entertaining characterisation does not trivialise them.
5. As a viewer, I want the chatbot to use the latest captured knowledge without spoiler restrictions, so that I can ask directly about revelations and outcomes.
6. As a user, I want a command-line conversation, so that I can use the first demonstration without a graphical interface.
7. As a user, I want follow-up questions to inherit conversational context, so that I do not have to repeat every character name.
8. As a user, I want factual follow-up answers grounded again in source evidence, so that earlier generated text does not become an unsupported source.
9. As a user, I want to reset the conversation, so that I can begin a new line of inquiry without earlier references affecting it.
10. As a user, I want ambiguous character references clarified, so that the system does not silently answer about the wrong person.
11. As a viewer, I want broad sourced coverage of the agreed 20 core characters, so that the initial demonstration contains recognisable and connected histories.
12. As a viewer, I want supporting characters included when they explain a relationship or event, so that the core roster does not sever relevant connections.
13. As a viewer, I want relevant pre-1990 history retained for eligible characters, so that later relationships remain understandable.
14. As a viewer, I want the initial knowledge base to distinguish main-series material from spin-offs and podcasts, so that its canon boundary is clear.
15. As a viewer, I want to see the limits of captured coverage, so that I do not mistake an incomplete corpus for the entire programme.
16. As a maintainer, I want to expand the core roster through the same ingestion and evaluation process, so that the system can grow towards most notable characters.
17. As a viewer, I want biological ancestry and descendants, so that I can understand family trees accurately.
18. As a viewer, I want adoptive and step-parent relationships represented separately, so that socially important ties remain available without changing biological ancestry.
19. As a viewer, I want a character kept distinct from their performer and aliases resolved consistently, so that recasts and name changes do not create incorrect identities.
20. As a viewer, I want current and former family or romantic relationships distinguished, so that historical ties are not mistaken for current ones.
21. As a viewer, I want marriage, separation, divorce, reconciliation, and remarriage distinguished, so that repeated relationships are explained correctly.
22. As a viewer, I want affairs and other supported personal relationships included, so that connections beyond marriage can be explored.
23. As a viewer, I want pregnancy and death events captured where supported, so that important changes in family histories can be explained.
24. As a viewer, I want actual commission of a crime separated from accusation and conviction, so that an innocent or falsely accused character is not labelled a perpetrator.
25. As a viewer, I want criminal justice involvement to include roles and distinct stages, so that court appearances and imprisonment are not conflated.
26. As a viewer, I want supported scandals and unusual events retained even when they do not fit an existing category, so that classification does not discard useful knowledge.
27. As a viewer, I want event types and themes distinguished, so that a topical theme does not become an invented event or character connection.
28. As a viewer, I want an evidenced explanation of how two characters are connected, so that I can inspect the relationships or shared events behind the answer.
29. As a viewer, I want shared events and participant roles, so that I can understand who did what within a plot.
30. As a viewer, I want exact, approximate, relative, and unknown timing preserved, so that the answer does not invent dates.
31. As a viewer, I want supported later corrections reflected in current answers, so that outdated story accounts do not silently remain authoritative.
32. As a viewer, I want unresolved source disagreements explained, so that uncertainty is visible instead of concealed by a confident answer.
33. As a viewer, I want false premises challenged with evidence, so that a character's lie or mistaken belief is not repeated as established fact.
34. As a viewer, I want absence from the corpus distinguished from proof that something never happened, so that incomplete coverage does not produce false negatives.
35. As a viewer, I want supported portions of an answer even when other parts are unresolved, so that partial evidence is still useful.
36. As a viewer, I want a clear abstention when the corpus cannot support an answer, so that fluent speculation does not replace evidence.
37. As a user, I want investigations to stop at configured limits and explain what remains unknown, so that answering stays bounded and transparent.
38. As a viewer, I want supporting passages and identifiable sources attached to factual answers, so that I can inspect the evidence myself.
39. As a viewer, I want a graph answer to expose the supporting relationship chain and evidence for its asserted connections, so that derived relationships are checkable.
40. As a viewer, I want an investigative answer to summarise the actual tools and findings used, so that I can understand how its evidence was gathered.
41. As a viewer, I want source-supported and independently cross-checked information distinguished, so that provenance is not overstated.
42. As a viewer, I want source-check dates distinguished from demonstrated storyline coverage, so that a recent fetch is not mistaken for complete current knowledge.
43. As a demonstrator, I want a neutral engineering appendix separate from Phil's voice, so that factual provenance and measurements are easy to assess.
44. As a demonstrator, I want the executed route, fallbacks, and escalations reported, so that the system explains actual behavior rather than an invented account.
45. As a demonstrator, I want elapsed time and available token and estimated model-cost measurements, so that efficiency can be discussed with evidence.
46. As a demonstrator, I want missing measurements identified honestly, so that unavailable usage is not reported as zero cost or fabricated confidence.
47. As a demonstrator, I want detailed execution traces available for inspection, so that failures and expensive steps can be investigated.
48. As a user, I want automatic routing to use an appropriate available capability, so that I need not choose a retrieval technique for ordinary questions.
49. As a demonstrator, I want an explicit route override, so that I can compare retrieval strategies while keeping the override visible.
50. As an AI engineer, I want routing evaluated on supported answer quality and total expense, so that matching a route label is not mistaken for solving the question well.
51. As an AI engineer, I want multiple successful routes recognised for one question, so that evaluation does not reward unnecessary complexity.
52. As an AI engineer, I want graph routing restricted to supported query capabilities, so that unsupported questions do not produce misleading structured answers.
53. As an AI engineer, I want bounded escalation when evidence is inadequate, so that investigation is used where it may improve the answer.
54. As an AI engineer, I want every route evaluated against an always-text-RAG baseline on the same corpus and answer model, so that improvements can be attributed and measured.
55. As a user, I want all answer routes to use a consistent captured snapshot, so that citations and related answers can be reproduced.
56. As a maintainer, I want narrative sources, identity links, and episode metadata assigned their appropriate roles, so that metadata agreement is not treated as independent plot corroboration.
57. As a maintainer, I want HTML/JSON ingestion measured separately from semantic claim extraction, so that lost source content can be distinguished from misunderstood content.
58. As a maintainer, I want source revisions, evidence spans, and extracted claims linked, so that a relationship can be traced back to the material supporting it.
59. As a maintainer, I want extracted claims retained independently of graph projections, so that interpretations and graph structures can change without losing provenance.
60. As a maintainer, I want automated admission checks and explicit review outcomes, so that unchecked extraction is not automatically presented as established knowledge.
61. As a reviewer, I want ambiguous or conflicting claims held for review, so that important uncertainties receive attention.
62. As a maintainer, I want a thorough initial manual audit followed by targeted review and sampling, so that review effort can grow sensibly with the corpus.
63. As a maintainer, I want earlier evidence preserved when claims are corrected, so that changed answers can be explained.
64. As a maintainer, I want ingestion reruns and refresh failures to be observable and reproducible, so that the usable knowledge base is not silently corrupted.
65. As a maintainer, I want a manual refresh initially and a weekly scheduled refresh when deployed, so that updates can follow the project's delivery stage.
66. As a developer, I want the CLI to use the shared FastAPI backend, so that a later client can reuse application behavior.
67. As a developer, I want PostgreSQL to hold the initial source, claim, relationship, and retrieval data, so that the first architecture has a manageable operational footprint.
68. As a developer, I want typed graph-query tools with explicit semantics, so that traversal results preserve domain meaning and evidence.
69. As a developer, I want a reproducible local Docker Compose environment, so that the demonstration and its integrations can be run consistently.
70. As a project owner, I want conservative configurable API and investigation limits, so that spending and execution stay controlled while exact values are calibrated during setup.
71. As a developer, I want small behavior slices guided by failing tests and reviewed evaluation cases, so that development responds to observable requirements and failures.
72. As a developer, I want unit tests at confirmed public boundaries, so that domain rules remain protected without coupling tests to private implementation details.
73. As a developer, I want integration tests using real PostgreSQL/pgvector and application interfaces, so that actual storage and orchestration behavior is exercised.
74. As a developer, I want controlled external-service substitutes for routine tests and separate budgeted live-provider checks, so that reproducibility and real compatibility are assessed distinctly.
75. As an AI engineer, I want a small reviewed reference set before the first extraction pilot, so that quality can guide the initial implementation.
76. As an AI engineer, I want parsing coverage, missing records, duplicates, and provenance evaluated, so that semantic evaluation starts from adequately captured documents.
77. As an AI engineer, I want extraction precision, recall, and F1 separated from schema validity, so that well-formed but incorrect claims are detected.
78. As an AI engineer, I want extraction checks for identity, roles, relation direction, negation, uncertainty, and timing, so that domain mistakes are visible at component level.
79. As an AI engineer, I want evidence grounding evaluated independently of extracted value accuracy, so that a correct-looking answer with an unsupported citation still fails.
80. As an AI engineer, I want retrieval and context-sufficiency evaluations, so that finding one relevant passage is not mistaken for collecting everything needed to answer.
81. As an AI engineer, I want graph result, path, edge-type, and provenance checks, so that graph answers are evaluated for both correctness and support.
82. As an AI engineer, I want router and investigator evaluations covering eligibility, limits, recovery, escalation, and task success, so that orchestration quality is measured directly.
83. As an AI engineer, I want end-to-end evaluations of final persona answers and multi-turn conversations, so that component gains are checked against user-visible outcomes.
84. As an evaluator, I want factual correctness, groundedness, completeness, relevance, citation support, and answerability assessed separately, so that one score cannot hide a different failure.
85. As an evaluator, I want persona quality assessed separately from facts and treatment of serious harm, so that style cannot compensate for incorrect or minimising answers.
86. As an evaluator, I want custom datasets covering positive, negative, ambiguous, corrected, and incomplete-evidence cases, so that the suite reflects this project's actual risks.
87. As an evaluator, I want model-generated cases reviewed and labelled as synthetic where applicable, so that generated expectations do not become unexamined ground truth.
88. As an evaluator, I want repeated story events and near-duplicate material grouped before dataset splitting, so that overlapping character biographies do not inflate held-out results.
89. As an evaluator, I want dataset artifacts, source snapshots, labels, prompts, models, scorers, and configurations versioned, so that comparisons can be reproduced.
90. As an evaluator, I want calibrated project-specific LLM judges for suitable semantic checks, so that automated assessments have defined rubrics and known limitations.
91. As an evaluator, I want judge disagreements and sensitivity to order, verbosity, and repeated runs examined, so that judge scores are not treated as infallible.
92. As an AI engineer, I want meaningful failures converted into reviewed regression cases, so that improvements do not repeatedly reintroduce known mistakes.
93. As an AI engineer, I want controlled ablations and paired per-case comparisons, so that apparent improvements can be attributed to the changes being tested.
94. As a project owner, I want serving costs and offline evaluation expenditure reported separately, so that efficiency and development spending remain understandable.
95. As a portfolio reviewer, I want unit/integration results and MLflow component/end-to-end reports associated with the evaluated revision, so that the engineering claims can be inspected.
96. As a portfolio reviewer, I want all three routes demonstrated through real executions with visible limitations, so that the project establishes more than a scripted chatbot response.
97. As a project owner, I want numerical quality thresholds established after a baseline and before held-out acceptance comparisons, so that acceptance criteria are informed without moving after results are seen.
98. As a developer, I want a complete text-RAG slice before adding graph retrieval and investigation, so that each stage has a working, measurable foundation.

99. As a user, I want to optionally rate an individual response as helpful or not helpful, so that I can give feedback without interrupting the conversation.
100. As a user, I want optional feedback categories and a comment or proposed correction, so that I can explain problems with facts, coverage, evidence, clarity or Phil's voice.
101. As a user, I want feedback to be acknowledged reliably and retries or revisions handled predictably, so that my submission is not lost or counted repeatedly.
102. As an evaluator, I want feedback linked to the exact served response, conversation turn, evidence snapshot and execution trace, so that I assess what the user actually received.
103. As a maintainer, I want user opinions and suggested corrections distinguished from reviewed factual expectations, so that feedback cannot silently change canon or become unverified ground truth.
104. As a project owner, I want online evaluation to run automatically on normal local-demo interactions, so that live quality monitoring is part of this release rather than deferred to cloud hosting.
105. As an evaluator, I want accepted feedback to update online quality signals and review priorities, so that feedback is used operationally rather than merely stored.
106. As an evaluator, I want suitable deterministic and calibrated semantic checks on served traces, so that online assessment can work when independently reviewed reference answers are absent.
107. As an evaluator, I want both feedback-directed inspection and a recorded sample of interactions with and without feedback, so that self-selected ratings are not presented as representative population accuracy.
108. As an evaluator, I want delayed or revised feedback reconciled with the original interaction and assessment revisions, so that results remain correct without regenerating the answer.
109. As a maintainer, I want online evaluation to have bounded costs, retries and processing lag with visible incomplete states, so that failures do not block conversation or masquerade as successful scores.
110. As a reviewer, I want feedback coverage, satisfaction, automated quality and processing failures reported with explicit denominators and version/cohort information, so that trends are interpretable.
111. As a reviewer, I want negative feedback and user/judge disagreements inspected with recorded dispositions, so that reported issues lead to evidence-based improvements.
112. As an AI engineer, I want reviewed live failures promoted into versioned regression cases with leakage checks, so that improvements are tested without contaminating held-out acceptance data.
113. As a user, I want feedback handling to use minimal identifying information, clear usage/retention rules and controlled access, so that giving feedback does not create a personal-memory feature or expose another session.
114. As a portfolio reviewer, I want to demonstrate the complete answer-to-feedback-to-online-assessment-to-review path, so that the product proves feedback affects evaluation.
115. As an evaluator, I want feedback and assessment provenance and revisions retained separately, so that user ratings, code checks, judges and adjudicated expectations can be inspected without conflation.
116. As a project owner, I want online evaluation expenditure separated from serving and offline evaluation costs, so that the full feedback loop stays within configured limits.

117. As a viewer, I want a conventional text answer to consider evidence found through several faithful query variants, so that relevant passages missed by the original wording can contribute to the answer.
118. As a viewer, I want relevant surrounding sentences included when a retrieved passage omits essential context, so that qualifications, chronology and references remain understandable.
119. As a viewer, I want every fact drawn from expanded context to retain its own resolvable source span, so that the extra context remains checkable.
120. As a project owner, I want query expansion, retrieval fan-out and assembled context bounded and traced, so that broader retrieval remains predictable in cost and latency.
121. As a evaluator, I want fusion and context expansion compared separately with single-query retrieval, so that retrieval gains are checked against final answer quality.
122. As a user, I want eligible repeated standalone questions to reuse supported text answers, so that frequent questions can be answered with lower latency and fewer model calls.
123. As a viewer, I want cached answers restricted to compatible snapshots and configurations with expiry and invalidation, so that outdated answers are not silently reused as current knowledge.
124. As a user, I want conversation-dependent and incompatible requests excluded from shared answer reuse, so that another question or session does not determine my answer.
125. As a demonstrator, I want cache hits to retain citations while receiving a new response identifier and truthful execution record, so that reuse can be inspected without claiming another generation ran.
126. As a evaluator, I want feedback and online evaluation to include each served cache hit, so that frequently reused mistakes remain visible and reviewable.
127. As a evaluator, I want cold and warm cache results measured separately with explicit hit and error denominators, so that reuse benefits do not conceal incorrect answers or distort retrieval comparisons.
128. As a maintainer, I want a bounded cache with disable, expiry, retirement and failure fallback behavior, so that the application remains usable when cache reuse is unavailable.
129. As a project owner, I want any later semantic matching for paraphrases gated by reviewed false-match evaluation, so that similar wording cannot silently substitute a different character, date or relationship question.
130. As a evaluator, I want cache contents isolated across evaluation runs and dataset partitions, so that previous answers and held-out labels cannot contaminate comparisons.

## Implementation Decisions

### Scope and domain model

- The first product is a local CLI conversation called Ask Phil. Phil is the only initial persona and may answer from the full supported corpus. A character is a fictional person, distinct from a performer. Session history supports references and follow-ups; persistent personal memory is outside this scope.
- Initial core coverage comprises exactly these 20 characters: Phil Mitchell, Grant Mitchell, Peggy Mitchell, Sharon Watts, Ben Mitchell, Ian Beale, Kathy Beale, Cindy Beale, Lucy Beale, Bobby Beale, Martin Fowler, Kat Slater, Stacey Slater, Alfie Moon, Pat Butcher, Janine Butcher, Dot Cotton, Denise Fox, Max Branning, and Linda Carter.
- Eligibility means an appearance in the main television series during or after 1990, including earlier debuts. Retain relevant earlier history. The list is a curated prominent roster, not a definitive popularity ranking. Keep evidenced supporting characters beyond the 20 and use the same process to expand core coverage later.
- Separate character identity and aliases, character relationships, story events and participant roles, themes, source-backed claims, and their evidence. Family trees contain biological ancestry; adoptive, step-parent, and other personal relationships remain distinguishable outside that tree. Do not map guardianship or wards into adoption without supporting evidence.
- Initial event classification covers marriages/divorces, affairs, pregnancy, death, crime, and specific criminal-justice events. Keep themes such as domestic abuse and the manosphere separate from event types. A common theme or mere co-appearance is insufficient to establish a character connection. Retain evidenced unclassified facts for text retrieval and make the classification gap visible.
- A crime is an act established as committed within the story, independent of detection or legal outcome. Criminal justice involvement records roles and distinct events such as accusation, arrest, trial, conviction, acquittal, imprisonment, and release. Preserve false accusations, convictions, corrections, and changing accounts without collapsing them into guilt.
- Preserve exact, approximate, relative, and unknown story timing. A broadcast date, source publication date, or refresh timestamp is not automatically a story event date. Keep current and former relationships distinct, including repeated marriages and the difference between separation and divorce.

### Sources, ingestion, and claims

- Use Wikipedia character narratives initially, Wikidata primarily for canonical identity links, and TVmaze for episode metadata. Main-series material must be distinguished at passage level when a source also discusses spin-offs, podcasts, performers, or production context.
- Start with ordinary HTML/JSON ingestion and LlamaIndex structured extraction. Introduce specialised document parsing only if representative inputs demonstrate a need. Parsing/content-retention errors and semantic extraction errors must be observable separately.
- Preserve captured source revisions and content, stable character/alias identities, passages or structured evidence records, extracted claims and their arguments/roles/timing, claim-to-evidence links, and review/admission outcomes. These are semantic record requirements; concrete schema and endpoint names are implementation choices within the agreed boundaries.
- Source-backed claims and evidence are the underlying knowledge record. Queryable graph relationships are rebuildable projections of claims that pass the agreed checks. Uncertain claims remain available for qualified explanation without appearing as established graph connections.
- Apply automated checks for structure, source support, identity, relationship meaning, and contradictions. Hold ambiguous or conflicting claims for review. Thoroughly audit a small initial batch manually, then use targeted review and sampling as coverage expands. Passing automation does not imply independent cross-checking.
- Source-supported answers are allowed with clear attribution. Reserve cross-checked or verified descriptions for actual evidence checks. Repeated copies of an account, matching identifiers, or episode metadata alone do not independently corroborate a narrative claim.
- Current interpretations follow supported corrections while retaining earlier evidence. Preserve unresolved disagreement rather than silently selecting one version. A source statement must be interpreted in context, including lies, beliefs, accusations, and retractions.
- All query routes use a consistent versioned captured source snapshot and its derived graph. Ingestion/refresh obtains new material separately. Make successful publication, failed or partial imports, reproducible reruns, and evidence-link integrity observable; do not silently mix incompatible source and graph versions.
- Use Prefect for ingestion and refresh. Trigger refresh manually for the local demonstration and schedule it weekly when deployed. Report when sources were checked separately from any known storyline coverage date.

### Application and retrieval architecture

- Use Python, LlamaIndex, FastAPI, PostgreSQL with pgvector, Docker Compose, Prefect, and MLflow. The CLI calls FastAPI, which calls shared application logic. Keep client-specific presentation separate so a later Shiny client can reuse the backend.
- PostgreSQL initially holds source, claim, relationship, and retrieval data. LlamaIndex's PostgreSQL vector integration supports text/vector retrieval; graph traversal is explicit application logic exposed through typed SQL-backed tools. A dedicated graph store is deferred until measured requirements justify it.
- The application boundaries are source ingestion/refresh, claim extraction/admission, text retrieval and typed graph tools, routing/bounded investigation, conversation API/CLI, and evaluation scorers. Preserve these public boundaries without requiring a separate service for every boundary.
- Conventional RAG retrieves supporting passages and, in the completed text route, uses bounded query fusion and evidence-preserving context expansion. GraphRAG returns supported structured results or relationship paths with evidence. Agentic RAG performs bounded investigation using the available text and graph tools within the captured snapshot. It may combine these capabilities; no live-web browsing occurs during answering.
- Initial graph capabilities are biological ancestry/descendants, family and romantic relationship histories, bounded evidenced connections between characters, and shared events/participants with distinct crime and criminal-justice roles. Graph coverage is narrower than the underlying text wherever claims have not been classified or admitted.
- The router checks capability eligibility, selects an available route, checks obtained evidence, and escalates within limits when needed. Normal conversations route automatically; explicit overrides support demonstration and comparison and must remain visible in the execution record.
- Judge routing by the quality of supported answers and the cost/latency of attaining it. Multiple routes may be valid. Do not require an investigator merely because a question looks complicated if one passage already supports the answer. Include selection, checking, retries, and investigation overhead in comparisons.
- Configure API and investigation limits during setup. Enforce the chosen bounds and return supported findings with a clear limitation when execution stops. Exact provider/model choices and numerical caps remain intentionally undecided until setup and initial measurement.

### Conventional text retrieval: fusion and context expansion

- Add RAG-Fusion within the conventional text route: retain the original question, generate a bounded set of faithful query variants, retrieve ranked candidates for each, and combine their rankings using reciprocal rank fusion (RRF). Deduplicate by stable evidence identity; do not count repeated variants or identical hits as independent evidence. Record rank convention, fusion constant, per-list limits, merged limit and deterministic tie handling. A fusion score is a ranking signal, not factual confidence.
- Add a distinct post-retrieval context-expansion step: include bounded surrounding sentences or a suitable parent passage from the same captured source revision when needed to interpret a hit. This is the wider-context behavior requested by the user. Begin with sentence-window expansion; hierarchical auto-merging is an alternative only if input structure and evaluation justify it. Preserve main-series passage filtering and revision/span provenance for all added text. Merge overlapping windows without losing citation locators.
- Use compatible LlamaIndex fusion and sentence-window abstractions with PostgreSQL/pgvector at the existing boundaries. Start with multi-query vector retrieval; lexical retrieval is optional. No graph traversal or agent loop is required.
- Resolve conversational references before query expansion, preserve identities, dates, negation and requested relationships, and never treat generated variants as evidence. Inspect candidate drift; bound variant count, retrieval fan-out, expansion size, total tokens, latency and model spend within the request budget. Invalid or unavailable expansion falls back visibly to original-query retrieval under the same limits. Budget exhaustion cannot trigger extra unbounded calls.
- Generate from the original/resolved question and the final evidence context. Record original query, variants, ranked candidates, fused selection, added windows, deduplication/truncation and actual context separately. Cite the spans actually supporting each claim, including material added by expansion. Broader context comes from the captured snapshot; unsupported model knowledge and live-web enrichment remain outside scope.
- Retain the single-query text baseline from the first model slice. Evaluate single-query, fusion-only, expansion-only and combined text configurations on identical frozen questions/corpus/answer-model settings with comparable final-context budgets. Version the selected conventional-text policy for subsequent graph/router comparisons; measure rather than assume improvement. Reference: [LlamaIndex fusion](https://developers.llamaindex.ai/python/framework/integrations/retrievers/reciprocal_rerank_fusion/) and [sentence-window retrieval](https://developers.llamaindex.ai/python/examples/node_postprocessor/metadatareplacementdemo/).

### Repeated-question answer caching

- Implement an application answer cache for repeated, standalone conventional-text questions after the response, refresh and online-evaluation contracts work. Begin with exact matches after documented conservative normalization. Preserve names, dates, negation and requested relationships; bypass follow-ups or any request that depends on session history, graph/investigative execution, incompatible overrides or unresolved identity. This first cache does not promise paraphrase hits.
- Store reusable answer text, citations and the original supporting context/provenance in PostgreSQL initially. A separate Redis service is not required at this demo scale. Reuse requires the same effective request, canon/access scope, source snapshot and index revision, text/fusion/context configuration, answer model/settings, prompts/persona, output/validation policy and relevant application version. Check eligibility and evidence resolvability on every hit. Invalid or retired entries are misses.
- Snapshot publication/rollback, corrected or withdrawn evidence, and relevant configuration changes must make incompatible entries ineligible immediately; TTL alone does not establish freshness. Define bounded storage/eviction, expiry, explicit retirement, disable/bypass and a cache-error fallback to normal bounded answering. Store successful supported answers only; do not populate from failures, clarification or unsupported outcomes. A reported error may be flagged for review; user opinion cannot rewrite evidence or certify correctness.
- Every cache delivery receives a new response ID and serving trace linked to its cache entry and original generation/evidence lineage. Preserve the answer's citations and support status. Report a cache hit and this request's actual elapsed time, model calls and known usage; never replay the original latency/cost as current work or imply retrieval/generation ran again. Do not expose another session's conversation, feedback or private trace to the recipient.
- Collect feedback against the newly served response and include cached deliveries in online metrics, sampling, judging and review. Resolve the original evidence/context for assessment without generating a replacement answer. Count delivered interactions for feedback coverage, identify shared answer lineage when interpreting repeated errors, and distinguish cache-hit and fresh-generation cohorts.
- Keep caching disabled or isolated and empty for retrieval/model-quality comparisons. Report deliberate cold/warm workload experiments separately, including eligible requests, hits/misses, stale or invalid reuse, supported-answer quality, latency and total serving cost. Isolate cache namespaces by run and dataset partition; do not warm held-out comparisons from tuning answers or labels.
- Semantic caching matches paraphrases by embedding similarity and is a later opt-in extension, not required for the initial cache. Before enabling it, require hard compatibility filters plus calibrated thresholds and reviewed positive/negative pairs, especially different characters, dates, negation, biological versus step-parent ties, and guilt versus accusation. Provider prompt caching and ingestion/embedding caches are different optimisations and do not satisfy this answer-reuse requirement. See [semantic cache semantics and trade-offs](https://redis.io/docs/latest/develop/use-cases/semantic-cache/).

### Conversation and evidence contracts

- A chat response exposes the answer or clarification/partial/abstain outcome, source evidence, relevant uncertainty, the executed route and any fallback, the source snapshot/refresh information, and elapsed time. Detailed inspection exposes recorded execution and available token/model-cost measurements. Final field names and transport shapes must implement this behavior without introducing new product scope.
- Phil's voice is a presentation constraint: preserve factual claims and their qualifications. Self-serving commentary may not deny or obscure evidence and may not minimise serious offences or their harm. Present citations, paths, tool records, and measurements neutrally.
- Conventional responses cite supporting excerpts; graph responses expose the relevant path or structured result and evidence for asserted edges; investigative responses summarise actual tool calls/findings and resulting evidence. Assemble the appendix from execution records, not an invented model narrative.
- Reuse conversational context for references, while grounding every factual response again in the snapshot. Do not treat generated conversation history as evidence. Provide a reset action.
- Ask for clarification when identity remains ambiguous. Return supported portions when possible, identify unanswered parts, and abstain when evidence is absent. An empty retrieval or graph result establishes only that no supporting result was found within the available coverage.
- Report missing measurements honestly. Label estimated model cost appropriately; unavailable usage is not zero cost and retrieval similarity or aggregate evaluation scores are not per-answer confidence.

### User feedback and online evaluation

- Feedback is part of the initial CLI/FastAPI product. Offer optional helpful/not-helpful feedback on a selected response, with optional categories (facts, missing/outdated information, evidence, clarity, persona/tone, other) and bounded free text or proposed correction. Skipping feedback must not impede conversation. Acknowledge durable acceptance and handle retries, changed ratings and invalid response references explicitly.
- Give each served outcome a stable response identifier linked to the original final persona text, evidence/context, turn/session reference, source/graph snapshot, executed route and code/prompt/model versions. The backend resolves authorised feedback to the actual trace; do not let clients write arbitrary MLflow assessments or another session's feedback. No user accounts are required.
- Persist feedback revisions and delivery state in PostgreSQL and attach human-origin assessments to the corresponding MLflow trace. A repeated submission identity is idempotent; the current rating counts once per interaction/anonymous submission context, while revision history remains inspectable. Acknowledging saved feedback does not claim that a background judge has finished. Delayed trace export or MLflow outage leaves durable pending work, not lost feedback.
- Explain feedback use and configure retention/access/redaction before capture. Collect no identity beyond an opaque session/feedback context unless needed by an agreed later feature. Keep evaluation records separate from conversational memory: reset clears answer context, and feedback never becomes retrieval evidence. Treat free text as untrusted data, not instructions; minimise data sent to external judges.
- Online evaluation means automatically assessing actual served interactions during normal operation, asynchronously within a configured processing window. It must work in the local Docker Compose demo. Manual analysis of old logs or constructing an offline dataset alone does not satisfy it. Do not rerun the answering agent or replace original evidence when grading an existing response.
- Every accepted current feedback item contributes to descriptive feedback metrics and triage. Combine a bounded feedback-directed sample (prioritising factual/evidence/harm reports) with a recorded random sample of eligible interactions, including those without ratings. Record selection policy, eligibility and sample rates; unknown or declined feedback is not a positive vote. Keep feedback-selected and representative-sample findings separate.
- Reuse calibrated, versioned evaluators with declared input requirements. Online checks may assess evidence/citation integrity, grounding, relevance, uncertainty and persona treatment from recorded outputs/context. Reference-dependent correctness, recall or completeness measures are unavailable until suitable expectations have been independently reviewed. Keep user helpfulness, reported factual errors, automated findings and reviewed correctness separate; a vote is not a verified answer key.
- Use the existing Prefect orchestration and self-hosted-compatible MLflow assessment APIs for the durable automatic evaluation workflow. MLflow native automatic judges may be used where the selected version supports the needed behavior; do not assume they cover deterministic scorers, delayed feedback, retries or re-evaluation. Demonstrate the configured workflow rather than requiring a managed-only review service or a new evaluation platform.
- Reconcile feedback arriving after the original assessment, revisions and repeated deliveries without duplicate active counts or unintended repeat model charges. Version changed assessments and deduplicate work by interaction, evaluator/configuration and relevant feedback revision. Generic grounding judges assess the original evidence without being led by the user's vote; feedback-aware triage uses a separately labelled rubric.
- Configure finite evaluation call/time/spend limits, bounded retries and concurrency, a disable control, and an observable backlog/lag target. Judging does not block response delivery or feedback acceptance. Report pending, successful, failed, budget-skipped and ineligible work distinctly. Separate online evaluation expense from answering cost and offline evaluation expense; missing usage is not zero.
- Report counts and denominators for eligible served interactions, interactions with current feedback, positive/negative ratings, sampled/evaluated interactions, valid scores and failed/skipped/pending work. Define served-time cohorts and feedback-as-of cutoffs, and separate revisions from additional interactions. Break findings down by actual route, outcome, snapshot and application/evaluator versions where sample sizes permit. Self-selected feedback and observational trends do not establish unbiased accuracy or causal improvement.
- A maintainer inspects original traces, user reports and judge disagreements, records dispositions and verifies proposed corrections against the source policy. Review each accepted report with a category/comment; sample remaining ratings according to the recorded policy. Only reviewed/adjudicated cases become versioned regression/reference data, with story/duplicate grouping and held-out contamination checks. Feedback does not autonomously change source claims, prompts, routing or model weights.

### Delivery and operations

- Prepare a small reviewed seed dataset and use the confirmed test boundaries from the first development slices. Build a complete evidence-backed text-RAG path and baseline, then add checked graph capabilities, then bounded investigation and automatic routing.
- The first complete portfolio demonstration must include all three routes, the agreed core roster, grounded follow-ups, reproducible refresh, and the complete software-test, offline evaluation and feedback-driven online evaluation workflow. A text-only intermediate slice is a delivery step, not completion of this spec.
- Run locally first using Docker Compose. R Shiny and Azure/Posit Connect hosting are later options. The initial two-week working-slice aim does not establish a fixed commitment for completing every feature; available hours and monetary amounts remain open, with conservative limits chosen during setup.

## Testing Decisions

### Test boundaries and development discipline

- The user has explicitly confirmed all six public test boundaries: source ingestion/refresh; claim extraction/admission; text retrieval and typed graph tools; routing/bounded investigation; conversation API/CLI; and evaluation scorers. No new seam is introduced by this spec and no renewed confirmation is needed for these boundaries.
- Prefer the conversation API as the highest end-to-end seam for product behavior, with focused CLI transport checks. Use the other approved public boundaries where component isolation, domain-rule verification, or failure attribution adds value. Do not create additional seams merely to test internal helpers.
- Good tests assert external behavior using independently established expected results. They survive refactoring, exercise meaningful failure cases, and do not mock internal collaborators, test private methods, reimplement the same algorithm in assertions, or require one exact internal call sequence when several strategies are valid.
- Work in vertical slices: define the public behavior, add a failing deterministic test or reviewed evaluation case, make the smallest useful change, and run the affected unit/integration, component, and end-to-end regressions. Do not prewrite a large speculative suite against an imagined implementation.
- Repository prior art is the confirmed design, domain glossary, architecture decisions, test strategy, and candidate demonstration scenarios. There is no existing application, executable test suite, completed dataset, or measured model baseline to reuse; do not present those documents as passing tests or validated gold data.

### Unit and integration suite

- Unit-test exposed rules for identity and alias normalization, relation direction, biological ancestry, role distinctions, date precision, claim admission, citation integrity, and limit arithmetic. Test actual contracts and counterexamples rather than implementation shape.
- Integration-test real PostgreSQL/pgvector, source/claim persistence, snapshot publication and revisions, rerun idempotence, evidence links, graph results, orchestration outcomes, API/CLI contracts, grounded follow-ups/reset, and failed or interrupted operations.
- Substitute external source/model-service boundaries for routine reproducible runs while keeping internal application collaborators real. Prefer a real test database. Add separately budgeted live-provider checks; substituted-provider tests do not establish real model quality or compatibility.
- Test software scorers against independently reviewed known successes, failures, and missing-data cases. Validate observable tool limits and recovery without prescribing an unnecessary exact sequence of internal calls.

### Component evaluation suite

| Component | Required evaluation focus |
| --- | --- |
| Ingestion/parsing | Retained relevant sections/records; missed, duplicated, or excluded content; source revisions and reliable evidence locators. |
| Entity/relation/event extraction | Schema validity separately from normalized value/identity accuracy; precision, recall, and F1 where annotation supports them; direction, participant roles, negation, uncertainty, dates, duplicates, and invented records. |
| Extraction grounding | Whether the cited source revision and span resolve and support the extracted claim in context, independently of value matching. |
| Text retrieval | Recall@k and Hit@k initially; precision@k, MRR, or nDCG where useful, with explicit metric variants and reference requirements. |
| Context assembly | Relevant context, required-fact coverage, sufficiency of combined evidence, sentence-window provenance and losses caused by truncation. |
| Fusion | Query fidelity, candidate and fused-ranking coverage, duplicate handling, budget/fallback behavior and final-answer effects. |
| Answer cache | Eligible hit/miss denominators, exact-match validity, stale/incorrect reuse, evidence/feedback lineage, cold/warm quality, latency and expense. |
| Graph retrieval | Correct result sets and relationship meaning, allowed types/direction, valid supported paths, evidence coverage, cycles/bounds, and qualified empty results. |
| Router/investigator | Eligibility, tool/argument validity, supported task success, fallback/recovery, limit enforcement, missed/unnecessary escalation, and total quality/cost trade-offs. |
| Answer generation | Correctness against reviewed references, groundedness in actual context, completeness, relevance, clarification, partial answers, and abstention. |
| Citations | Resolvable references, evidence availability, claim-level support, and coverage of factual assertions. |
| Persona/appendix | Preservation of facts and uncertainty, separate style assessment, treatment of serious harm, and agreement with actual execution and measurements. |

- Separate measures that answer different questions. Hit@k or MRR can succeed with insufficient evidence for a multi-fact answer. Schema validity does not establish truth; faithfulness to context does not establish independent source correctness; citation existence does not establish support.
- Specify normalization/matching rules, duplicate handling, top-k denominators, relevance labels, acceptable alternative paths, and uncertainty tolerances. Evaluate by event/relation type and difficult-case category as well as aggregate scores. Recall requires sufficiently complete annotation of the evaluated source material.

### Fusion and cache tests

- At existing public boundaries, test RRF ordering, duplicate handling, query drift, window scope/revision/citations, context truncation and bounded fallback. Use independent rank expectations and reviewed cases needing surrounding qualifications.
- Compare baseline, fusion-only, expansion-only and combined text retrieval. Measure candidates, fused ranking, final-context sufficiency and final answers separately; include query-generation expense and keep caching disabled.
- Integrate real cache persistence and API/CLI hit/miss, normalization, expiry/invalidation/rollback, isolation, retirement, disable and failure recovery. Each hit preserves evidence but receives a new response/trace, feedback and online assessment.
- Measure stale/incorrect reuse and cold/warm latency/cost with explicit denominators. Isolate runs and dataset partitions; independently review any future semantic-matching thresholds and near-miss cases.

### Project-specific datasets and judges

- Create a small independently reviewed seed set before the first extraction/model-driven slice. Grow linked datasets for source fixtures, claim annotations, retrieval relevance, graph questions, routing/investigation tasks, and end-to-end conversations from new coverage and observed failures.
- Record stable case IDs, source snapshots and spans, questions/history, expected facts/roles, acceptable alternatives, forbidden unsupported assertions, answerability, sufficient evidence sets, route eligibility where appropriate, reviewer/adjudication notes, split membership, and synthetic provenance.
- Include biological versus step/adoptive ties, wards versus adoption, character versus performer, repeated marriages, separation versus divorce, false confession, actual guilt versus conviction, uncertain dates, corrections/conflicts, themes, incomplete coverage, false premises, and conversational references.
- Cross-check reference facts according to the source policy and record what was checked. Model-generated questions/labels may propose examples but require review before becoming gold. Keep synthetic cases marked and examine realistic source cases separately.
- Separate development, judge-calibration, held-out comparison, and regression uses. Group overlapping story events, near-duplicate passages, paraphrases, and synthetic derivatives before splitting, including stories repeated across different character pages. Keep held-out labels out of tuning; their supporting passages may still remain retrievable for ordinary RAG evaluation.
- Freeze dataset artifacts/hashes, splits, source revisions, extraction/normalization rules, prompts, models/settings, retrieval configuration, scorer/rubric versions, and code revision where available. Version reference corrections and rerun baseline and candidate fairly. Use self-hosted-compatible artifacts rather than assuming a hosted vendor's immutable-dataset feature is available.
- Use deterministic checks where expectations are explicit and LLM judges for semantic support, completeness, uncertainty, and persona qualities where rubrics add value. Give judges the relevant evidence and allowed alternatives; keep facts and style separate.
- Calibrate judges against human-reviewed labels, inspect disagreements and false passes, and validate changes against labels excluded from judge tuning. Record judge configuration and concise assessment reasons. Check answer-order and verbosity sensitivity and repeat a representative subset to estimate variation; low temperature or another model does not guarantee reliability.

### Feedback and online evaluation tests

- Keep the existing six public boundaries. Feedback submission is exercised through the conversation API/CLI; background evaluation and its public results use the existing evaluation/scorer and orchestration contracts. No separate service boundary or new design-seam approval is required.
- Before implementing feedback, review cases for helpful/not-helpful/skip, optional comments, invalid or other-session references, duplicate submission, changed rating, reset, delayed trace export and MLflow failure. Verify the original response/trace association, durable receipt, access rules, minimal logging and retention behavior with real PostgreSQL and local MLflow integrations.
- Before enabling automatic evaluation, test the complete normal-use path: serve an answer, submit feedback, process it automatically and inspect its online metrics/assessments and review state. Include delayed feedback after prior scoring, feedback on partial/abstain/clarification outcomes, all three routes and a follow-up/reset interaction.
- Check metric/scorer arithmetic against independent fixtures, including no feedback, zero denominators, duplicate/revised votes, unrated interactions and failed or budget-skipped evaluations. Check sampling/eligibility deterministically in routine tests and show feedback-directed and background samples separately. No score is silently manufactured for missing context or reference labels.
- Integration-test restart/recovery, bounded retries, cancellation/disable, slow or failing judges, unavailable MLflow, redaction and hostile feedback text. Assert actual persisted feedback/jobs/assessments and unchanged served answers, not one internal execution sequence. The app remains usable when evaluation is unavailable.
- Validate online judges against reviewed labels and inspect user/judge disagreements; promote a reviewed live failure into a grouped/versioned regression case without leaking it into an existing held-out split. Record monitoring cadence, reviewer responsibility and pending/unresolved dispositions.
- Run a separately budgeted live local-demo evaluation and report latency to assessment, sample/feedback coverage, measurement gaps and online expense. This complements the fixed-corpus offline baseline; online observational results do not replace held-out acceptance.

### End-to-end comparisons, reporting, and gates

- Evaluate representative questions and multi-turn conversations through the public application path. Assess the final persona answer, citations, actual evidence appendix, clarification/partial/abstain behavior, reset, and representative limit/failure cases.
- Compare always-text-RAG, graph-capable, investigative, and routed policies using the same frozen corpus/question set. Hold answer-model settings fixed when isolating retrieval changes. Try other eligible routes on a representative subset to identify multiple successful strategies and their observed costs.
- Use targeted ablations where practical and report component changes alongside final-answer effects. Include per-case failures, category breakdowns, sample sizes, paired changes, appropriate uncertainty estimates, and latency distributions. Repeated stochastic runs are not additional independent questions.
- Use MLflow for traces, artifacts, custom offline scorers, calibrated judges, and comparisons. Preserve actual retrieval and assembled-context information needed by scorers, including graph and multi-step evidence. Keep software-test results in the test runner/CI artifacts and associate them with the evaluated revision.
- Measure routing, checking, retries, and investigation as part of serving cost/latency. Report offline judge/evaluation expenditure separately. Label cost estimates and missing usage honestly.
- Run fast deterministic tests and relevant fixture-based regressions during development. Run budgeted real-model component/end-to-end evaluations when relevant models, prompts, schemas, retrieval/routing policies, or corpus content change and before accepting a demonstration build.
- Require deterministic contracts and reviewed demonstration cases to pass their applicable checks. Resolve critical factual, biological-relationship, guilt, citation, or answerability failures rather than hiding them in averages. Choose numerical thresholds, k values, dataset sizes, and repeat counts after an initial baseline and before judging candidates on held-out comparisons.

## Out of Scope

- Spoiler controls, audience reveal-date filtering, or modelling what Phil personally knows or would honestly admit.
- Complete EastEnders canon, claims of exhaustive character histories, or programme-wide rankings/superlatives unsupported by demonstrated corpus coverage.
- Spin-off and podcast material in the initial corpus; full transcripts, video, audio, image processing, or PDF/OCR as assumed initial inputs.
- Unreviewed expansion to fan wikis or other narrative sources, and unrestricted live-web browsing during answer generation.
- Persistent personal memory, accounts, multiple selectable personas, and a graphical or R Shiny client in the initial delivery. Retained feedback/evaluation records are allowed for the specified monitoring workflow and are not conversation memory.
- Production cloud deployment or a final Azure/Posit Connect hosting commitment as part of the local demonstration.
- Automatic fine-tuning, self-modifying prompts/routing or automatic canon edits based on user feedback; formal online A/B experimentation is not required for this release.
- A dedicated graph database without measured need, and modelling complete storyline arcs before a supported requirement calls for it.
- Treating a matching identifier, model-generated label, fluent answer, or LLM-judge score as independently verified truth.
- Pretending candidate demonstration questions are already gold-labelled, that benchmarks already exist, or that a text-only intermediate slice completes the three-route demonstration.

## Further Notes

- The complete design and public test boundaries were explicitly confirmed by the user before this specification was requested. This issue synthesises those decisions; it does not reopen the interview or introduce additional test seams.
- The original scoping pack is background. Accepted decisions supersede its spoiler requirements and refine the interface, corpus, storage, evidence model, and evaluation strategy. The active architecture decisions preserve current knowledge without spoilers, factual persona behavior, evidence for corrections/conflicts, claims underlying graph projections, snapshot-only answering, and initial PostgreSQL storage.
- The deterministic captured-evidence slice in issue #2 is complete, with native and Docker acceptance recorded separately. Model-driven answering, fusion, caching and broader quality evaluation remain unimplemented; this specification makes no model-quality claims.
- Setup/pilot choices remain deliberately open: exact providers/models, package versions, numerical API/investigation limits, broader dataset sizes, and quality/cost/latency thresholds. Build the reviewed seed data and testing/evaluation workflow from the outset, then set informed thresholds before held-out acceptance comparisons.
- Candidate demonstrations include a directly cited marriage date, Ian/Ben biological parent links, Kat/Alfie relationship history, the Lucy/Max/Bobby investigation, a false claim by Phil about Jay's father, and an exact-date request unsupported by the captured evidence. Validate premises, source revisions, alternative valid answers, and actual answerability before adopting them as gold cases.

- Amendment, 23 September 2026: the user explicitly required feedback collection and use in online evaluations. These are current local-demo acceptance obligations. The existing issue set is extended and relevant issues amended; the original stories 1–98 keep their identifiers.

### Completion criteria

1. The 20 core profiles are ingested with visible evidence and coverage limitations, including evidenced supporting characters where needed.
2. All three retrieval routes execute and report their actual evidence and trace, with automatic routing and visible overrides/fallbacks.
3. The unit and integration suite passes its confirmed public behavioral contracts and failure-handling checks.
4. Component and end-to-end results are recorded against versioned custom data, and reviewed demonstration cases pass factual-support, citation, domain-correctness, and expected-answerability checks.
5. MLflow reports quality, latency, and cost against the fixed-corpus text-RAG baseline, including judge configuration, calibration evidence, and known limitations where judges are used.
6. Ingestion can be rerun reproducibly, and the CLI supports grounded follow-up questions, clarification, partial answers, abstention, and reset.
7. Users can submit optional response-level feedback through the CLI/API, with reliable association, receipts, revisions and appropriate access/data handling.
8. Normal local use automatically feeds feedback and sampled served traces into bounded online evaluation and inspection; delayed feedback, failed/skipped work and sampling/denominator limitations are visible.
9. A reported issue can be reviewed against its original evidence, given an explicit disposition and promoted into a reviewed regression case. Demonstrate this full loop and separate online evaluation expenditure from serving and offline evaluation costs.

10. The conventional text route demonstrates bounded RAG-Fusion and source-context expansion, with separate ablations and resolvable supporting spans.
11. Eligible repeated text questions demonstrate versioned exact-match answer reuse, invalidation, honest cache-hit traces and feedback/online evaluation; cold/warm performance is reported separately from uncached quality.
