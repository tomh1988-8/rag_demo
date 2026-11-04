# Reviewed explanations, retained cohorts and source evidence

The user requested implementation of all three candidates in the
4 November architecture report, using TDD, independent code review and a commit
on the current branch. The starting revision and review fixed point is
`70c3d2c308c7e09b1c5e4afab9ba62ee04b2dcf6` on `main`.
The originating report is `/tmp/architecture-review-20261104-121736-583137.html`.

## Accepted scope

1. Deepen reviewed Claim explanations. Concentrate complete corrected/disputed
   evidence, reply/context limits and safe outcomes in the existing explanation
   module. Conventional text and investigation use the same guarantee; retained
   text records describe the actual final context. Retrieval strategy and
   investigation coverage remain route decisions.
2. Deepen retained cohort reporting. Load retained answers and feedback revisions
   once for a report, and apply cohort membership, cutoff and expiry consistently
   to feedback, assessment and backlog views. Preserve public pagination,
   denominators, backend eligibility, unknown expense and report retention.
3. Unify source evidence resolution. Inspection, context scoring and regression
   promotion share exact original-passage and admitted-sentence resolution.
   Promotion accepts source-checked sentence evidence from the original snapshot;
   independent expected facts, immutable review, lineage and split controls apply.

ADRs 0003–0007 remain in force. No new domain terms or factual interpretations
are introduced. Preserve existing data, paid-inference accounting, historical
evidence and the user's pre-existing workspace changes. No paid inference,
tracker mutation or remote publication is part of this task.

## Test seams and implementation sequence

The already confirmed seams in [the testing strategy](../../design/testing-and-evaluation.md)
cover these changes: conversation answers/retained traces, bounded investigation,
text retrieval/source citation resolution and evaluation reporting/promotion.
Use real disposable PostgreSQL/pgvector and local MLflow, with existing controlled
external model adapters. Test observable responses, reports and checked promotion
artifacts, rather than private methods or internal collaborator call order.

Work one regression at a time: reproduce the long reviewed-explanation failure,
deepen its shared admission, then exercise context/qualification retention;
characterize large and concurrent retained cohorts before consolidating report
reads; reproduce expanded-evidence promotion before sharing source resolution.
Run focused files and strict typechecking during implementation, both independent
review axes against the starting revision, then the full suite once at the end.

## Implementation

`review_notes.prepare_text_review` now admits a complete ready-to-cite reply,
including source classifications, wording, citation limits and serialized context
size. An explanation that cannot fit returns an evidence-free bounded outcome.
Conventional text prepares it before retaining its selection, so progress and the
final text record agree. Investigation uses the same admission and reply instead
of its separate wording-length gate; its tool outcomes remain inspectable.

`retained_reporting.RetainedReports` owns reporting reads and assembly. It loads
the eligible interactions and all cutoff-eligible feedback revisions in two bulk
queries, then reads assessment/triage/expense data in the same PostgreSQL
repeatable-read transaction. Online reporting obtains every review item directly;
the feedback interface preserves its 100-item pagination and full denominators.
The same captured interactions determine backend eligibility, pending work,
serving expense and report expiry. Cumulative judge expense keeps its separate
global scope. The evaluation configuration fingerprints the new implementation.

Regression promotion now calls the same captured-span resolver as inspection and
context scoring. Exact text, fingerprint and source revision checks still apply
before independently documented source checks, split checks and artifact writes.
No generic storage abstraction or additional model call is introduced.

## Development validation

- [Reviewed-reply failures](review-reply-red.xml.gz): conventional text raised
  `string_too_long`; investigation returned rejected evidence as final context.
  [Six focused checks](review-reply-green.xml) pass after shared admission.
- [The affected answer/context files](review-focused.xml): **60 passing cases**,
  zero failures, errors or skips.
- [Concurrent cohort failure](cohort-read-red.xml.gz): a report mixed one retained
  feedback interaction with zero triaged revisions after concurrent expiry.
  [The passing regression](cohort-read-green.xml) retains one coherent read.
- [Expanded-evidence promotion failure](sentence-promotion-red.xml.gz) and
  [passing regression](sentence-promotion-green.xml): an actual served sentence
  citation can become a checked regression with original response/source lineage.
- [Final feedback/report/promotion checks](evidence-report-focused.xml):
  **32 passing cases**, including 102 delivered interactions, review pagination
  beyond 100 items, backend eligibility, tampering/wrong-revision/wrong-snapshot
  rejection and held-out overlap rejection.

The [earlier reporting run](report-focused.xml.gz) passed 32 cases and exposed one
test-setup error: the foreign-backend fixture used wall time after the fixed
feedback cutoff. Giving it the shared fixture clock makes the intended 102-item
cohort explicit; both reporting cases pass in the final focused run. The initial
long-reply test also used an unsupported 8,000-byte setting; correcting it to
4,000 bytes exposed the actual construction/retention failures recorded above.

Strict mypy passes **174 files**; Ruff, formatting and diff whitespace checks
pass. The complete public OpenAPI is identical to the starting revision:
**28 paths and 104 schemas**. All **149 protected existing inputs**, including
existing data and the user's pre-existing work, match the starting hashes.
These are controlled-model software checks, not new factual-quality acceptance.

Independent review and the final full-suite result will be recorded below.
