# Domain Docs

This repo uses a single-context domain documentation layout.

## Before exploring, read these

- `CONTEXT.md` at the repo root.
- ADRs in `docs/adr/` that concern the area being explored.

If these files do not exist, proceed silently. Do not flag their
absence or suggest creating them upfront. The `/domain-modeling`
skill creates them lazily when terms or decisions get resolved.

## File structure

- `CONTEXT.md`: shared domain vocabulary.
- `docs/adr/`: architectural decision records.

## Use the glossary's vocabulary

When naming a domain concept in an issue, proposal, hypothesis,
or test, use the term defined in `CONTEXT.md`. Avoid synonyms
the glossary explicitly rejects.

If a concept is missing, reconsider whether it belongs to the
domain or note the gap for `/domain-modeling`.

## Flag ADR conflicts

Explicitly identify any proposal that contradicts an existing
ADR and explain why the decision merits reconsideration.
