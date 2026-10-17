# Issue #7 — all 20 core text profiles

The curated roster uses one generic import, source inventory and text answer path.
It is a prominence-based selection, with source-supported supporting characters
and earlier history; it is not a ranking, exhaustive canon or checked graph.

## Capture and import

`data/sources/core-profiles-v2.json.gz` retains the complete 20 HTTP payloads,
their original check times/hashes, reviewed character identities and
revision-specific narrative scope policies. The decoded payload total is
8,727,521 bytes. The import admits 461 paragraphs as 794 exact-span passages,
excludes six explicit spin-off/podcast paragraphs, and retains 585 unreviewed
paragraphs outside retrieval. Every admitted passage fits the existing
1,200-byte serialized context alone. Answer-time fetching is unchanged.

Use the existing configured PostgreSQL/pgvector and pinned local embedding model:

```sh
uv run ask-phil refresh-sources data/sources/core-profiles-v2.json.gz
uv run ask-phil publication
uv run ask-phil source-report --snapshot SNAPSHOT_ID
uv run ask-phil source ben-mitchell-wiki --snapshot SNAPSHOT_ID
uv run ask-phil resolve-character 'Kat Moon' --snapshot SNAPSHOT_ID
```

Replace `SNAPSHOT_ID` with the publication's snapshot identifier. The same command
can be rerun after interruption; complete unchanged input reuses its publication.
Existing recovery and historical citation behavior remains in force.

For a new live capture, the generic CLI now accepts a durable checkpoint:

```sh
uv run ask-phil capture-sources data/sources/core-profiles-plan-v2.json \
  artifacts/new-core-profiles.json.gz \
  --checkpoint-dir artifacts/new-core-capture
```

Rerun that command after a source/transport failure. Successful sources are
reused with their original check dates. One process owns a checkpoint at a time;
a changed plan, mismatched request or corrupt payload is rejected. Choose a new
checkpoint for intentionally newer captures. The final output must be a fresh
path. Bounds remain 20 sources, 5 MB per source, 20 MB total, no automatic retries
and a 30-second network-operation timeout. Cached and new bytes share that total.
This timeout is not a whole-batch deadline. A new Wikipedia revision requires a
new scope review before publication. A future character uses the same catalogue,
capture and import contracts, without a family-specific implementation.

The source access/attribution policy in [the source inventory](../../../data/sources/README.md)
continues to apply: Wikipedia contributors, CC BY-SA 4.0, retained revision links
and attribution. Wikimedia terms and User-Agent policy were rechecked on
17 October 2026; access remained serial and bounded.

## Coverage and source review

[The runtime inventory](coverage-inventory.json) records source revisions, check
times, hashes, identity resolution, primary/mention coverage, sections and retained
character counts. [The per-character review](coverage-review.json) adds concrete
known gaps and inspected overlaps for all 20 core profiles and supporting Den.
Angie Watts, Charlie Slater, Mick Carter and other supporting characters also
remain in the captured narrative; they do not enlarge the core roster.

Two exact duplicate paragraph groups occur across Kat/Alfie production sections;
neither is admitted. Agreement on Phil/Grant's arrival does not establish source
independence. The review also records Cindy's apparent-death/later-survival
accounts and Denise's earlier unknown-father/later-discovery wording. These
require chronological context, not automatic precedence by source date. Several
biographies discuss newer developments outside their admitted Storylines section.
A `present` heading or recent fetch is insufficient to establish current coverage.

## Reviewed questions and measurements

[Reference v2](../../../data/references/core-profiles-v2.json) fixes 25 questions
before model execution: one per core profile, an additional Janine regression, two cross-profile cases and two
missing-identifier cases. Literal expectations and sufficient passage IDs come
from source inspection, independently of generated answers. Shared passages and
story events remain together in 21 groups. All are exposed development cases;
calibration and held-out splits are empty. Human review and independent canon
corroboration are not claimed.

The recorder uses the existing scorers, real local embeddings, PostgreSQL/pgvector
and the actual uncached API/CLI. Run component measurement after publishing the
exact referenced snapshot:

```sh
uv run python scripts/evaluate_text_corpus.py retrieval \
  --references data/references/core-profiles-v2.json \
  --output artifacts/core-retrieval.json
```

For live answers, start the API with `ASK_PHIL_MODELS=config/openrouter-sol.json`
and the existing private key/shared ledger setup, then run:

```sh
uv run python scripts/evaluate_text_corpus.py capture \
  --references data/references/core-profiles-v2.json \
  --api-url http://127.0.0.1:8007 --output artifacts/core-answers.json
```

Set `ASK_PHIL_MODELS=config/openrouter-sol.json` in the recorder's shell too.
The API can be started with `uv run uvicorn ask_phil.api:create_app --factory
--host 127.0.0.1 --port 8007`, using the configured `DATABASE_URL`, model profile
and `MLFLOW_TRACKING_URI`. Keep the original shared trial ledger in the repository
working directory. To score separately authored, hash-bound reviews:

```sh
uv run python scripts/evaluate_text_corpus.py score \
  --references data/references/core-profiles-v2.json \
  --capture artifacts/core-answers.json --reviews artifacts/core-reviews.json \
  --output artifacts/core-quality.json
```

