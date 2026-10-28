# Issue #16: evidenced character connections

The explicit graph route composes admitted biological parentage, social and romantic
history, and shared incident roles into bounded character paths. Every step retains
its original Claim, direction, timing and source locators. Wording follows those
typed steps without an inference call. Source support is not independent canon
corroboration.

The starting revision is `2412c23172b7c343a37ce23463fd0ecece98920e` on `main`.
The scope is [GitHub #16](https://github.com/tomh1988-8/rag_demo/issues/16) and its
[retained live specification](issue.json). TDD uses the previously confirmed typed
graph, conversation, bounded execution and evaluation seams.

## Public contract

```sh
ask-phil ask 'How are Peggy and Ben connected?' \
  --snapshot connections-pilot-v1 --route graph \
  --character peggy-mitchell --connect-to ben-mitchell \
  --depth 2 --max-paths 5 --max-expansions 500
```

`POST /v1/answers` and session turns accept:

```json
{
  "snapshot_id": "connections-pilot-v1",
  "question": "How are Peggy and Ben connected?",
  "route": "graph",
  "graph": {
    "kind": "connection",
    "character_id": "peggy-mitchell",
    "target_id": "ben-mitchell",
    "max_depth": 2,
    "max_paths": 5,
    "max_expansions": 500
  }
}
```

`POST /v1/snapshots/{snapshot_id}/connections` exposes the same typed graph
result. It reports the actual source fingerprint, all installed projection
fingerprints, names, paths, examined path count and expansion-limit flag. The
answer adds per-step wording, resolvable source citations, the explicit route
override, execution accounting and the actual `connection_graph` MLflow span.
Saved responses retain their identities and evidence after application restart.

Both endpoints require the `connection_graph` execution capability. Queries have
two distinct reviewed character IDs, depth 1–6 (default 3), result paths 1–20
(default 5) and expansions 1–5,000 (default 500). One expansion is a non-origin
walk state; a single extra state detects truncation. PostgreSQL statements also
obey the existing request deadline and five-second statement cap. Reaching a
destination stops that branch. Characters and incident identities cannot repeat
within a path. An expansion or result limit produces `truncated`, including when
no destination has yet been found. Depth is always disclosed in the query.

The traversal reads existing immutable admitted SQL projections; it installs no
new graph or unchecked links. Available graph families can be used independently.
Queries pin one source/publication and compare all installed projection identities.
Absent graph families remain visible in `graphs`. A missing graph, unknown
character, empty bounded search or stopped request cannot establish programme-wide
absence. Complete evidence must fit the existing context budget; otherwise the
answer abstains and retains the actual context-limit outcome rather than excerpting
away a qualification. Published disputes remain outside paths and can be explained
with their complete retained review groups.

## Permitted meanings

- Biological edges can be followed parent-to-child or child-to-parent. Parent,
  child, grandparent, grandchild and sibling meanings require the corresponding
  all-biological one- or two-step path. No gender, cousin or social ancestry is
  inferred. Biological connections use admitted family edges exclusively;
  biological assertions remain inspectable in relationship history without
  providing an alternative admission path.
- Social parentage and ward ties preserve subject-to-object or reverse direction.
  Romantic assertions are traversable symmetrically; their relation, episode,
  captured current/former/unknown status and story timing remain intact. An
  historical marriage, separation, divorce or affair does not imply a current tie.
- A shared-event step requires explicit admitted participants in the same reviewed
  incident ID. It retains every admitted stage and role for that incident, including
  separately supported commission, legal outcomes and explicitly false accounts.
  Accusation and conviction never become commission. Distinct incident IDs cannot
  be joined just because labels or themes resemble each other. Pregnancy alone
  supplies no parentage, and a death passage supplies no unmentioned witness.
- Shared themes, unclassified text subjects, co-appearance, hallucinations,
  performers, held and unreviewed Claims do not create adjacency.

## Reviewed evidence

[Ten cases](../../../data/references/connections-v1.json) were prepared before
implementation from the existing exposed parentage, relationship, crime/justice
and life-event references. They cover direct adoption, a biological grandparent,
alternative paths, misleading conviction, composition across graph families,
no path, cycles, depth, text-only exclusions and performer identity. The combined
[source snapshot](../../../data/seed/connections-pilot-v1.json) preserves exact
existing passages and their individual source metadata; original inputs and
historical extraction scores are unchanged. [Content-bound reviews](claim-reviews.json)
retain the reference assertions, including the non-biological parentage candidate
which stays outside the family projection.

The acceptance command captures actual API, CLI and session outputs, compares
actual MLflow root/tool outputs, resolves citations, reads every component audit,
resets sessions and retrieves original responses after restart:

```sh
.venv/bin/python scripts/record_connection_acceptance.py \
  --database-url postgresql://USER:PASSWORD@HOST:PORT/postgres \
  --output artifacts/connections-new.json \
  --tracking-uri sqlite:///artifacts/connections-new-mlflow.db
```

Existing biological, relationship-history and event queries run through their own
public answer contracts alongside connections. Component scores report result
correctness, step meaning and source resolution separately. Final prose support
requires a separate source-based review; component scores do not manufacture it.
These exposed curated cases establish scoped composition capability, while broad
graph coverage, automatic investigation/routing and held-out release quality remain
separate tickets. No new extraction or paid model call is required.

Run software verification against disposable PostgreSQL databases:

```sh
ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres \
  .venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
```

Preserve the non-resetting $5 ledger at $0.464981, its zero unsettled reservations,
the private key and the user's pre-existing workspace changes. Software results,
source-review findings, retained failures and revision linkage are recorded with
this issue's validation and review artifacts.
