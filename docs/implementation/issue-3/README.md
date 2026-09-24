# Issue #3 implementation evidence

24 September 2026. [Issue #3](https://github.com/tomh1988-8/rag_demo/issues/3):
single-query, uncached text RAG using LlamaIndex, PostgreSQL/pgvector, local Ollama
and MLflow. Review baseline: `573a8ad`. Runtime acceptance and both independent review axes passed; verified tracker
closure is recorded in
[validation.json](validation.json) and [review.md](review.md).

## Model choice and migration point

The user authorised installing a current open model sized for this 8 GB CPU laptop.
The selected [Gemma 4 E2B QAT](https://ollama.com/library/gemma4:e2b-it-qat) package
is about 4.3 GB; [EmbeddingGemma](https://ollama.com/library/embeddinggemma) is about
622 MB. Ollama 0.34.4 runs in Docker with cloud use disabled, one loaded model,
one inference request at a time and unload-after-call (`keep_alive=0`). The existing
host Ollama 0.5.12 and its Qwen model were left intact.

The [configuration](../../../config/local-models.json) pins both full model digests,
768 embedding dimensions, temperature 0, seed 17, a 4,096-token generation window,
256 output tokens and a 180-second SDK network timeout. Temperature 0 is this
development baseline's greedy setting; it is not a claim that it is the provider's
recommended setting for all tasks. [Google's retrieval prefixes](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers)
are versioned with the embedding identity. A small LlamaIndex `BaseEmbedding`
integration retains Ollama's reported token count and sets `truncate=false`;
the standard embedding adapter discards this usage and defaults to truncation.
Model tags are checked against the recorded digests before requests.

**The laptop model is for development and smoke checks only.** The user explicitly
excluded it as a deployment or serious quality-testing model. Recommend/configure
a stronger model before representative quality comparisons (#9), substantive
claim-extraction pilots (#11 onward), or judging broad roster answers (#7).
Those gates require a new provider/model baseline; these results do not transfer.
Paid-provider keys and conservative account/request controls must be configured
locally before its first paid call. No paid API calls were made for this slice.

## Bounds and truthful measurements

- Questions: 1–500 characters and at most 1,000 UTF-8 bytes. Passage embedding:
  at most 1,800 UTF-8 bytes plus the fixed task prefix, with provider truncation disabled.
- One query embedding, exact pgvector cosine retrieval at k=3, 1,200 UTF-8 bytes
  of complete evidence spans, and one answer call. No model retries, cache or fusion.
- The small context byte limits conservatively reserve room in the 4,096-token
  model window; they are not a measured tokenizer count. Token usage is reported
  only when returned by the provider. Missing values remain `null`.
- `elapsed_ms` ends after final composition; trace flushing, response persistence
  and HTTP delivery are outside that measurement. Network timeouts are not a
  guaranteed end-to-end deadline or cancellation of provider computation.
- Zero estimated API cost means local Ollama API charges only. Hardware, power
  and hosting costs are unmeasured. Indexing, serving and offline evaluation use
  separate MLflow experiments and expenditure labels.

The Python packages are locked in `uv.lock`; actual package, source, prompt,
reference and configuration identities accompany each saved baseline. The
application fingerprint covers the installed Python modules; the containing Git
commit links the code and evidence without a circular commit hash in the artifact.

## Evidence and original-response contract

Retrieval filters by immutable snapshot fingerprint and embedding identity. It
returns original source passages; the assembled context records which whole spans
fit its budget. Citations must uniquely reference that context and resolve through
the existing snapshot/evidence endpoint. These rules establish resolution, not
semantic claim support or independent canon corroboration.

Every answer, insufficient-evidence reply and generation failure has a stable
response ID. PostgreSQL preserves the original final persona answer, question,
citations, retrieved/context passages, snapshot, executed route, model settings,
prompt/application fingerprints, usage, latency and completed MLflow trace ID.
A separately returned bearer read token resolves exactly that response; only its
hash is stored, and it is excluded from traces and published evidence. There is no
assessment-write or feedback endpoint. Validation and infrastructure errors are
HTTP errors before a served answer outcome, with 422/404/503 distinctions.

## Independent development labels and scorer definitions

The [RAG references](../../../data/references/phil-arrival-rag-v1.json) reuse the
source-reviewed arrival fact and absent-parentage case from issue #2. Reviewers,
source revision, offsets and limitations remain in the original reference file.
No generated answer supplied these labels. There is one passage and one fact group,
with one answerable and one unanswerable exposed development question.

Matching uses exact IDs within this snapshot. Deduplicate before selecting top k.
Recall@k divides relevant returned IDs by all labelled relevant IDs; Hit@k is
binary and MRR@k uses the first relevant rank. A case with no relevant passages
has no positive denominator, so these measures are null. Context fact coverage
uses independently labelled sufficient sets for each required fact, divided by
the required-fact count. An unanswerable case has no sufficient answer context,
even if the nearest-neighbour query returns an unrelated passage. Empty fact
labels never yield a vacuous perfect sufficiency result.

The scorer's two-fact worked example separately exposes context loss despite a
retrieval hit. The one-passage live fixture cannot establish meaningful ranking
quality, broad answerability, persona quality, held-out performance or deployment
readiness. Serious evaluation belongs after the model migration above.

## Initial live probe and retained failure

[Initial probe](local-probe-v0.json): two actual local-model outcomes and completed
MLflow traces. The arrival answer gave February 1990 and the supported Arches
detail; the parentage question declined to answer. Recorded latencies were about
21.8 and 18.9 seconds. Query embedding input counts were 19 and 17; generation
input/output counts were 240/50 and 238/28. These are observations, not an SLA.

The arrival answer was neutral third-person wording, so its basic Phil-style
acceptance was weak. Further [v1](local-probe-v1.json) and [v2](local-probe-v2.json)
probes added the opening but still used "He" or "Phil Mitchell". A real CLI/API
[serving probe](serving-probe-v1.json) also failed the first-person check. All are
retained, with their original prompt/application identities. The v1 artifact was
originally logged to MLflow as `text-baseline-v1.json`; it is a failed development
attempt, not the accepted baseline.

An explicit grammar example, "Phil did X" to "I did X", resolved the exposed
arrival case in [v3](local-probe-v3.json). This is development-set prompt tuning,
not a held-out improvement claim. The final Docker baseline rechecked the
absent-parentage case and public API/CLI path with this prompt successfully.

The first Docker build also exposed an omitted allowlist entry for configuration
and the evaluation runner. `.dockerignore` now includes both; the rebuilt runtime
and test images succeeded. Final startup and persistence checks passed below.

## TDD and review

The user-approved retrieval, conversation API/CLI and scorer seams were reused.
Observed red-to-green steps included missing retrieval/context modules; oversized
embedding inputs not rejected; no answer API/CLI; an uncaught invented citation;
changed model identity accepted; missing/unindexed snapshots escaping as exceptions;
missing separate embedding usage; and an oversized multibyte question accepted.
Each was followed by its implementation and relevant-file checks. Additional
regressions cover idempotent indexing, snapshot/model isolation, null metric
denominators, original-response lookup after application recreation and private
read tokens. External model HTTP responses are substituted; PostgreSQL/pgvector,
MLflow, application behavior and CLI HTTP transport are real.

The code-review skill used independent Standards and Spec agents. The minor
duplicated MLflow experiment setup was consolidated; the Standards follow-up found
no remaining findings. Spec review identified the final persona, complete client
latency, restart and register evidence as acceptance gaps; the records below
address them; the final independent readback confirmed no remaining findings.

The [pre-refinement test suite](pre-prompt-docker-tests.log) passed all 31 tests.
The final prompt change was driven by the live style failure, so the rebuilt
image was checked again: [32 tests passed](docker-tests.log), with zero failures,
errors or skips ([JUnit](tests.xml)). Static lint/format and strict type checking
passed (21 source files). The only pytest warning is an upstream Starlette/httpx
deprecation. Compose also noted the retained earlier test container; MLflow emitted
a non-fatal missing OS username warning for the numeric container UID. Actual
traces and the evaluation run were persisted and read back successfully.

## Final Docker baseline and restart acceptance

[Accepted development baseline](text-baseline-v4.json), MLflow run
`5722d6dd4374444eb6a6d7c1ce357f6a`, uses application fingerprint
`42cfb7575ff26aac74eb35e65233b69d426238ff5f78ae50c9773764781a43d9`.
The actual prompt is retained in each trace; its SHA-256 is
`a5c55194fed5bcb97322c4bdcf04644094c11d4cfd8fa73846d6f88599cb18bf`.

| Exposed case | Actual final outcome | Observed usage and application latency |
| --- | --- | --- |
| Arrival | First-person answer beginning "Right, listen. I first arrived", February 1990, supported Arches detail, one resolvable citation | 341 generation input / 55 output / 19 query-embedding input tokens; 27.3 s |
| Parentage absent from fixture | Insufficient evidence, no citations; no remembered answer supplied | 339 generation input / 28 output / 17 query-embedding input tokens; 21.0 s |

The positive case has Recall@3, Hit@3, MRR@3 and context fact coverage of 1 over
one relevant passage/one required fact. The negative case has zero positive labels,
null metric denominators and insufficient context. Neither row is an aggregate
quality estimate. No semantic judge or complete persona evaluation is claimed.

The separate [CLI/API serving check](docker-serving.json) returned the same supported
first-person answer. Complete client wall time was **30.4 s**, including CLI startup,
response delivery/parsing, trace flush, storage and initial assertions; application
`elapsed_ms` was **24.2 s**. These are different explicitly scoped measurements.
After restarting PostgreSQL, the API and MLflow, lookup returned the exact original
response and citation. Missing/wrong read tokens returned 404. Neither the seed nor
the answer was regenerated. The [saved trace](docker-serving-trace.json) resolved
through the restarted MLflow HTTP server and shows the actual retrieval, query
embedding, assembled context and answer call. Indexing, serving and offline
evaluation are separate experiments.

The [validation record](validation.json) retains code/configuration fingerprints,
container image IDs, versions, checklist results and limitations. Fourteen recorded
live answer calls include the failed development attempts; each invocation had
its stated one/two-call budget, 256 output tokens per call and no retry. Paid API
calls: zero. Model memory peak, deployment performance and hardware costs were not
measured. AD-09.3 remains Pending for complete routing/online accounting; five
initial text-slice obligations gain scoped Pass evidence (13 Pass, 38 Pending).

## Token-accounting review correction

The final Standards review caught an incorrect MLflow aggregate: answer spans
reported input/output counts but omitted their total, so the trace total counted
only embedding tokens. The [earlier v3 baseline](text-baseline-v3.json) and earlier
probes remain unchanged as historical evidence; their aggregate `total_tokens`
must not be used. Their per-call input/output values were correct.

The [failing regression](token-accounting-red.log) reproduced 12 rather than the
independently expected 57 total tokens. The [corrected check](token-accounting-green.log)
passes through real PostgreSQL/API/MLflow for both complete and missing usage.
Answer totals are supplied when both counts are known; `usage_complete` explicitly
distinguishes complete requests from aggregates of reported counts. Missing values
remain null. The final v4 baseline and serving trace were regenerated with the
corrected application: arrival totals are 360 input, 55 output, 415 total; the
absent-parentage case is 356 input, 28 output, 384 total. These include query
embedding input, while indexing is separate. Log transcript trailing whitespace
was normalised without changing messages.

One [test run](cold-start-timeout-tests.log) exceeded the CLI lookup subprocess's
15-second cold-start allowance. Its allowance now matches the existing 30-second
CLI request test; all response, citation and private-lookup assertions are retained.
The final 32-test run passed. A [restart helper attempt](startup-readiness-retry.log)
queried MLflow's health endpoint before startup finished. After waiting for that
service's readiness, original-response and trace readback passed without repeating
the answer or baseline. These checks are functional acceptance, not latency gates.

## Existing local stack

The accepted stack remains available under Compose project **`ask-phil-issue3`**,
with models, PostgreSQL data and MLflow data in its named volumes. Use that project
name on this machine to reuse the installed models:

```sh
docker compose -p ask-phil-issue3 --profile rag ps
docker compose -p ask-phil-issue3 exec -T api ask-phil ask "When does Phil Mitchell first arrive in Walford?" --snapshot phil-arrival-v1
```

API: `http://127.0.0.1:8000`; MLflow: `http://127.0.0.1:5000`.
`docker compose -p ask-phil-issue3 --profile rag down` stops it while retaining
the named data/model volumes. The repository's general setup instructions use
the default project name, which creates different volumes on first use.
