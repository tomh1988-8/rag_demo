# Issue #15: corrected and disputed knowledge

Maintainers can inspect held Claims and publish content-bound review outcomes.
Each review creates an immutable source snapshot, retains every earlier Claim and
review, rebuilds all existing graph families and the text index, and publishes
their identities together. Text and graph answers explain corrected or disputed
accounts with source citations. Review is not independent corroboration.

The starting revision is `640084cc2fc55f43abb8f44b7c68c7a3a40d6c72` on `main`.
The approved scope is [GitHub #15](https://github.com/tomh1988-8/rag_demo/issues/15)
and its [retained body](issue.json). Existing confirmed admission, retrieval,
refresh, typed graph and conversation boundaries are used for TDD.

## Maintainer contract

```sh
ask-phil claim-reviews --snapshot SNAPSHOT_ID > inspection.json
# Prepare a ReviewRequest from the inspected source/graph fingerprints and exact Claim content.
ask-phil review-claims review-request.json
ask-phil publication
ask-phil refresh-runs
```

`claim-reviews` uses `GET /v1/snapshots/{snapshot_id}/reviews`. It returns
the source fingerprint, all family audits, identities, retained source passages,
admission reasons and chronological review revisions. Existing per-family audit
and evidence endpoints remain available, including for failed candidates.
`review-claims` requires maintainer database access and the configured local
embedding model. There is no review write endpoint or answering-agent write tool.

`ReviewRequest` binds `snapshot_id`, `snapshot_sha256` and the complete `graphs`
record returned by inspection. `family_reviews`, `relationship_reviews` and
`event_reviews` contain content-bound outcomes and rationales. Optional
`new_family_claims`, `new_relationship_claims`, `new_event_claims` and
`new_context_claims` add distinct, explicitly reviewed assertions; existing IDs
cannot be overwritten. The original batch remains inspectable in its old snapshot.

Supported, unsupported, uncertain and disputed reviews retain their meaning.
An explicit superseded outcome requires supported replacement IDs in
`superseded_by`; it removes the old account from conflict checks while retaining
the raw Claim and its reasons. Domain admission still rejects invalid roles,
unsupported commission, cycles and uncertainty. Supported negations and social
parentage can replace an erroneous assertion without entering biological edges.
Review all relevant duplicate assertions and projection families explicitly.
Previously accepted retirements remain retired when their replacement is later
corrected, disputed, uncertain or unsupported. New corrections still require
supported terminal accounts; original correction links remain inspectable.

Queries pin one publication. The manifest records source, actual vector artifact,
all admitted-claim/graph derivations, review identity and generation. Once sealed,
an absent graph family cannot be silently installed later into that publication.
Failed projection or interrupted indexing retains the previous usable version;
the candidate is inspectable but cannot answer. Exact retry resumes immutable
artifacts. Recovery verifies the previous source/index/graph/review identities;
new requests reject the withdrawn version, while already-pinned work can finish.
Unchanged source refresh keeps the review; changed source inputs need new reviews.

## Answer behavior

Review explanations use deterministic wording tied to retained typed assertions.
The text route still performs real vector retrieval. If it retrieves a reviewed
dispute, it includes the whole competing group for the same parentage subject,
relationship episode, event identity or text classification. It can retrieve one
account and still expose both. Connected replacement groups are followed when a
correction changes the person, episode or event identity. The source passages and
rendered review explanation
must fit the existing context limit together; otherwise the answer abstains.
Repeated rationale is rendered once while every audit record remains intact.

Graph answers keep disputed Claims outside established connections and attach
their explanatory evidence, including when there are no admitted paths. Corrections
retain the earlier account, its replacement and the reason for change. These
bounded explanations are partial, with explicit coverage limits. Generation is
skipped for this deterministic review path and reported as such in the trace;
the ordinary text generation prompt is unchanged.

## Pilot, failures and validation

[Frozen inputs and expected outcomes](pilot-inputs-v2.json) precede their runtime execution;
the original [two-case freeze](pilot-inputs.json) remains unchanged.
The sourced case repairs the actual issue #11 Peggy locator from 104 to 105 Unicode
characters without rewriting its raw extraction or changing the supported value.
The old held Claim remains inspectable; a distinct supported replacement admits
Peggy's biological link to Phil. The second case has two explicitly synthetic
conflicting father accounts. It is not a real EastEnders source dispute.
The third deliberately authors a wrong biological Den/Sharon interpretation
against the unchanged adoption source, then corrects it to adoption at age three.
Its baseline and rollback answers intentionally reproduce the old error; they are
recovery evidence and are excluded from passing factual-answer results.

[Review and annotation guidance](review-guidance.md) records the complete pilot
audit, matching dimensions, duplicate treatment, uncertainty tolerances, reference
completeness, future targeted review and sampling. Existing extraction scores and
references are unchanged; curated correction does not improve the original score.

[The initial runtime](runtime-initial/summary.json) retains thirteen actual public
responses with exact MLflow readback, source resolution, saved-response restart,
reset and recovery. The correction works. The synthetic-dispute text explanation
exceeds the initial context budget because each account repeats its review rationale,
so that text answer abstains. The graph/CLI/session cases already explain both accounts.
This text failure remains recorded. The repair renders shared rationale once and
completes connected review groups even when retrieval finds only one member.
[Regressions](regressions.json) also retain both independent-review findings and
their public regression tests. [The final code review](review.md) has zero remaining
Standards or Spec findings. [Validation](validation.json) binds the final execution
evidence to [frozen software inputs](software-inputs.json); the
[acceptance map](acceptance-map.json) links all seven ticket criteria to their artifacts.

The [accepted runtime](runtime-accepted/summary.json) contains nineteen final public
responses at application SHA
`badf2d507c8abcf7cacb8654585026c411f4b64bba531e9513ac0f759318ab07`.
All actual MLflow outputs and saved responses match, citations resolve, and each
scenario passes API restart/readback, session reset and rollback. The projection
fault leaves the prior publication usable and returns HTTP 503 for the unpublished
candidate; exact retry publishes successfully. [Source-based quality review](answer-quality.json)
passes all twelve current corrected/disputed answers on support, grounding,
complete interpretation and attribution/coverage. Independent review confirms those
results and explicitly excludes the two deliberately wrong old-version answers.
`runtime-reviewed` and `runtime-final` retain the successful intermediate captures;
`runtime-accepted` is the final implementation's acceptance record.

The single final full suite passes **480 tests**, with zero failures, errors or
skips (1,242.67 seconds). All **26 new focused tests** passed before that run.
Strict mypy across 109 files and Ruff lint/formatting pass. All 166 frozen software,
configuration and data inputs stayed unchanged throughout validation. The 37 original
data files, 51 pre-existing workspace files, private key and budget ledger are
unchanged. No paid model calls were made; the shared ledger remains **$0.464981**
with zero unsettled reservations.

The runtime runner uses isolated PostgreSQL databases, the pinned local embedding
model, real HTTP/CLI/session requests and MLflow. Its serving spend limit is zero;
no paid answer generation or new extraction is needed. Software correctness,
deterministic explanation quality and historical model extraction quality are
separate results. Broad graph coverage, automatic routing, representative quality
and full release gates remain later tickets.

```sh
ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres \
  .venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
ASK_PHIL_MODELS=config/openrouter-sol.json \
  .venv/bin/python scripts/record_review_acceptance.py \
  --database-url postgresql://USER:PASSWORD@HOST:PORT/postgres \
  --output artifacts/review-acceptance-new
```

The acceptance runner refuses to overwrite evidence. Its model configuration
identifies the available embedding client; the deterministic review answers make
no generation call. Preserve the shared non-resetting $5 ledger and original
source/reference inputs when reproducing this work.
