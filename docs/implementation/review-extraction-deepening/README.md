# Claim review explanation and extraction deepening

The user selected both candidates from the 27 October 2026 architecture review
and explicitly approved pushing the completed work to GitHub. The starting
revision is `1ff6207264669fe2a733fdcdf99bcf9e225491c4` on `main`; it is also the
fixed point for the final independent code review.

## Accepted scope

Concentrate Claim review explanation preparation: connected corrections and
competing accounts, complete evidence, deterministic wording, source
qualifications and route-specific context constraints. Text answers retain their
three-passage cap and formatted-byte accounting; graph answers retain complete
graph evidence, their byte accounting and recorded stop outcomes. Preserve
correction history, retained Claims, citations, publication identities and
legacy snapshot behavior.

Concentrate structured Claim extraction setup: each extraction kind owns its
prompt, provider/output schema, material preparation, parsing and typed candidate
construction. Callers must no longer configure the same schema separately.
Preserve distinct domain prompts, outbound prompt behavior, stored formats and
fingerprints, raw output, scoring, accounting and the existing retained-run
lifecycle. Extraction does not admit candidates or change model-quality results.

This does not implement the next product ticket (#16) or change source/reference
inputs. Preserve the user's pre-existing workspace changes, credentials and the
shared spending ledger. No paid model calls are needed.

## Test seams

The user-confirmed seams in [the testing strategy](../../design/testing-and-evaluation.md)
already cover Claim extraction, text retrieval and typed graph tools, bounded
answers, and conversation/CLI behavior. Use those interfaces to characterize
the refactor. Keep real disposable PostgreSQL databases and local MLflow; the
existing controlled HTTP transport substitutes for the external model provider.
Do not mock internal collaborators or manufacture changed product behavior to
make a behavior-preserving refactor fail a test.

Run affected test files and strict typechecking during implementation. After
the two independent review axes and their repairs, run the full suite once,
then commit, push and verify the published tree against the local commit.

## Implementation

`review_notes` owns notice derivation, connected-group completion, source passage
selection, wording and route-specific sizing. Its prepared explanation keeps the
notices, passages, source qualification and rendered text together. Retrieval
asks for all notices connected to its evidence; text and graph answering consume
complete preparations rather than coordinating the helper sequence. Persistence
and inspection stay in `knowledge_review`, including its existing read import.

`structured_extraction.ClaimExtractor` binds each kind's output schema, prompt and
batch type in one declaration. It prepares the captured material, invokes the
existing provider adapter with that same schema, validates the result and builds
typed candidates. The retained run selects that declaration and reads its
fingerprints; it does not repeat the schema/prompt choice. Existing typed
extraction functions and `ParentageLLM`/`ClaimLLM` imports remain available for
pilot compatibility. Schema selection is per invocation, so the adapter's legacy
standalone default remains intact.

The parentage and relationship prompts retain their existing prompt-side schema
copy. The event prompt retains its omission of that copy. Removing further copies
would change model inputs and needs separate evaluation.

## Verification in progress

The two existing review-answer regressions passed before restructuring after
extending the context-limit case to both routes. The affected review and refresh
files then passed 13 checks. The relationship extraction case first failed when
an unconfigured adapter sent parentage schema, then passed with both default and
legacy explicitly configured adapters. The extraction files passed all 16 checks,
including immutable evidence, failed tracing, interruption and accounting.

[Compatibility captures](compatibility.json) compare archived starting source
with the refactor using controlled provider responses for parentage, relationship,
Crime and life-event extraction. All four outbound requests match exactly;
normalized raw output, batches, scores, hashes, counters and accounting match,
with each saved result checked against its actual MLflow trace. Per-run IDs and
timing are excluded from behavioral equality. All 24 HTTP paths and 76 public
records have identical schemas. These are software compatibility checks, not new
model-quality or independent canon results.
