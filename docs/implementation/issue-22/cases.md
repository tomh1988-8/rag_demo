# Reviewed feedback cases

Issue [#22](https://github.com/tomh1988-8/rag_demo/issues/22), starting at
`ce0e27cc62a9933af38ec6efceafe42107570640` on `main`. These exposed development
cases were specified before implementation. The user confirmed the conversation
API/CLI and evaluation seams again in this session. They exercise feedback
collection, not independent factual correctness or the automatic judges in #23.

| Case | Expected observable result |
| --- | --- |
| Helpful / not helpful / skip | Optional feedback on a delivered response has a durable receipt. Skip is neither positive nor negative. Chat and reset require no rating. |
| Ownership | A session's expiring feedback capability authorizes only its own delivered responses, including earlier reset generations. A different session, answer read token or arbitrary trace target cannot authorize session feedback. Standalone responses use their own response capability. |
| Original interaction | Inspection retains the exact final answer, assembled context, citations, turn/generation, source and graph fingerprints, actual route, model, prompt and application versions. A reusable answer value cannot carry another delivery's feedback. |
| Duplicate / revision | The same submission ID and redacted payload returns the same revision. Reusing that ID for changed input conflicts. A new submission ID creates one later revision of the same feedback identity; only the latest accepted revision counts as current. |
| Untrusted text | Categories are an enum. Comment and proposed correction share a 1,000-byte budget, each at most 500 characters. Recognizable credentials and submitted bearer capabilities are redacted before persistence. Comments stay out of prompts, retrieval, conversational references and exported human assessments. |
| Delivery outage / delayed trace | Acceptance needs PostgreSQL, not MLflow. A missing trace or failed assessment export leaves inspectable pending state. Bounded retry after restart delivers to the original trace. A lost export acknowledgement cannot create duplicate assessments. |
| Revised assessment | Each revision is independently inspectable; a newer human assessment supersedes its prior revision. Human helpfulness and reported errors are never adjudicated correctness or gold expectations. |
| Retention / rate limit | Policy and use are shown before capture. At most ten new submissions per minute per anonymous context; exact retries do not consume more slots. Expired payloads become inaccessible and are purged; assessment deletion is retried with minimal cleanup identifiers if MLflow is unavailable. |
| Summary arithmetic | A served-time half-open cohort and explicit feedback-as-of cutoff select the original delivered interactions and latest eligible revisions. Four interactions (helpful, not helpful, skip, unrated) give eligible=4, submitted=3, rated=2, positive=1, negative=1, skipped=1, unrated=2, coverage=1/2, positive share=1/2. No ratings gives null positive share; an empty cohort gives null coverage. |
| Late / revised ratings | A later helpful revision changes positive/negative counts once, without changing the served cohort. A cutoff before that revision retains the earlier rating. Feedback beyond the cutoff does not leak into reports. All current items remain accessible in a paginated review-priority list. |
| Normal local use | CLI conversation or ask, optional feedback, durable readback, local MLflow HUMAN assessment, and a changed maintainer summary run against real PostgreSQL and local MLflow. No paid inference is needed to establish this deterministic transport/storage contract. |

Acceptance is measured through HTTP/CLI, public evaluation results and actual local
MLflow assessments. External model/service/time boundaries may be controlled;
internal application collaborators and PostgreSQL remain real. Executed results
are now recorded in [validation](validation.json), with the original failures
and subsequent review regressions retained separately. Existing private inputs,
data, workspace changes and the shared non-resetting provider ledger are protected.