The recorder invokes `ask-phil ask` against the actual HTTP API for every case,
retaining private read receipts only in ignored `artifacts/`. Published records
contain responses, citations, retrieval/context, usage, trace IDs and hashes.
The initial limit is 30 calls across this ticket and at most $1 additional
inference credits; the non-resetting $5 provider cap and shared ledger remain.
No automatic retry, new allowance, model fallback, fusion or caching is enabled.
Separate reviewed results assess actual claims and citations; selected-span
retrieval labels are not exhaustive relevance annotation or per-answer confidence.

## Development observations

Initial generic-name URLs for Grant and Bobby returned disambiguation pages.
Inspection caught their missing character infobox/narrative; the retained final
batch uses the disambiguated character URLs. No model was asked about those pages.

The initial import repeatedly reloaded the embedding model. The retained
[timing probe](embedding-residency.json) uses the same passage/model and shows
the reload cost. Local embeddings now retain the small model for five idle
minutes, then unload. The first worker was deliberately interrupted; the next
refresh marks it interrupted and rebuilds its incomplete index before publication.
Embedding identity, prefixes, dimensions and source/context limits remain the same.
The probe is an exposed timing observation, not a general performance benchmark.

The first software run passed 145 tests. Independent review identified and fixed
the Cindy daughter/mother alias collision and missing MLflow scorer linkage.
The corrected v2 corpus keeps every original capture byte/check date; its catalogue
withholds the ambiguous maternal alias, producing a new immutable publication.
[The correction record](corpus-correction.json) reproduces the old batch from the
v2 captures plus retained v1 plan, preserving lineage without a duplicate binary.
The added Janine case shares its existing development group; the original
retrieval/context failure remains in both baseline and final matrices.

The first actual serving pilot answered Phil correctly at $0.004036, with a
95.87-second application elapsed time. Inspection exposed repeated serialization
of the entire snapshot for each passage during index validation. Preparation and
validation now compute one local fingerprint per operation, retaining the same
artifact checks and hashes. The first pilot and review remain as before-review
evidence. Final software, live answer quality and publication are recorded below.

## Final results

The [final 149-test run](software-tests.xml) passed with zero failures, errors or
skips in 342.29 seconds; Ruff and strict mypy (41 files) pass. The existing upstream
Starlette/httpx test-client deprecation is the only warning. [Validation](validation.json)
binds the software result to exact code, test, script, dependency, corpus and
reference hashes and pinned PostgreSQL/pgvector and Ollama images.

[The corrected lifecycle](lifecycle-final.json) records publication generation 2,
unchanged raw captures and the preserved generation-1 pilot response after refresh
and API restart. The runtime source inventory equals the actual CLI/API report.
The 20-profile import and 25 real CLI requests used the shared pipeline throughout.

[The live matrix](serving-matrix.json), [independent source/answer labels](answer-reviews.json)
and [separate quality dimensions](answer-quality.json) establish sourced success
for **20/20 core profiles**. The matrix answers 22 questions and abstains on three:
two missing identifiers and the original Janine question whose evidence was lost.
The additional Janine therapy question succeeds. All 26 actual factual assertions
are correct, grounded and citation-supported in this exposed source-based review.
Outcome appropriateness is judged against actual supplied context; it is separate
from full-reference completeness.

[Selected-passage retrieval](retrieval-final.json) hits the labelled evidence at
k=3 for all 23 answerable questions, but assembled context and full required-fact
coverage pass **21/23**. Janine's original required passage and the explicit
Phil/Grant co-ownership passage are both retrieved at rank 3 and excluded by the
whole-span context budget. Cross-garage gives the correct name and supported
opening/joining facts, while its full frozen co-ownership fact remains uncovered.
These failures remain in [the regression register](regressions.json) for #24/#9;
neither the extra Janine case nor a weaker garage answer erases them.

[The summary](summary.json) records 26 actual serving calls including the retained
pilot, costing **$0.0999804** in reported inference credits. The existing shared
ledger totals $0.208899 after upward rounding, with no unsettled reservations.
Offline review uses zero answer-model calls and a separate MLflow review run with
hash-bound references, response captures, reviewed labels, metrics and artifacts.
Generation expense remains serving because every capture used the real API/CLI.
Final application elapsed times range from 3.80 to 5.90 seconds (median 4.36);
these are one exposed sequence, not complete CLI wall times or a controlled
performance comparison. The laptop answer model was not used for acceptance.

All cases remain development data in 21 groups. No human review, independent canon
corroboration, exhaustive history, held-out calibration, checked graph coverage,
fusion, caching or online-feedback acceptance is claimed. The independent review
is recorded in [the separate reports](review.md). [Published implementation
55616db](https://github.com/tomh1988-8/rag_demo/commit/55616db5ad07f686dce5d4ec96193ab73b1f0eaf) exactly matches local acceptance commit `4e34f29`
and tree `2c23a08f6128b1b5dc8096193469a36b0f4bd4d1`. The [publication receipt](publication.json)
records fetched-tree verification and closure readback with all seven criteria
checked. Publication used the GitHub connector because native Git lacks push
credentials. The next ticket is #8; it has not been started.
