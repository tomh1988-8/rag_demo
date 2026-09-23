# Candidate demonstration and evaluation cases

These are candidate scenarios within the agreed design, not a labelled evaluation dataset. Expected claims, source revisions, and uncertainties must be reviewed before these become gold cases. More than one retrieval route may produce a valid answer; actual execution and evidence must be recorded.

These examples are candidate seeds for the [testing and evaluation strategy](testing-and-evaluation.md), which also covers unit/integration tests, component datasets, held-out end-to-end comparisons, and calibrated LLM judges. They do not represent the full suite.

| Case | Candidate question | What it exercises | Starting sources |
| --- | --- | --- | --- |
| Direct evidence | When did Phil and Sharon marry, according to the captured account? | Direct passage support, citation correctness, and honest date precision. | [Phil Mitchell](https://en.wikipedia.org/wiki/Phil_Mitchell#Storylines) |
| Biological relationship | How are Ian Beale and Ben Mitchell related biologically? Show the supporting parent links. | Biological-only graph paths, derived relationships, and evidence for each parentage claim. | [Ian Beale](https://en.wikipedia.org/wiki/Ian_Beale), [Kathy Beale](https://en.wikipedia.org/wiki/Kathy_Beale), [Ben Mitchell](https://en.wikipedia.org/wiki/Ben_Mitchell_(EastEnders)) |
| Relationship history | Trace Kat and Alfie's marriages and separations in the main series, distinguishing divorce, reconciliation, and remarriage. | Repeated relationships, chronology, distinctions between separation and divorce, and main-series scope. | [Kat Slater](https://en.wikipedia.org/wiki/Kat_Slater), [Alfie Moon](https://en.wikipedia.org/wiki/Alfie_Moon) |
| Investigation | How did Lucy's death lead to Max's conviction and the exposure of Bobby's involvement? Explain Ian's and Phil's roles. | Evidence across characters, actual conduct versus legal outcomes, and bounded investigation. | [Ian Beale](https://en.wikipedia.org/wiki/Ian_Beale#Storylines), [Max Branning](https://en.wikipedia.org/wiki/Max_Branning#Storylines), [Phil Mitchell](https://en.wikipedia.org/wiki/Phil_Mitchell#Storylines) |
| False premise | Did Phil kill Jay's father in the car-lot fire, as he claimed? | Context around a character's statement, source-supported correction of a premise, and supporting characters outside the core roster. | [Phil Mitchell](https://en.wikipedia.org/wiki/Phil_Mitchell#Storylines) |
| Missing precision | What exact in-universe calendar date did Kat receive her suspended sentence for perjury? | Preserving uncertainty and distinguishing event dates from broadcast dates. | [Kat Slater](https://en.wikipedia.org/wiki/Kat_Slater#Storylines) |

## Review cautions

- Validate each question's premise against the captured main-series corpus before labelling expected answers.
- The inspected Ian and Max source narratives use different wording for Bobby's charge; review or attribute those accounts rather than silently normalising them to one legal label.
- The missing-precision case is conditional: an exact date may become available in another captured passage. Abstention is appropriate only when the frozen corpus does not support the requested precision.
- A retrieved passage can answer a relationship or investigative question directly. Do not require an unnecessarily expensive route merely to match a label.
- Confirm each derived biological relationship from its underlying parentage evidence; other relationship types must not substitute for biological ancestry.
- Score final persona answers for preservation of facts, qualifications, and seriousness of harm, separately from voice quality.
