# Independent review

Fixed point: `1ff6207264669fe2a733fdcdf99bcf9e225491c4`.
Implementation: `b336248` (Deepen Claim review explanations and structured extraction).
Both reviewers used `git diff 1ff6207264669fe2a733fdcdf99bcf9e225491c4...HEAD`.
The originating scope is [the accepted implementation](README.md), selected by
the user from both architecture candidates. Two independent agents reviewed
Standards and Spec in parallel. Unrelated pre-existing workspace changes were
excluded.

## Standards

Hard violations: **0**. Actionable baseline smells: **0**.

The changes respect the documented domain vocabulary, ADRs 0004–0007 and the
approved test seams. Review explanation rules now concentrate in one module,
while text and graph callers retain their distinct evidence limits and stop
outcomes. Extraction setup binds schema selection, parsing and candidate
construction without changing admission or persistence responsibilities.

The remaining typed extraction functions are small compatibility delegates.
Their preservation is explicitly required by the accepted scope, so they do not
warrant a Middle Man finding.

The changed tests exercise observable answer outcomes and the actual external
provider request schema. They use real storage and controlled external responses
rather than mocks of internal collaborators. The compatibility documentation
correctly distinguishes software checks from model-quality or canon acceptance.

The reviewer inspected the committed diff and relevant standards, without
executing tests or independently verifying the recorded runtime captures.

## Spec

Zero Spec findings in `1ff6207...b336248`.

The refactor preserves connected correction groups, complete evidence, text's
three-passage cap and formatted-byte accounting, graph sizing and stop outcomes,
synthetic qualifications, citation ordering and legacy snapshot behavior. Notice
derivation moved without changing its admission or correction rules.

Extraction now selects provider schema and local parsing from the same extraction
declaration. Existing typed functions and legacy `ParentageLLM`/`ClaimLLM` imports
remain available; standalone adapter defaults remain intact. Prompt contents,
retained batch types, scoring and failure/accounting handling remain within scope.

The reviewer independently compared the four archived/current compatibility
captures: outbound requests and normalized retained records match. Public schemas
match, and the source fingerprint matches the recorded refactored capture.

No missing requirements, unrequested product behavior or incorrect implementation
was identified. No files were changed or tests run by this reviewer.

Standards: **0**, worst issue: none. Spec: **0**, worst issue: none.
Full-suite execution, publication and remote-tree verification are recorded
separately; the independent reviews do not establish those results.
