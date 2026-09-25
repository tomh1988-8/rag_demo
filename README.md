# Ask Phil

An evidence-backed EastEnders demo under development. The CLI and FastAPI expose
captured evidence inspection and a single-query text-RAG answer using LlamaIndex,
PostgreSQL/pgvector and local Ollama models. Answers include resolvable citations,
snapshot coverage, actual MLflow traces and a durable original-response identifier.
Fusion, caching, graph/investigative routes, conversational history and the online
feedback/evaluation loop remain later tickets.

Issue #4 adds partial/clarification outcomes, evidence-linked qualifications and
separate quality scoring. Its [scoped Sol acceptance](docs/implementation/issue-4/cloud/README.md)
records 85 passing software tests, 13 reviewed policy cases and five actual CLI/API
checks. Historical local-model failures remain preserved. This exposed development
matrix does not establish broad-corpus or held-out answer quality.

Issue #5 adds [reviewed real-source ingestion](docs/implementation/issue-5/README.md):
capture Wikipedia, Wikidata and TVmaze inputs; import a frozen batch; inspect source
coverage/exclusions; resolve character aliases separately from performers; and
trace passages to their captured revision and ordered source paragraphs. The small
batch covers three core identities plus one supporting identity. It does not yet
provide the complete 20-character corpus.

The default source snapshot contains **one reviewed passage**, not a complete EastEnders knowledge
base. Gemma 4 E2B QAT is a laptop development convenience. Its smoke results are
not deployment or representative quality evidence. Move to a more capable model
before substantial extraction pilots or serious quality acceptance, and record
that model's own baseline with spending controls configured before paid calls.

## OpenRouter trial

Qwen3.8 Flash, GPT-6 Sol and GLM 5.3 Flash profiles are available with a shared
$5 trial budget. Follow the [private key and spending setup](docs/implementation/openrouter-setup.md)
before selecting a cloud profile. The capped Sol profile passed #4's scoped policy
baseline; Qwen's smoke was rejected and GLM remains untested. Local commands below
keep their existing default. Preserve the shared key and spending ledger.

## Run local text RAG

The local stack uses CPU inference, one loaded model and one inference request at
a time. Initial downloads include roughly 4.3 GB for Gemma 4 E2B QAT and 622 MB for
EmbeddingGemma, plus the runtime images. From this directory:

```sh
docker compose --profile rag up -d db ollama
docker compose --profile rag exec -T ollama ollama pull gemma4:e2b-it-qat
docker compose --profile rag exec -T ollama ollama pull embeddinggemma:300m
docker compose --profile rag up --build --wait --wait-timeout 180
mkdir -p artifacts
docker compose exec -T api ask-phil ask "When does Phil Mitchell first arrive in Walford?" --snapshot phil-arrival-v1 > artifacts/receipt.json
docker compose exec -T api ask-phil response /dev/stdin < artifacts/receipt.json
```

Models are pinned by digest in [local-models.json](config/local-models.json).
The app rejects a missing or changed model; updating a tag requires an explicit
configuration review and new baseline. The `index` service embeds the loaded
snapshot idempotently before MLflow starts. The API answers after that index is
ready. A new source snapshot or embedding configuration needs its own index.

The API is at `http://127.0.0.1:8000` and MLflow at `http://127.0.0.1:5000`.
Use the returned `trace_id` in MLflow; serving, indexing and offline-evaluation
experiments are separate. Models and traces survive service restarts in named
volumes. `ASK_PHIL_PORT`, `ASK_PHIL_MLFLOW_PORT` and `ASK_PHIL_OLLAMA_PORT` override
host ports. These are local services; this setup is not a hosted deployment.

`POST /v1/answers` accepts `question` and `snapshot_id`. It returns an original
response plus a per-response read token. `GET /v1/responses/{response_id}` requires
that token in `Authorization: Bearer ...`; the CLI reads it from the saved receipt.
Keep receipts private; the example saves them in the Git-ignored `artifacts/` directory.
Lookup returns the original answer/context/measurements, without rerunning a model.
There is no assessment-write or feedback endpoint in this slice.

