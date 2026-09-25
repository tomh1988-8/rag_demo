# Issue #5 implementation

Baseline/review fixed point: `f2de4a7942441c619d4b2c137c16ffed05a89144`.
Origin: GitHub issue #5 under specification #1. Work on the current branch.

Use the already confirmed source-ingestion/refresh and conversation API/CLI
boundaries, including exposed identity and scope rules. No new test boundary is
needed. Keep the existing seed fingerprints and saved response shapes compatible.

1. Resolve reviewed aliases to stable character identities, retaining performers
   separately and returning explicit ambiguous/unknown results.
2. Capture bounded official HTML/JSON inputs and preserve their bytes, revisions,
   attribution and capture dates. Parse Wikipedia paragraphs in source order;
   preserve excluded and unreviewed spans and section identifiers. Admit narrative
   spans only under a revision-bound reviewed scope policy. Keep Wikidata identity
   records and TVmaze broadcast metadata outside narrative retrieval.
3. Import atomically through the existing PostgreSQL snapshot boundary and expose
   provenance, scope/retention reports, identities and captured records through
   maintainer CLI and read-only API inspection.
4. Exercise malformed/incomplete inputs, missing/duplicate records, reimports,
   evidence integrity and old-contract compatibility. Record a separate live
   source check. This deterministic ticket needs no paid model calls.
5. Run focused tests/type checks during implementation; run the full suite once
   at completion. Use independent Standards and Spec review agents, resolve
   findings, update evidence/handoff, commit, publish and verify the remote tree.

Refresh scheduling/publication recovery remains #6; extraction/admission remains
#11 onward; context expansion remains #24. The new importer retains the ordered
source context those tickets will need.

Implementation and review are complete at `0322b2e`: 115 Docker tests, Ruff and
strict mypy pass. Both independent review axes have zero remaining findings.
The acceptance README links exact source/code identities and the saved results.
