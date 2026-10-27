# Issue #14: life events, themes and unclassified facts

The event tool now exposes pregnancy and death, alongside the existing crime and
justice history. Reviewed thematic subjects and unclassified facts remain text
annotations; they never create event participants, family links or connections.
Text retrieval returns the unchanged source passages and their admitted
annotations. Their serialized size counts against the existing context budget,
and cited annotations add an explicit classification qualification to the answer.

## Public contract

`EventQuery.kind` accepts `life_events` and the existing `crime_history`.
`theme` and `unclassified` return `ineligible`, with guidance to use text evidence.
`character_id`, optional `participant_id`, optional `event_id`, and `max_events`
retain the bounded incident-query contract. Participants must belong to the
requested event family; a legal assertion cannot make someone a death participant.
Listing order is not chronology. Empty results do not establish that an event
never occurred. Graph answers remain partial because captured coverage is limited.

Pregnancy admits `pregnant_person`; death admits `deceased`. Parentage, witnesses,
and dates require their own support. The current deliberately narrow roles do
not infer those facts from co-appearance, a funeral, a hallucination, or a belief.
The raw and reviewed claims remain inspectable at
`GET /v1/snapshots/{snapshot_id}/event-claims`. Events are queried through
`POST /v1/snapshots/{snapshot_id}/events` or the explicit conversation graph route.

```sh
ask-phil load data/seed/life-events-pilot-v1.json
ask-phil install-events docs/implementation/issue-14/reviewed-claims.json docs/implementation/issue-14/reviewed-reviews.json
ask-phil ask "When did Peggy die?" --snapshot life-events-pilot-v1 --route graph --event-kind life_events --character peggy-mitchell --event peggy-death
ask-phil ask "Does a shared theme establish a connection?" --snapshot life-events-pilot-v1 --route graph --event-kind theme --character peggy-mitchell --participant phil-mitchell
```

The existing `--crime-history` flag remains supported. Automatic routing and
natural-language inference of graph arguments remain later work.

## Frozen source review and extraction

The [pre-pilot source review](reference-review.md), [hash freeze](pre-pilot.json),
and [source reference](../../../data/references/life-events-v1.json) precede the
model call. Seven excerpts from unchanged captured profiles supply five life
events, one domestic-abuse theme and one public-tape-revelation classification
gap. The pregnancy account leaves paternity uncertain; the funeral date does not
date Peggy's death; Pat is a hallucination; Ian's later support is not presence
at Lucy's death. No selected source supports a manosphere theme.

[One actual extraction](extraction-pilot.json) at `3ff8287` returned valid schema.
Exact event values match 4/5; pregnancy matches 2/3 and death 2/2. The sole timing
value difference is `On Christmas Day 2005` versus `Christmas Day 2005`: a strict
wording mismatch, not an invented date. Three event locators resolve. Zero covers
the deliberately conservative full supporting-span reference, while manual source
review supports three shorter quotes. Two malformed locators remain held.

The domestic-abuse annotation matches its value and full supporting span. The
unclassified annotation has a valid supporting quote and supported character
subset but omits Kathy as a party subject from the frozen reference. Context
classification value precision/recall is 1/2, with 2/2 resolvable spans and 1/2
strict grounding. [Content-bound reviews](raw-reviews.json) and
[raw admission](raw-admission.json) preserve these distinctions. No raw outputs,
labels, or locators were rewritten to improve a score.

[The curated batch](reviewed-claims.json) retains all seven raw records and adds
the seven pre-reviewed reference records with distinct IDs. Its
[reviews](reviewed-reviews.json) admit eight event source assertions and four
text annotations; the same two raw event holds remain. Duplicate event support
stays in the audit and shares prose. This is curated capability, not successful
automatic extraction, a held-out comparison, human adjudication, or independent
canon corroboration.

The extraction cost **$0.0352235** and three serving calls cost **$0.0124210**:
**$0.0476445** in reported inference cost for this issue. The non-resetting shared
$5 ledger is **$0.464981**, with zero unsettled reservations; per-call upward
rounding accounts for the slightly larger ledger delta. Graph answers require no
inference. Database and hosting costs are excluded.

## Validation and retained failures

[The final graph capture](runtime-final.json) at `ef77ce8` records thirty actual
API, CLI and session outcomes for the raw and reviewed projections, with exact
MLflow output readback, citation resolution, saved-response restart and reset
checks. The raw phase exposes missing pregnancy/death coverage after its holds;
the curated phase supplies all five reviewed events. Theme/unclassified queries,
unmentioned parentage, hallucinations, co-appearance and unknown identities all
retain limited outcomes. The [initial capture](runtime-initial.json) and
[unchanged-output rescore](extraction-score-final.json) remain inspectable.

[Three actual text responses](text-runtime.json) use pinned local embeddings,
PostgreSQL retrieval and capped OpenRouter generation through the public HTTP API.
Their saved responses, citations and actual MLflow root outputs match. The
[source-based quality review](text-quality.json) passes the tape revelation and
domestic-abuse cases: the unclassified fact stays available with a visible gap,
and the theme does not establish a connection. The unsupported-manosphere case
fails its frozen answerability expectation (`answered` instead of
`insufficient_evidence`) and omits the explicit caveat about coverage elsewhere.
Its incidental examples and citations are supported; it invents no theme or
connection. This remains one failed text case, separately from trace integrity.
[Regressions](regressions.json) retain it alongside all extraction failures.

Focused red/green tests cover admission, PostgreSQL projections and retrieval,
API/CLI answers, context sizing, extraction and metric distinctions. A controlled
extraction initially exceeded the 16,000-byte input budget because the schema
appeared twice; the prompt copy was removed while provider schema enforcement
and local validation remain. A separate regression protects existing audit JSON
from inheriting the outbound-only strict schema requirements. Existing batches
retain their serialization and fingerprints.

The strict output contract follows the provider requirement that every property
be required in the outbound schema, while legacy retained batches can omit the
new empty list. [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs#all-fields-must-be-required).

[Independent Standards and Spec reviews](review.md) found zero implementation
issues. A further read-only evidence audit matched all thirty graph responses and
all three text responses to actual MLflow records, and verified the reviewed
claims, roles, timing, citations and retained failures. The final full-suite
run passes **414 tests**, with zero failures, errors or skips. Strict mypy passes
across 99 files; Ruff lint and formatting pass. [Validation](validation.json)
binds the [software report](software-tests.xml), final captures and source
fingerprint to `ef77ce8`. Sixteen warnings concern the existing Starlette/httpx
deprecation and pytest's `record_property`/xunit2 compatibility. All 34 original
data files, 51 pre-existing workspace files and seven frozen pilot files remain
unchanged. RAG-04, EXT-04 and wider release obligations remain Pending; scoped
evidence does not change their broader requirements.
