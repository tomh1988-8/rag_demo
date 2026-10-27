# Issue #13: crimes and criminal justice roles

The explicit graph route returns reviewed crime/justice assertions and all
participants in a shared incident. Each assertion retains its own legal stage,
participant roles, account attribution, story timing and source evidence. An
accusation, confession or legal outcome never supplies a commission assertion.
Answers use deterministic factual wording and make no inference calls.

## Source labels and actual extraction

[The pre-pilot review](reference-review.md) and
[hash freeze](pre-pilot.json) precede the one model call. Six short excerpts from
the unchanged captured `core-profiles-v2` sources support seventeen labelled
assertions about Lucy's murder, Stella's death and Carl's crash. The
[original reference](../../../data/references/crime-justice-v1.json) preserves paragraph
origins, document offsets, source revisions, capture hashes and the seven reviewed
identities. These are exposed development labels, without human adjudication or
independent canon corroboration.

The [outbound manifest](outbound-manifest.json) describes the public excerpts,
identity catalogue, incident scope and schema sent to the existing capped provider.
Expected claims and reviews were withheld. The
[one Sol extraction](extraction-pilot.json), captured at `a361332`, has valid schema
and four candidates: three exact normalized values, precision 3/4, recall 3/17,
F1 2/7. Three locators resolve; one candidate meets the deliberately conservative
full-reference-span grounding proxy. Identity, role, assigned direction, negation,
timing and account diagnostics are reported separately, alongside each event type.
A schema-valid result is not a quality pass.

[Content-bound source reviews](raw-reviews.json) admit Ben's arrest and the
narrative revelation identifying Bobby as Lucy's killer. The shorter Bobby quote
resolves and semantically supports that assertion even though it fails the stricter
full-reference-span proxy. Phil's false-confession candidate has a malformed span
and is held. The victim-only crash commission is held because its required
perpetrator is outside the selected catalogue; no substitute perpetrator is inferred.
[Raw admission](raw-admission.json) retains every failure and unchanged candidate.
The raw slice misses fourteen of seventeen reference assertions.

[The v2 serving batch](reviewed-claims-v2.json) retains all four raw candidates
and adds seventeen reviewed assertions with prefixed claim IDs.
[Independent source review](reference-review-v2.md) corrected five omitted relative
qualifiers in a separately versioned reference after the pilot; the two arrest/charge
quotes now include the supported timing clause. V1 and all original evidence remain
unchanged. [The unchanged-pilot rescore](reference-correction-v2.json) preserves
the original quality failures. [V2 reviews](reviewed-reviews-v2.json) bind each
complete claim's fingerprint. [Admission](reviewed-admission-v2.json) separates the nineteen admitted source records
(including two duplicate supports) from the two holds. Duplicate source support
remains in the typed audit while identical source-anchored assertions share one
prose entry. The reviewed capability
must not be reported as successful automatic extraction.

The sole offline call cost **$0.030536**. The preserved shared non-resetting $5
ledger is **$0.417335**, with zero unsettled reservations. Serving inference cost
is zero; database and hosting costs are excluded.

## Public contract and use

`EventQuery` has `kind: crime_history`, a reviewed `character_id`, optional distinct
`participant_id`, optional `event_id`, and `max_events` from 1–20 (typed default 10).
The cap counts distinct incidents and retains all admitted assertions within each
selected incident, rather than truncating participant roles. A shared-incident
query returns other participants in that incident with their own roles; it never
transfers guilt between them. Listing order is not chronology. The immutable
batch holds at most 100 source assertions.

`POST /v1/snapshots/{snapshot_id}/events` exposes the typed read-only tool.
`GET /v1/snapshots/{snapshot_id}/event-claims` returns raw claims, reviews and
admission independently of projection inclusion. `found`, `empty`, `truncated`,
`unavailable` and `unknown_character` remain distinct. Missing legal history never
establishes absence of crime. Every supported answer is partial because the
selected captured incidents cannot establish exhaustive history.

The tool has its own `event_graph` execution capability. Shared answer execution
retains the existing tool/concurrency/deadline/cancellation, database read-only,
context, saved-response and MLflow constraints. A stop discards selected claims
and citations. A broad Max history exceeds the existing 1,200-byte context budget;
select one incident to obtain a supported answer. Automatic routing, natural-language
graph argument inference and wider corrections/refresh remain later tickets.

```sh
export DATABASE_URL=postgresql://YOUR_USER@HOST:PORT/YOUR_DATABASE
.venv/bin/ask-phil load data/seed/crime-pilot-v1.json
.venv/bin/ask-phil install-events docs/implementation/issue-13/reviewed-claims-v2.json docs/implementation/issue-13/reviewed-reviews-v2.json
```

Start the API against that database, then:

```sh
.venv/bin/ask-phil ask "Who killed Lucy and who was convicted?" --snapshot crime-pilot-v1 --route graph --crime-history --character max-branning --event lucy-murder
.venv/bin/ask-phil ask "Did Phil kill Stella because he confessed?" --snapshot crime-pilot-v1 --route graph --crime-history --character phil-mitchell --event stella-death
.venv/bin/ask-phil event-claims --snapshot crime-pilot-v1
```

Typed arguments select the history; free-text questions remain inspectable.
The neutral appendix and typed graph preserve exact source names and quotations;
Phil's own assertions use first person and no wording minimises serious harm.

## Validation

Completion validation, independent review, actual public runtime evidence and
publication receipts are recorded alongside this document as they finish. Wider
RAG-04, EXT-04 and AD-08.4 release obligations retain their existing status.
