# Reference correction after independent review

The independent Standards reviewer found a genuine omission in the original
reference's claim to annotate all relationship assertions. The Ben birth excerpt
also calls Kathy Phil's "then wife"; v1 labelled only its two parentage assertions.
The v1 matching contract keys by passage, so its marriage label on another passage
does not cover this additional source assertion. Its original recall denominator
was therefore incomplete. All ten source excerpts themselves are unchanged and
match the captured documents, offsets, metadata and revisions.

`relationships-v2.json` adds a thirteenth source assertion for that marriage.
It belongs to the existing Phil/Kathy episode. The marriage's date and status
remain unknown: Ben's March 1996 birth does not establish their wedding date or
present-day marital status. This is an extra supporting source instance, not a
second wedding. The renderer combines identical same-episode assertions while
the structured result, audit and citations retain both sources.

The original v1 reference, pre-pilot freeze, raw model output, twelve-candidate
audit, original scores and initial runtime remain unchanged. This correction was
made after the pilot in response to an independent source-based finding; the
thirteenth label was not frozen before inference. Twelve curated assertions
predate the call; the thirteenth is the documented review correction. No new paid
call was made. Source review is by agents, not human/canon adjudication.

Under the corrected reference the same raw output has precision 5/12, recall
5/13 and F1 0.4. Exact locators and strict full-excerpt grounding remain 2/12.
All twelve raw candidates remain held. The v2 combined batch retains them and
admits thirteen curated source assertions describing twelve semantic assertions.

The Spec reviewer also identified a scorer bug: separate episodes with identical
unknown values and the same supporting passage could collapse. The corrected
scorer retains episode multiplicity, matches values one-to-one while ignoring
arbitrary ID spelling, and tests missing/reordered repeated affairs. It selects
a consistent alignment by episode agreement then ordering. More than 4096
possible alignments leaves those two scores unavailable instead of inventing a
pass. This is a deterministic scorer limit, not an LLM judge or held-out result.
