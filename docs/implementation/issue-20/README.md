# Checked coverage across the core roster

Issue [#20](https://github.com/tomh1988-8/rag_demo/issues/20) extends the existing
extraction, admission and graph tools. Validation is in progress.

The retained 20-profile corpus has 794 narrative passages. The first coverage
version deliberately annotates selected excerpts across every profile, including
Den as a supporting identity. The other passages and out-of-scope supporting
identities remain explicit coverage gaps. This is a checked capability inventory,
not exhaustive extraction of all narrative history or canon acceptance.

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
   the frozen [public questions](../../../data/references/core-graph-questions-v1.json):

   ```bash
   .venv/bin/python scripts/assemble_coverage.py \
     --snapshot artifacts/issue-20-snapshot.json --plan data/coverage/core-v1/plan.json \
     --captures docs/implementation/issue-20/extraction \
     --decisions docs/implementation/issue-20/raw-reviews.json \
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
     --cases data/references/core-graph-questions-v1.json \
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
