# Research: a reusable agent development checklist

Reviewed: 23 September 2026. Status: research and recommendation for discussion; the existing project tickets have not been restructured.

The intended checklist is for developing LLM applications, workflows, and agents in different projects. Humans or coding agents can follow it. It should be independent of programming language, model provider, framework, and deployment platform.

## How popularity was assessed

There is no comparable public usage ranking across book appendices, research rubrics, conference requirements, and engineering playbooks. The shortlist uses observable reach, formal adoption, and primary-source engineering provenance. These signals are recorded separately: institutional authorship establishes provenance, while repository stars indicate attention to a repository. Neither measures use of an individual checklist.

Approximate repository counts below are those displayed by GitHub when accessed for this review; they can change and may reflect cached pages. This is a shortlist of established references, not a measured global ranking.

## ML references worth using

| Reference | Reach or adoption evidence | Useful contribution | Adaptation needed for agents |
| --- | --- | --- | --- |
| [Aurélien Géron's ML Project Checklist](https://github.com/ageron/handson-ml3/blob/main/ml-project-checklist.md) | The author's third-edition [book repository](https://github.com/ageron/handson-ml3) displays about 14.2k stars and 5.3k forks; these belong to the whole repository. | An accessible lifecycle from problem framing and data inspection to experiments and ongoing operation. | Replace assumptions about training models with choices about prompts, context, tools, and orchestration. |
| [Google's ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/) | Published at IEEE Big Data in 2017 and grounded in Google's production experience; no comparative adoption count established here. | A 28-check readiness rubric covering data, models, infrastructure, and monitoring. | Its [paper](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf) explicitly leaves ordinary software engineering practices outside its main scope; include those as well as agent behavior. |
| Microsoft's [ML Fundamentals](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-fundamentals-checklist/) and [Model Production Checklist](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-model-checklist/) | Official engineering playbook; its [repository](https://github.com/microsoft/code-with-engineering-playbook) displays about 2.7k stars, for the whole playbook. | Connects data feasibility, baselines, tested evaluation code, and operational acceptance. | Scope production requirements to the intended release and add tool/state behavior. |
| [NeurIPS Paper Checklist](https://neurips.cc/public/guides/PaperChecklist) | The official submission guidance requires including the checklist. This is direct evidence of formal adoption. | Reproducibility, justified claims, limitations, and evidence supporting answers to checklist questions. | Use the evidence discipline without inheriting a research-paper submission process. |
| [CheckList](https://aclanthology.org/2020.acl-main.442/) | ACL 2020 research with an [implementation repository](https://github.com/marcotcr/checklist) displaying about 2.0k stars. | Test capabilities through simple cases, changes that should preserve behavior, and changes that should alter it predictably. | This is an NLP behavioral-testing method; it supplies part of the test strategy rather than the whole development lifecycle. |
| [DC-Check](https://www.vanderschaar-lab.com/dc-check/) | A research-backed checklist from the van der Schaar Lab; no comparative popularity claim established. | Examines data decisions across development, testing, and operation. | Extend its lens to evidence corpora, tool responses, task distributions, and evaluation labels. |
| [AWS MLOps checklist](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/introduction.html) | Official AWS Prescriptive Guidance; no comparable usage count established. | Explicitly supports readiness reviews and generating backlog work across [nine operational areas](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/mlops-checklist-components.html). | Keep the planning method while removing AWS-specific implementation assumptions and mandatory model retraining. |

I also inspected [Sjösund's ML Project Checklist](https://github.com/sjosund/ml-project-checklist), whose repository displays 40 stars. It is a useful community synthesis, but the available evidence does not justify ranking it alongside the largest references by popularity.

## Agent-specific additions

These sources are included for direct relevance and engineering provenance; I have not established a comparative popularity ranking for them.

- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) informs the choice between a fixed workflow and an agent, tool-interface design, and bounded execution. For this proposal, the practical consequence is to record what additional autonomy achieves against a simpler working baseline.
- [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents), published 9 January 2026, supports checking both recorded execution and the actual result, building evaluation cases early, and using suitable code, model, and human graders. A completion message alone cannot establish that an external action succeeded.
- [OWASP: AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) informs authority, input, and memory boundaries. Apply its action checks to capabilities actually present.
- Anthropic's [tool-design guidance](https://www.anthropic.com/engineering/writing-tools-for-agents) and [multi-agent research-system account](https://www.anthropic.com/engineering/built-multi-agent-research-system) add concrete interface, coordination, and resource considerations for the relevant modules.
- [LlamaIndex's evaluation guidance](https://developers.llamaindex.ai/python/framework/module_guides/evaluating/) distinguishes retrieval and response evaluation. It informs a conditional RAG module without mandating LlamaIndex.
- [ExtractBench's metric definitions](https://github.com/run-llama/ExtractBench#metrics) distinguish extracted values from their source grounding. They inform an extraction module; the benchmark's enterprise-document scores do not establish performance on another corpus.

## Recommendation

Use Géron's lifecycle as an organising influence, the ML Test Score and Microsoft playbooks for engineering checks, and NeurIPS/CheckList for evidence and behavioral testing. Add agent-specific requirements where the original ML checklists assume a predictive model rather than a system using tools over several steps.

The resulting [draft checklist](../checklists/agent-development.md) is an original synthesis, not an existing industry standard. It has ten core areas and conditional modules. Each check has an ID and an expected evidence type, allowing it to become a ticket acceptance criterion and remain reusable across projects.

Use three review moments: establish the project profile and initial examples; revisit affected checks during each working slice; inspect the applicable evidence before the intended release. Operating checks continue after deployment. A small local demonstration can defer deployment-only work explicitly while still requiring sound tests and evaluations.

After agreement, fit tickets to checklist outcomes and evidence. A ticket can cover several checks, and a check can have evidence supplied by several tickets. Sections can organise the backlog while tickets continue to deliver independently demonstrable behavior. The current ticket count and boundaries are still provisional.
