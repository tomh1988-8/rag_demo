# Independent review of issue #11

Fixed point: `7286a85f0e7306a1e2898973aea31c9248665af9`.
Reviewed implementation: `8d58624` (initial `8d867f2`, then review fixes).
The two axes ran in separate agents using the code-review skill. Source review
completed before the final full-suite run. The accepted source is unchanged.

## Standards

No remaining hard violations or actionable heuristic findings. Installation is
a maintainer operation. Answering uses typed, parameterized, bounded read-only
SQL and retains content-bound reviews, claims and evidence independently of the
projection. Tests exercise the agreed public boundaries. Frozen materials and
the final rescore match their hashes. Saved-stop behavior is correctly scoped
to operations after the snapshot is loaded; initial storage/pin failures can
return 503 without a receipt.

The initial minor duplicated-code judgment concerned repeated MLflow experiment
setup. The shared `experiment_for` helper resolves it without changing names or
artifact locations. All affected callers use it directly.

## Spec

No remaining actionable findings at `8d58624`. The initial P2 concerned global
semantic deduplication across distinct annotated source spans. Matching now
preserves input passage identity and evaluates quote resolution separately. The
counterexample first failed, then correctly reported two expected instances,
recall 0.5 and one grounded claim. The independent reviewer reproduced the final
rescore and verified raw-output, reference and scorer hashes.

Frozen labels remain unchanged. Pilot values 4/4, resolvable spans 3/4 and strict
grounding 2/4 remain distinct. API/CLI overrides, biological admission, immutable
records, SQL paths, citations and documented failures meet the ticket's slice.
Graph completeness still fails at recall 2/3 and remains a regression. Source
review and passing software do not convert that quality failure into acceptance.

Final findings: Standards 0; Spec 0. No remaining worst issue on either axis.
The final runtime replay and software report provide the subsequent execution
evidence; the preliminary capture remains retained separately.

The final evidence review independently read back all nine graph traces and the
original extraction trace: stored outputs match the saved artifacts exactly,
and every runtime/source hash matches `8d58624`. One minor page-count error in
the regression limitations was corrected from two source pages to three.
