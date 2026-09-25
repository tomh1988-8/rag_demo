# Issue #5 — real source ingestion

The maintainer can capture Wikipedia HTML, Wikidata identities and TVmaze episode
metadata, import a reviewed batch atomically into PostgreSQL, then inspect source
coverage, scope exclusions, original content and character identities through the
CLI/API. Imported citations retain capture/revision, section and ordered paragraph
provenance. Existing seed and response documents retain their original shapes.

## Reproduce

With a development `DATABASE_URL` configured and the current API running:

```sh
uv run ask-phil import-sources data/sources/real-sources-v1.json.gz --snapshot real-sources-v1
uv run ask-phil source-report --snapshot real-sources-v1
uv run ask-phil resolve-character 'Sharon Rickman' --snapshot real-sources-v1
uv run ask-phil resolve-character 'Letitia Dean' --snapshot real-sources-v1
uv run ask-phil inspect 'signet ring' --snapshot real-sources-v1
uv run ask-phil source kat-wiki --snapshot real-sources-v1
uv run ask-phil source episode --snapshot real-sources-v1
```

Only the import command needs database credentials. Reads use the shared HTTP
API. `source-report` returns counts, identities, licenses, attribution and gaps;
`source` returns the full retained payload plus ordered spans or structured
metadata. The Wikipedia passage citations still resolve through the existing
evidence endpoint. There is no public upload endpoint.

To obtain a separately saved current batch:

```sh
uv run ask-phil capture-sources data/sources/real-sources-plan-v1.json artifacts/new-sources.json.gz
```

The command refuses to overwrite an artifact. A changed Wikipedia revision needs
scope review before import. Capture and parsing failures leave the currently
stored snapshots untouched; this does not implement the active-snapshot refresh
and rollback workflow reserved for #6.

## Evidence and limits

The frozen eight-input batch has three core identities and one supporting identity.
It retains **79/79 reviewed main-series paragraphs**, produces 138 retrieval
passages, excludes five spin-off/podcast paragraphs, and holds 198 other paragraphs
for review. The denominator is the reviewed narrative subset, not the entire
article or canon. Three Wikidata records and one TVmaze episode remain inspectable
metadata, outside narrative retrieval. The episode's absent summary is reported.

[Source-use inventory](../../../data/sources/README.md),
[review notes](source-review.md) and the versioned paragraph labels define the
source roles, scope and independent expected content. The new CLI also captured
all eight sources in a separately recorded live check; its narrative projection
matched the frozen sample. A failed TVmaze endpoint discovery is retained in the
record. No paid model calls were needed or made.

TDD first exposed missing identity/parser interfaces, scope/provenance failures,
missing HTTP/CLI operations, malformed nested JSON, an unreported missing section,
conflicting scope rules and conflicting duplicate records. Each was fixed through
the agreed public boundaries. The live tests use real PostgreSQL and HTTP; only
external source responses are substituted in deterministic source-failure tests.

Validation and independent review results will be recorded before publication.
Full-corpus parsing, semantic extraction, graph coverage and answer quality remain
outside this ticket's acceptance claim.
