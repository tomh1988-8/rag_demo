# Issue #11: reviewed biological family graph

The explicit graph route answers biological ancestry and descendant queries from
admitted claims in PostgreSQL. Extracted claims, arguments, evidence and reviews
are retained separately from the derived edges. The text route remains the
default. There is no automatic routing or query-time extraction.

## Reference, extraction and admission

[Four source-reviewed labels](../../../data/references/parentage-v1.json) extend
the existing captured corpus with three short immutable spans. The
[pre-extraction reviews](reference-review.md) and [freeze](pre-pilot.json) precede
the first call. The seven-identity annotation scope is complete for those spans;
Angie and Eric are explicitly outside it. Original source revisions, offsets,
capture hashes, attribution and licenses are retained. All cases are exposed
development material. The source corpus and existing reference files are unchanged.

The [single Sol pilot](extraction-pilot.json) uses LlamaIndex's structured
completion program and Pydantic parser, backed by the existing capped provider
adapter. It sends source spans, identities, prompt and schema; it withholds the
reference labels. The fixed matching rule ignores claim IDs and reports semantic
duplicates separately. Month precision does not become a day. Values and evidence
support are independent measures.

| Measure | Actual pilot result |
| --- | --- |
| Schema | 1/1 valid response |
| Normalized values | 4/4 correct; precision/recall/F1 1.0 on this slice |
| Resolvable evidence spans | 3/4 |
| Frozen full-reference-span grounding | 2/4 |
| Independent semantic support audit | 4/4 meanings source-supported |
| Admission | 2 admitted biological claims; 2 held claims |

The [content-bound audit](claim-reviews.json) checked every model claim against
the unchanged source and reference. Peggy's quoted sentence has 105 characters,
but its model end offset is 104: it is held for `evidence_span`. Den's shorter
adoption quote resolves and supports its meaning, but fails the deliberately
conservative full-reference-span score; adoption stays outside the biological
tree. Neither record nor label was repaired to make the pilot pass. The
[raw normalized claims](claims.json) and [admission decisions](admission.json)
preserve both outcomes. Agent source review is not human adjudication or
independent canon corroboration.

Admission also checks reviewed identities, exact source/quote spans, affirmative
certainty, biological meaning, content-bound support review, explicit negation,
competing biological parents and cycles. Unsupported, uncertain or conflicting
claims remain available for review. Quote resolution alone never grants admission.
Different immutable source snapshots require separate projection installation.
Each snapshot's graph cannot be overwritten; changed interpretations and wider
refresh/correction lifecycle remain #15.

## Public contract

`FamilyQuery` requires a reviewed character ID and `ancestors` or `descendants`.
Depth is 1–6, default 3; maximum returned paths is 1–50, default 20. Recursive SQL
uses only admitted biological edges, with cycle protection, a result limit and
read-only connections with statement/lock deadlines. Results carry parent→child
edge orientation, claim IDs, exact evidence locators and source/graph fingerprints.
An ancestor traversal lists child→parent paths; descendant paths run parent→child.

`found`, `empty`, `truncated`, `unavailable` and `unknown_character` are explicit
tool outcomes. No result establishes a negative. Graph answers with evidence are
`partial` because this small collection cannot establish an exhaustive family
tree. Stops after the source snapshot is loaded produce saved limited outcomes.
Initial publication/source-storage failures can return HTTP 503 without a receipt;
direct typed-tool stops also return 503. Storage failures produce HTTP 503,
missing snapshots 404 and invalid arguments 422. Explicit graph queries never
fall back to text or infer a relative from generated conversation claims.
Registered withdrawn publications are rejected for new answers; historical
citations and receipts remain available. New active snapshots without an
installed compatible graph return `unavailable`.

