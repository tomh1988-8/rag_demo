# Checked coverage across the core roster

Issue [#20](https://github.com/tomh1988-8/rag_demo/issues/20) extends the existing
extraction, admission and graph tools. The 22 live extraction batches and 25
public graph outcomes and text demonstration are complete. All 586 native tests,
eight Docker contracts and static checks pass. [Publication and completed tracker
closure](publication.json) have exact readback, with all seven criteria checked.

The retained 20-profile corpus has 794 narrative passages. The first coverage
version deliberately annotates selected excerpts across every profile, including
Den as a supporting identity. The other passages and out-of-scope supporting
identities remain explicit coverage gaps. This is a checked capability inventory,
not exhaustive extraction of all narrative history or canon acceptance.

## Measured results

[Coverage by profile](coverage.md) and the [machine-readable inventory](coverage.json)
record original text, selected scope, extraction scores, admitted/held records,
review notes and known gaps for every core profile. All 794 original passages
remain present; 22 exact excerpts are added to the same captured snapshot.
The 31 pre-extraction labels comprise 29 structured assertions and two text
classifications. All 32 actual candidates received source review, rather than
sampling this small expansion.

| Selected extraction family | Expected / predicted | Strict matches | Precision / recall / F1 | Resolvable / full-span grounded |
| --- | ---: | ---: | --- | ---: |
| Parentage | 10 / 10 | 6 | .600 / .600 / .600 | 8 / 5 |
| Relationship history | 7 / 7 | 4 | .571 / .571 / .571 | 5 / 0 |
| Events | 12 / 13 | 8 | .615 / .667 / .640 | 6 / 1 |

These are per-source assertion counts within fully annotated excerpts and
declared identities/incidents. The 16 shared story groups are exposed development;
repeated births and weddings are not independent observations. Themes match 1/1;
the tape classification matches 0/1 because its raw subject set is incomplete.
Neither text classification meets the conservative full-reference-span grounding
rule. See [category results and interpretation](extraction-summary.json).

Strict matching includes literal wording and conservative annotation policy.
Phil's raw “later” is present in the source; the unknown/relative mismatch is not
a hallucinated time. Cindy's “in 1993” differs literally from “1993” without
asserting a wrong year. A narrow sufficient quote may fail full-span grounding
while still supporting its claim. Malformed locators, the out-of-catalogue Laura
candidate and transfer of news-receipt timing to Dot's death remain separately
recorded failures. Original scores and frozen labels are unchanged.

The reviewed projection admits 28 structured source assertions and two text
classifications. All raw candidates remain in its audit: 31 are explicitly
superseded by reviewed canonical assertions; Laura is held outside the catalogue.
Canonicalization preserves passing originals as well as correcting failures.
Two independent reviewers corrected an inaccurate Lucy locator rationale and
the incomplete Bobby rationale; [v1 notes](raw-reviews-v1.json), the
[correction](review-corrections.json) and corrected notes remain available.

The first composition was rejected by the existing episode safeguard because
Martin and Stacey's same wedding had unknown versus relative timing in two
source accounts. The [content-bound projection review](reference-reviews.json)
keeps Martin's less-specific assertion current and explicitly retires Stacey's
valid source-specific assertion. Both full biographies support the same wedding
sequence. [Public questions v2](../../../data/references/core-graph-questions-v2.json)
records this post-extraction change before public capture; v1, all extraction
references and raw model scores remain unchanged. The [original failure](assembly-initial.log)
and [passing public regression](coherence-green.log) are retained.

All [25 actual graph outcomes](runtime.json) pass separate result-set, full typed
value and locator checks, citation resolution, exact root/tool trace readback,
admission-audit readback, session reset and application restart. The
[final-prose review](answer-quality.json) separately assesses 29 factual groups
and all 25 outcomes. Its source-based agent labels are not human canon
adjudication. Structural completeness is measured by the graph result scorer;
the prose review has no invented required-fact denominator.

The [actual text answer](text-runtime.json) retrieves `coverage-phil-tape` from
the full 816-passage index and answers both reviewed facts. Its citation and
API/CLI/trace bodies agree. [Separate text review](text-quality.json) records 2/2
source-supported claims and 2/2 required facts. The [sealed publication](text-publication.json)
has exactly the same source and three graph fingerprints as the graph run;
the unclassified revelation stays outside typed graph adjacency.

Extraction reports **$0.232992** across 22 paid calls; the single text answer
reports **$0.005031**. Total incremental reported inference is **$0.238023**.
The shared ledger is **$0.911656**, with zero unsettled reservations, below its
original non-resetting $5 cap. No paid extraction or answer was repeated.
The local ledger's upward rounding adds $0.000006 over the sum of these reported
charges; it is conservative accounting rather than additional observed usage.
Reviews made no provider calls. The text execution's two model operations count
the local query embedding and one paid answer; they are not two billed answers.

The first external-call approval review could not classify the outbound source
text. A [zero-network payload inspection](outbound-manifest.json) established
that every extraction request contains public Wikipedia excerpts, public
character identities, instructions and schemas. The same requested action then
passed automatic approval. There is no remaining extraction-approval blocker.
The environment interruption and the later coherence repair retain partial test
logs; final validation uses the completed source revision. All eight final
Docker public-boundary/scorer contracts pass in [the retained log](docker-tests.log).

## Final software validation

The workflow and public captures use `eec7033`; extraction captures use `9f60cea`.
The application source fingerprint is identical across those revisions. The
later `416ef2f` changes only an existing test's synchronization, with no
application, prompt, source or model-setting change requiring paid recapture.

The first complete native run retained 585 passes and one scheduling-sensitive
test failure. Its [actual original trace](network-failure-analysis.json) confirms
the application cancelled before any model operation, with no tool steps or
citations. The test's fixed 0.8-second API timeout had not established in-flight
provider work. Its repair waits for the real provider handler, then cancels the
real client request while preserving connection-close and cancelled-trace
assertions. Both original isolated parameters and both repaired parameters pass.
Both independent review axes confirmed the stronger test contract.

The final full suite passed **586 tests** in two isolated processes: 320 and
266 passes, with zero failures, errors or skipped cases. The
[retained manifest](suite-partitions.json) and [combined result](software-test-result.json)
verify that every original node identity ran exactly once across the final
reports. Separate database/Prefect state kept the selections isolated. Strict
mypy passes across 140 files, as do Ruff/formatting; all 243 frozen software
inputs match. The initial failure, focused checks and both final reports remain
available. No live provider work was repeated by these software checks.

## Reusable process

1. Read the [review guidance](../issue-15/review-guidance.md). Select exact captured
   narrative spans; name the identity and claim-family scope. Keep original
   source records, older corrections and observed failures. Complete the selected
   reference annotations before evaluating a batch. Record missing identities and
   unassessed history; never count them as false claims or recall misses.
2. Version the [annotations](../../../data/references/core-graph-v1.json), including
   exact quotes, typed reference claims, reviewer notes and shared story groups.
   Current labels are source-based agent reviews, not human adjudication. All are
   non-synthetic exposed development material, without independent corroboration.
   Shared births, marriages and the tape revelation stay grouped across profiles.
3. Reconstruct the full corpus plus citable excerpts, then run bounded batches:

   ```bash
   .venv/bin/python scripts/prepare_coverage.py \
     --annotations data/references/core-graph-v1.json \
     --output data/coverage/core-v1 --snapshot artifacts/issue-20-snapshot.json
   .venv/bin/python scripts/run_coverage.py --plan data/coverage/core-v1/plan.json \
     --output docs/implementation/issue-20/extraction --max-batches 1
   ```

   Repeat the second command to continue. Completed, failed and interrupted
   attempts are never automatically replayed. A file lock excludes concurrent
   runners. Resume requires the same code, model and frozen inputs. An interrupted
   attempt needs inspection of its raw receipt, trace and shared budget reservation;
   creating another output directory is not an approved retry procedure.

4. Audit each candidate against the retained quote and catalogue. The current
   expansion reviews every candidate because the sample is small and prior pilots
   exposed locator and timing failures. For larger expansions follow the guidance's
   risk-based review and whole-group sampling rule; record selection and denominators.
   Reviews bind the original claim fingerprint. Retain raw outputs unchanged;
   source-supported replacements use distinct IDs and explicit correction links.
5. Assemble reviewed graph inputs, inspect the per-profile report and exercise
   the frozen [public questions](../../../data/references/core-graph-questions-v2.json):

   ```bash
   .venv/bin/python scripts/assemble_coverage.py \
     --snapshot artifacts/issue-20-snapshot.json --plan data/coverage/core-v1/plan.json \
     --captures docs/implementation/issue-20/extraction \
     --decisions docs/implementation/issue-20/raw-reviews.json \
     --reference-reviews docs/implementation/issue-20/reference-reviews.json \
     --output docs/implementation/issue-20/graph
   .venv/bin/python scripts/report_coverage.py \
     --snapshot artifacts/issue-20-snapshot.json --plan data/coverage/core-v1/plan.json \
     --captures docs/implementation/issue-20/extraction \
     --graph docs/implementation/issue-20/graph \
     --output docs/implementation/issue-20/coverage.json
   .venv/bin/python scripts/record_coverage.py --database-url "$ASK_PHIL_TEST_DATABASE_URL" \
     --snapshot artifacts/issue-20-snapshot.json \
     --claims docs/implementation/issue-20/graph/claims.json \
     --reviews docs/implementation/issue-20/graph/reviews.json \
     --cases data/references/core-graph-questions-v2.json \
     --output docs/implementation/issue-20/runtime.json
   ```

   The final command uses disposable databases, actual HTTP/CLI/session requests,
   citation resolution, exact MLflow readback and application restart. It installs
   all three projections against one source snapshot. Typed graph result checks
   are separate from final prose value and support review. Graph calls make no
   inference requests. Themes and unclassified facts remain available to text
   retrieval without creating graph links.

The original non-resetting $5 trial ledger starts this issue at **$0.673627** with
zero unsettled reservations. Extraction uses the existing pinned low-reasoning
profile, one model attempt per batch and the same provider/local budget controls.
The first version has 22 batches; it adds no retry allowance or separate ledger.
Original raw extraction failures, human/judge disagreements and release gates
from earlier tickets remain unchanged.
