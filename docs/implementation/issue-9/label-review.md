# Human label review for the support judge

These are authored counterexamples, **not EastEnders canon or generated answers**.
They calibrate only whether every factual assertion in an answer is supported by
the supplied context. They do not calibrate factual correctness, completeness,
persona, or broad narrative quality. The labels and rubric are fixed before any
judge execution. Tom approved all eight supplied labels in this session with
"continue, i approve". [The approval receipt](approval.json) retains the original
package and example hashes. The examples and labels remain unchanged; the dataset
now records their human approval. This approval covers the narrow support rubric.

Calibration context (synthetic `chairs-delivery` event):

1. Phil delivers three red chairs to the community hall on Monday.
2. Phil leaves before the meeting. The account does not identify its chairperson.

| ID | Answer | Approved support label |
| --- | --- | --- |
| chairs-supported | Phil delivers three red chairs. | Pass |
| chairs-wrong-colour | Phil delivers three blue chairs. | Fail |
| chairs-incomplete | Phil delivers chairs. | Pass (incomplete, but supported) |
| chairs-missing-input | Phil delivers three red chairs. **No context supplied.** | Unavailable |

Validation context (synthetic `library-return` event; excluded from judge tuning):

1. Ben borrows two history books from the library.
2. He returns both books on Tuesday. The account gives no fine information.

| ID | Answer | Approved support label |
| --- | --- | --- |
| books-supported | Ben returns both history books on Tuesday. | Pass |
| books-wrong-day | Ben returns the books on Friday. | Fail |
| books-invented-fine | Ben pays a ten-pound library fine. | Fail |
| books-missing-input | Ben returns the books on Tuesday. **No context supplied.** | Unavailable |

An absent reference answer does not prevent this context-only check. An absent
context does. A helpful vote or an unverified user correction cannot override any
label. Reversed evidence order and repeated/wordier answers retain these labels.
Any label correction must create a new dataset version and invalidate calibration.