`POST /v1/snapshots/{snapshot_id}/family` exposes the typed read-only tool.
`GET /v1/snapshots/{snapshot_id}/family-claims` exposes retained claims, reviews and
admission decisions. `POST /v1/answers` and session turns accept `route: graph`
plus `graph` arguments. A route/argument mismatch fails validation. Answer
receipts retain the explicit override, executed query, graph paths, citations,
source snapshot, actual MLflow trace, elapsed time and tool count. Model settings
are null and inference usage/cost are zero because this route makes no model calls.

Example setup against a disposable database:

```sh
export DATABASE_URL=postgresql://YOUR_USER@127.0.0.1:5432/YOUR_DATABASE
.venv/bin/ask-phil load data/seed/family-pilot-v1.json
.venv/bin/ask-phil install-family docs/implementation/issue-11/claims.json docs/implementation/issue-11/claim-reviews.json
```

Run the API with that database, then:

```sh
.venv/bin/ask-phil ask "Show Ben's biological ancestors" --snapshot family-pilot-v1 --route graph --character ben-mitchell --direction ancestors --depth 3
.venv/bin/ask-phil family-claims --snapshot family-pilot-v1
```

Installation is a maintainer command. Answering has no graph-write or extraction
capability. Canonical typed arguments determine the selected character and
traversal; the free-text question is retained for inspection.

## Runtime and quality limits

[Final runtime evidence](runtime-final.json), bound to [the accepted revision](runtime-final-revision.json),
records eight real HTTP responses, one
CLI response, edge-citation resolution, typed tool output, invalid input,
original-response readback after API recreation and actual MLflow span readback.
The raw pilot projection returns Ben's Phil/Kathy paths and excludes Peggy's
malformed locator and Den's adoption. Against the complete biological reference,
path precision is 1.0, recall 2/3 and F1 0.8: completeness fails and remains a
[recorded regression](regressions.json). Full-reference real-database tests separately exercise the
supported Peggy→Phil→Ben chain, both directions and bounds. Software capability
and conservative admission do not turn missing model evidence into a quality pass.

The one paid offline extraction call cost **$0.0184885**. All graph serving calls
cost zero inference credits. The preserved shared non-resetting $5 ledger totals
**$0.361573**, with zero unsettled reservations. No credentials, response read
tokens or session tokens are published. Hosting/database costs are excluded.

The [corrected offline rescore](extraction-score-final.json) preserves all numeric
pilot results after repairing span-aware duplicate matching. The raw pilot and
reference remain unchanged. [Extraction trace readback](extraction-trace-readback.json)
also confirms actual MLflow raw output and saved claims match.

Focused public tests cover claim admission, semantic-versus-grounding scoring,
real SQL paths, API/CLI, immutable reruns, scope/identity limits, missing graphs,
denied capabilities and conversation reference isolation. Strict mypy checks 70
files and Ruff/formatting pass. The focused graph/text integration run passed
31 tests, and 13 domain/scorer tests passed. [Independent reviews](review.md) have
zero remaining findings on either axis. The single final full-suite run passed **304 tests**, with zero failures, errors or skips
in 648.59 seconds. [Validation](validation.json) binds these results to `8d58624`;
[the software report](software-tests.xml) retains the runner output. An existing
Starlette/httpx deprecation warning remains.

The pilot was captured while implementation was uncommitted: its `code_revision`
is the starting HEAD and its application hash describes the capture-time working
tree. Its frozen data, prompt and schema hashes still match the final extraction
contract. Subsequent changes strengthen admission and serving behavior; they do
not constitute another model observation. Final validation binds the accepted
implementation commit and source hashes. The earlier runtime capture is retained
alongside final-revision runtime checks.

Implementation uses the installed LlamaIndex structured program. Its public
[structured-output documentation](https://developers.llamaindex.ai/python/examples/structured_outputs/structured_outputs/)
describes the schema-plus-parser contract; schema validity does not establish
semantic support, which this slice measures separately.

## Publication status

Implementation and acceptance evidence are committed locally at `8b11885`.
[The publication record](publication.json) records the automatic approval review
rejection of the push to GitHub `main`. Explicit approval for publication and
tracker closure is pending; no remote changes or issue closure have occurred.