Response status distinguishes `answered`, `partial`, `clarification`,
`insufficient_evidence` and `failed`. Partial/clarification replies identify
`unanswered` parts; `qualifications` carry evidence-linked corrections, conflicts,
explicit negatives and date precision. Optional empty fields stay absent from old
saved responses. An empty assembled context produces a fixed abstention without
answer-model inference. These contract checks do not prove semantic support.

Limits: 500 question characters **and** 1,000 UTF-8 bytes, one query embedding,
exact cosine retrieval at k=3, 1,200 UTF-8 bytes of whole-passage context and one
generation call with at most 512 output tokens in a 4,096-token window. The SDK
timeout is 180 seconds per network operation; it is not a guaranteed wall-clock
cancellation or an account spending cap. No automatic model retries, answer
cache or query fusion is enabled. Oversized passages must be split before indexing.

Local Ollama has no API charge. The labelled zero **estimated API cost** excludes
hardware, electricity and hosting. Unreported token counts remain `null`.
`elapsed_ms` measures answer preparation through final composition; trace flushing,
durable storage and HTTP delivery follow it. Citation validation checks resolution
against assembled context; semantic support still requires evaluation.

## Run evidence inspection without models

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

The image locks Python dependencies through `uv.lock`; PostgreSQL 18 includes
pgvector 0.8.6. Image tags can receive patches, so acceptance records also retain
image IDs. The `inspect` command continues to use deterministic full-text search
and never calls a model. Prefect refresh remains a later ticket.

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

Requires Python 3.12, [uv](https://docs.astral.sh/uv/) and PostgreSQL 18 with pgvector.
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

For text RAG, also start the Docker Ollama service and pull the pinned models as
above. Its default host port is 11435; `ASK_PHIL_OLLAMA_URL` can select another
local Ollama address. Before starting the API:

```sh
uv run ask-phil index --snapshot phil-arrival-v1
```

The explicit `load` and `index` commands need `DATABASE_URL`. Inspection and
answering call HTTP;
`--api-url URL` before the subcommand (or `ASK_PHIL_API_URL`) selects its server.
The API has no fixture-upload endpoint. Load fixtures only as a maintainer in this
local environment. Missing storage returns HTTP 503, unknown snapshot/evidence
identifiers return 404, and invalid query/limit parameters return 422. The CLI
returns a nonzero exit status for request, storage or fixture failures.
Unknown answer snapshots return 404; an unprepared index or unavailable model
configuration returns 503. Invalid requests return 422 before a model outcome is
created. Completed answers, insufficient-evidence replies and generation failures
all receive response identifiers. A generation failure contains a safe message,
an error trace and no unsupported model answer. Infrastructure/validation errors
are HTTP errors, not saved answer outcomes.

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
Model responses are controlled only at the external provider boundary; PostgreSQL,
vector retrieval, API/CLI behavior and MLflow storage remain real.

The [reviewed development cases](data/references/phil-arrival-v1.json) define source
labels independently of retrieval outputs. See the implementation evidence under
`docs/implementation/issue-2/` for actual baseline output and validation results.
Those results measure this deterministic slice, not generative or broad-corpus quality.

## Local model smoke evaluation

After loading and indexing the fixture, with `DATABASE_URL` configured:

```sh
uv run python scripts/evaluate_text_baseline.py --max-cases 2 --output artifacts/my-local-smoke.json
```

The script refuses to overwrite an existing artifact. It makes at most two answer
calls, keeps actual MLflow traces and separates retrieval metrics from context
sufficiency. [RAG reference labels](data/references/phil-arrival-rag-v1.json) reuse
the independently source-reviewed development cases. Missing relevant passages
give undefined (`null`) recall/ranking metrics, not a perfect score. One passage
cannot provide meaningful rank discrimination or broad quality conclusions.

The [issue #3 record](docs/implementation/issue-3/README.md) documents actual results,
limits, failures and the point at which a stronger model should replace this one.
