# Versioned correction after independent source review

The independent Spec reviewer checked all seventeen scoped assertions and all six
excerpt origins. Five v1 labels omitted explicit relative timing. The unmodified
v1 reference, pre-pilot freeze, model request/response, pilot score and initial
runtime remain historical evidence. This correction follows the pilot; the
corrected labels are not described as pre-pilot or held-out.

| Assertion | Corrected relative story timing |
| --- | --- |
| Max's arrest for Lucy's murder | when Lucy's blood is found on his shoe |
| Max's charge for Lucy's murder | when Lucy's blood is found on his shoe |
| Max's accusation of Bobby | As he is being arrested |
| Max's later imprisonment | later |
| Phil's release following confession/custody | later |

The arrest and charge quotes are expanded to include the blood-discovery clause.
All changes remain within the same retained source passages. Identities, roles,
incident membership and the seventeen-assertion scope are unchanged. Other dates
remain unknown where the source supplies no timing anchor. A phrase naming the
trial or acquittal itself is not its own calendar date. The bail interval does not
supply an unambiguous release date. No chronology is inferred from listing order.

`data/references/crime-justice-v2.json`, `reference-claims-v2.json` and
`reference-reviews-v2.json` retain the correction. The combined v2 batch retains
all four raw candidates unchanged and adds seventeen corrected reviewed assertions.
Raw review decisions remain unchanged: two admitted and two held.

`reference-correction-v2.json` hashes the corrected reference and original pilot
and rescoring uses exactly that unchanged raw model output. Precision remains
3/4, recall 3/17 and F1 2/7; all dimensional and per-event-type results are retained.
No new model calls or charges were made. Final API tests protect relative timing
and final runtime evidence will exercise the v2 serving batch.
