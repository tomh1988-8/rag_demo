# Ask Phil

An evidence-backed EastEnders demo under development. The first slice implements
[issue #2](https://github.com/tomh1988-8/rag_demo/issues/2): inspecting a small captured
source fixture through a CLI, shared FastAPI application and PostgreSQL.
It returns excerpts and provenance, with an explicit empty-result limitation.
It does not generate answers or call models. The chatbot, RAG routes and online
feedback/evaluation loop belong to subsequent tickets.

## Run with Docker Compose

Requires Docker Engine with the Compose plugin (v2 or newer). Acceptance was run
with Engine 29.8.1 and Compose 5.5.1. From this directory:

```sh
docker compose up --build --wait
docker compose exec api ask-phil inspect "When does Phil Mitchell first arrive in Walford?" --snapshot phil-arrival-v1
docker compose exec api ask-phil inspect "Who is Phil Mitchell's mother?" --snapshot phil-arrival-v1
```

The first command starts PostgreSQL, loads the seed idempotently, then starts the
API at `http://127.0.0.1:8000`. Open `/docs` for its request/response contract.
Set `ASK_PHIL_PORT` before startup to choose another host port. The database is
only exposed inside the Compose network. Its documented demo password is for this
local stack. No external credentials or paid APIs are needed.

`docker compose restart db api` preserves the named volume and evidence IDs.
`docker compose down` stops this project while preserving its data. Do not remove
the volume unless you intend to discard the local snapshot data.

The image locks Python dependencies through `uv.lock`; PostgreSQL uses major
version 18. Image tags can receive patches, so record image IDs with acceptance
runs when comparing environments. This first deterministic slice uses PostgreSQL
full-text search. Vector retrieval, LlamaIndex, Prefect refresh and MLflow arrive
in their dependent tickets; no stub integrations stand in for them here.

For an Ubuntu 24.04 development host, the optional
[installer](scripts/install-docker-ubuntu.sh) follows Docker's
[official apt setup](https://docs.docker.com/engine/install/ubuntu/):

```sh
sudo bash scripts/install-docker-ubuntu.sh "$USER"
```

It installs Engine and Compose, enables the daemon, and grants the named account
Docker group access. Log out and back in, or use `newgrp docker`, to activate the
new group in your shell. Existing conflicting packages cause it to stop for review.

## Native development

Requires Python 3.12, [uv](https://docs.astral.sh/uv/) and PostgreSQL 18.
Create an empty development database, then:

```sh
uv sync --frozen
export DATABASE_URL='postgresql://YOUR_USER@127.0.0.1:5432/ask_phil'
uv run ask-phil load data/seed/phil-arrival-v1.json
uv run uvicorn ask_phil.api:create_app --factory --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
uv run ask-phil inspect "When does Phil Mitchell first arrive in Walford?" --snapshot phil-arrival-v1
```

Only the explicit `load` command needs `DATABASE_URL`. Inspection calls HTTP;
`--api-url URL` before the subcommand (or `ASK_PHIL_API_URL`) selects its server.
The API has no fixture-upload endpoint. Load fixtures only as a maintainer in this
local environment. Missing storage returns HTTP 503, unknown snapshot/evidence
identifiers return 404, and invalid query/limit parameters return 422. The CLI
returns a nonzero exit status for request, storage or fixture failures.

## Evidence contract

The [source record](data/seed/README.md) documents the retained passage, license,
capture and source revision, and its limitations. This is **source-supported**
evidence, without independent corroboration. Capture time does not establish
complete storyline coverage. No match means only that this fixture's search did
not find an excerpt; it does not prove that something never happened.

Search uses PostgreSQL's English full-text configuration and `plainto_tsquery`:
all non-stopword query terms must match after stemming. It is a deliberately
simple, deterministic inspection baseline; it does not understand synonyms or
decide whether a passage completely answers a question. Limits are 1–20 results
and 1–500 query characters, with rank ties ordered by evidence ID.

Use `GET /v1/snapshots/{snapshot_id}/evidence/{evidence_id}` to resolve a saved
citation without searching again. Snapshots are immutable: identical imports are
safe, while changed content or provenance requires a new snapshot ID. Imports
and their passages commit atomically. Fingerprints cover validated canonical JSON;
passages also carry hashes and offsets into the retained source text.

## Tests and deterministic baseline

```sh
uv run mypy
uv run ruff check .
uv run pytest tests/test_provenance.py -q
docker compose --profile test run --build --rm test
```

For native integration tests, supply a **disposable PostgreSQL admin connection**:

```sh
uv run pytest tests/test_inspection.py -q --test-database-url postgresql://YOUR_USER@127.0.0.1:5432/postgres
uv run pytest -q --test-database-url postgresql://YOUR_USER@127.0.0.1:5432/postgres
```

Integration tests create uniquely named databases and drop only those databases
afterward. They fail explicitly if the test connection is missing; they do not
silently substitute an in-memory store. The CLI tests use a real localhost HTTP
server. Routine tests use the committed fixture and never fetch live sources.

The [reviewed development cases](data/references/phil-arrival-v1.json) define source
labels independently of retrieval outputs. See the implementation evidence under
`docs/implementation/issue-2/` for actual baseline output and validation results.
Those results measure this deterministic slice, not generative or broad-corpus quality.
