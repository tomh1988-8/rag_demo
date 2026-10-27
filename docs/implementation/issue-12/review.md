# Independent review of issue #12

Fixed point: `5faaff660572de9ceef4946ffed7cf09bf030824`, the revision at the
start of this implementation. Initial review target: `097bf7d`; fixes and final
re-review target: `0c9918c`.

Both axes ran in separate read-only agents using
`git diff 5faaff660572de9ceef4946ffed7cf09bf030824...HEAD`. User changes outside
the committed task diff were excluded. Standards considered AGENTS.md, CONTEXT.md,
ADRs 0004–0007, the confirmed testing strategy and the skill's smell baseline.
Spec used the freshly fetched issue #12 and parent specification.

## Standards

Initial findings: two, comprising one documented-standard breach and one
judgment about duplicated code.

1. The original reference's complete-annotation claim omitted Kathy's "then wife"
   marriage assertion in the Ben birth excerpt. The strategy requires sufficiently
   complete annotation before claiming recall. A separately versioned v2 reference
   adds the missing source instance for the same marriage episode with unknown
   wedding date. Original inputs, pilot and v1 reference are preserved. The
   independently recomputed corrected scores are precision 5/12, recall 5/13,
   F1 0.4. Thirteen curated assertions are admitted; twelve raw candidates are held.
2. Admission and scoring repeated the exact evidence-span predicate.
   `evidence_resolves` now supplies one shared check to both old/new admission
   paths and both scorers. Historical parentage behavior remains tested.

Final reviewer report at `0c9918c`: both findings resolved; no remaining actionable
standards finding, material source/reference error or ADR conflict. The renderer
preserves structured assertions and citations while combining equivalent
same-episode prose entries.

## Spec

Initial findings: two.

1. Keying expected claims by normalized values could collapse separate episodes
   with identical unknown timing/status and the same passage. Extracting only one
   of two affairs incorrectly scored complete recall. The scorer now retains
   multiplicity, uses one-to-one matching independent of arbitrary ID spelling,
   and aligns ambiguous instances consistently for episode/order scoring. A finite
   search cap leaves unresolved scores unavailable. The missing-affair regression
   now reports recall 0.5 and fails its missing episode pair.
2. Equal character/partner IDs duplicated the query predicate and returned every
   partner for that character. Self-pairs now fail typed validation; the regression
   protects the API/CLI query contract.

Final reviewer report at `0c9918c`: both findings resolved; no new actionable spec
defects or scope creep. The v2 source correction preserves the original reference,
freeze and pilot; its additional assertion establishes neither another wedding
nor its date. Admission recomputation matches the saved 13-admitted/12-held audit.
Unknown timing, relationship distinctions, biological ancestry isolation and all
underlying evidence remain intact.

Final findings: **Standards 0; Spec 0**. Model-quality failures remain separate
from these code/spec review results and are retained in the regression evidence.
