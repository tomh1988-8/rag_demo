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

## Acceptance results

At executable revision `0322b2e`, the full Docker suite passed **115 tests**, with
zero failures or skips, against real PostgreSQL. The suite ran once after the final
code changes. Ruff passed and strict mypy passed all 33 source files. The existing
seed fingerprint is unchanged. The one upstream Starlette/httpx deprecation warning
does not affect the results. [Validation and exact input hashes](validation.json)
and the [original JUnit result](software-tests.xml) preserve the run.

The [retention report](retention-report.json) records the frozen batch/reference
hashes, snapshot fingerprint, ordered reviewed denominators and missing-content
report. The [live compatibility record](live-compatibility.json) records all eight
successful responses plus the earlier failed discovery. Live capture preceded the
Den alias correction; its original artifact remains unchanged and all narrative
spans still match the corrected frozen batch.

[Independent review](review.md) has zero remaining findings on both Standards and
Spec. The omitted Den aliases, combined test cases and repeated attribution data
were repaired before acceptance. The project register now passes AD-03.2 and
EXT-01 for this sample; RAG-01 and AD-03.4 retain their broader pending obligations.
Full-corpus parsing, semantic extraction, graph coverage and answer quality remain
outside this ticket's acceptance claim. No application deployment is implied:
the existing long-lived Docker API/MLflow services still use the earlier #3 image.

## Publication

[Commit b6b45cb](https://github.com/tomh1988-8/rag_demo/commit/b6b45cb5eea3402ffe2be466e1693ef91af4ecf5) publishes the exact accepted local tree `97f9fa4981785294c7dcb7144bcd59a065ecb740` from `223e5db`. The authenticated GitHub connector advanced `main` without forcing; remote revision/tree readback passed before issue #5 was closed. All eight checked criteria, the acceptance body and closed state were read back. This receipt is added in a subsequent documentation commit.
