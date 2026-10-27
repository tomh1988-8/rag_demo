# Life events and classification source review

Before extraction, the retained `core-profiles-v2` passages were read for this
exposed development slice. The reference preserves exact excerpt offsets,
original passage IDs, captured revisions, licences and source hashes. This is
source review by Codex, without human adjudication or independent canon checks.

Pregnancy requires the `pregnant_person` role. Peggy's pregnancy has unknown
timing; Sharon's first selected pregnancy is discovered on Christmas Day 2005;
the other selected Sharon account explicitly leaves paternity uncertain. None
of these event assertions creates parentage, an unborn character or a partner.

Death requires `deceased`. Peggy's death is supported, but the nearby 4 July 2016
date describes her funeral. Pat is a hallucination, and Phil finds the body:
neither is an actual witness to the death. Lucy's death is supported without a
date; Phil supporting Ian afterwards does not establish either as present at
the death. This slice admits only deceased participants, leaving richer death
roles to later reviewed evidence.

Peggy and Phil's abuse is labelled with the subject `domestic_abuse`. A theme
claim records character subjects, never event participants or graph adjacency.
The captured tape revelation remains an unclassified fact: the current checked
event types do not cover public revelation of an affair. Its character subjects
do not enter graph paths. No selected source supports a manosphere label.

The public boundaries are claim extraction/admission, text retrieval and typed
graph queries, conversation API/CLI, and evaluation scoring, already confirmed
in the testing strategy and explicitly approved again in this implementation.
The initial fixed point for implementation review is `54689cb`.

Expected values are frozen before the first model call. Raw candidates, source
reviews, curated serving claims and metric failures will be retained separately.
Software fixtures may supply controlled provider responses; those are not model
quality measurements. Existing sources, labels, user work and the shared $5
non-resetting provider ledger remain preserved.
