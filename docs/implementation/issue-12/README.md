# Issue #12: family and romantic relationship histories

The explicit graph route now returns admitted family and romantic assertions,
their distinct relationship episodes, supported partial ordering and exact source
evidence. Biological ancestry retains its separate biological-only query.
Serving makes no inference calls. The text route remains the default; automatic
routing and wider correction/refresh behavior remain later tickets.

## Evidence before extraction

[Twelve reviewed annotations](../../../data/references/relationships-v1.json)
cover ten short excerpts from the unchanged captured `core-profiles-v2` corpus.
[The source review](reference-review.md) and [hash freeze](pre-pilot.json) precede
the one paid extraction. Original source revisions, document offsets, paragraph
locators, capture hashes, attribution and licenses are preserved. Amy Mitchell
is a reviewed supporting identity; the other nine reuse the captured catalogue.
All cases are exposed development material, reviewed by an agent, without human
adjudication or independent canon corroboration.

The reference separates Phil/Kathy's marriage, separation and reconciliation;
Phil/Sharon's affair; Grant/Sharon's reconciliation and divorce; Kat/Alfie's first
marriage and actual remarriage; adoption, step-parentage and biological parentage.
Unknown calendar dates stay unknown. Christmas Day has no stated year, adoption
age and leaving hospital are relative, early 2023 is approximate, and March 1996
does not become a day. Explicit timing paraphrases are frozen alternatives.
Software counterexamples additionally cover wards, current/former status,
negation, actor identities, contradictions, ordering cycles and unsafe reviews.

## Actual extraction and conservative admission

The [single Sol pilot](extraction-pilot.json), captured at `9000229`, uses the
shared capped provider adapter and LlamaIndex structured program. Its prompt
contains public source excerpts, character names/aliases/performers and a JSON
schema; reference answers and review notes are withheld.
[The payload inspection](outbound-manifest.json) documents what leaves the
machine. The existing shared non-resetting $5 trial authorization applies.
The initial automatic rejection was resolved after payload inspection and a
new approval review; it is not a current blocker.

| Pilot component | Actual result |
| --- | --- |
| Schema | 1/1 response valid; 12 candidates |
| Exact normalized values | 5/12; precision/recall/F1 0.4167 |
| Resolvable source/quote locators | 2/12 |
| Conservative full-reference-excerpt grounding | 2/12 |
| Reference episode pairs | 0/5 correct with missing matches counted as failures |
| Supported reference ordering | 0/3 correct; 4 model links emitted |
| Raw candidate admission after support review | 0 admitted, 12 held |

The score reports each relation type separately. Values for adoption, biological
parentage and remarriage match; other records have status/timing differences.
Wrong quote endpoints affect ten records. Both correctly located biological
claims conflate two directed relationships into one birth-event episode.
[The content-bound source audit](raw-claim-reviews.json) and
[raw admission](raw-admission.json) retain these failures. Neither model records
nor frozen labels were repaired to make the pilot pass.

For a usable reviewed slice, [the installed batch](claims.json) retains all twelve
raw candidates unchanged and adds the twelve source-reviewed assertions frozen
before the model call. [Reviews](claim-reviews.json) bind each complete record's
hash; [admission](admission.json) admits the curated twelve and holds the raw
twelve. This demonstrates manually curated capability, not successful automatic
extraction. The raw-only and combined projections are exercised in separate
disposable databases with the same frozen source snapshot.

The one paid offline call cost **$0.025226**. The preserved shared ledger is
**$0.386799**, with zero unsettled reservations. Serving costs zero inference
credits; database/hosting costs are excluded. The private key, ledger and all
earlier source/reference inputs remain unchanged apart from the recorded spend.

## Public contract

`RelationshipQuery` uses `kind: relationship_history`, a reviewed `character_id`,
an optional `partner_id` and `max_events` from 1–50 (default 20). Results preserve
each admitted assertion, claim/episode identifiers, source-bound quote locators,
reported status, timing precision and optional `after_claim_id`. Parent/guardian
roles remain directed; romantic pairs are symmetric. Only explicit supported
ordering links establish chronology; otherwise listing order has no temporal
meaning. Ward means subject guardian → object ward, never adoption.

The read-only SQL tool supports `found`, `empty`, `truncated`, `unavailable` and
`unknown_character`. An empty result is not a negative fact. The maintained
projection is immutable for its source snapshot; an identical rerun is idempotent
and a changed batch/review is rejected. All candidates and review decisions remain
inspectable independently of graph inclusion.

`POST /v1/snapshots/{snapshot_id}/relationships` exposes the typed tool;
`GET /v1/snapshots/{snapshot_id}/relationship-claims` returns the audit.
Answer/session requests use `route: graph` and the same `graph` arguments.
Biological queries retain their existing shape. Mixed history/ancestry arguments
are rejected. This graph capability shares the existing `family_graph` execution
allowance, read-only database limits, concurrency, cancellation, context checks,
saved receipts and trace lifecycle. There is no answering-time write/extraction
tool. Stops discard selected assertions and citations and retain a limited answer.

```sh
export DATABASE_URL=postgresql://YOUR_USER@HOST:PORT/YOUR_DATABASE
.venv/bin/ask-phil load data/seed/relationship-pilot-v1.json
.venv/bin/ask-phil install-relationships docs/implementation/issue-12/claims.json docs/implementation/issue-12/claim-reviews.json
```

Start the API against that database, then:

```sh
.venv/bin/ask-phil ask "Explain Kat and Alfie's marriages" --snapshot relationship-pilot-v1 --route graph --history --character kat-slater --partner alfie-moon
.venv/bin/ask-phil relationship-claims --snapshot relationship-pilot-v1
```

Typed arguments determine the selected relationship history; free text is retained
for inspection. Every supported answer remains `partial` because this selected
collection cannot establish exhaustive or present-day relationship coverage.

## Validation and remaining limits

[Initial runtime evidence](runtime-initial.json) records 26 actual public outcomes
across raw-only and curated projections, citation resolution, immutable audit
readback, invalid arguments, API recreation and exact MLflow root/tool outputs.
Curated answers preserve marriage versus separation/reconciliation, explicit
divorce, two marriage episodes, social direction and unknown dates. Raw-only
answers safely abstain; raw graph recall is zero. A bounded result intentionally
does not supply every reference claim. [Regressions](regressions.json) retain the
quality failures and scope limits separately from software capabilities.

Focused checks and strict mypy pass during implementation. Final independent
reviews, full-suite validation and publication evidence are added after review.
Broader graph coverage, corrections, automatic routing, held-out quality and
human/canon acceptance remain outstanding project obligations.
