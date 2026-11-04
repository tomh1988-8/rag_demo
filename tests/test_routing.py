"""Public capability eligibility and evidence-based escalation rules."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ask_phil.connection_graph import ConnectionQuery
from ask_phil.event_graph import EventQuery
from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionPolicies
from ask_phil.family_graph import FamilyQuery
from ask_phil.identity import IdentityCatalogue
from ask_phil.relationship_graph import RelationshipQuery
from ask_phil.routing import CoveredEvent, GraphCoverage, RoutingPolicy, RoutingRules


def test_biological_routing_requires_admitted_directional_coverage() -> None:
    reference = json.loads(Path("data/references/parentage-v1.json").read_bytes())
    catalogue = IdentityCatalogue.model_validate(reference["catalogue"])
    rules = RoutingRules(
        catalogue,
        GraphCoverage(family_edges=(("phil-mitchell", "ben-mitchell"),)),
    )
    eligible = rules.eligibility("Who are Ben Mitchell's biological parents?")
    assert eligible.eligible
    assert eligible.query == FamilyQuery(
        character_id="ben-mitchell", direction="ancestors", max_depth=1
    )
    missing = rules.eligibility("Who are Phil Mitchell's biological parents?")
    assert not missing.eligible
    assert missing.reason == "no_admitted_coverage"


def test_relationship_history_requires_the_requested_pair_and_complete_question() -> None:
    reference = json.loads(Path("data/references/parentage-v1.json").read_bytes())
    catalogue = IdentityCatalogue.model_validate(reference["catalogue"])
    rules = RoutingRules(
        catalogue,
        GraphCoverage(relationship_pairs=(("phil-mitchell", "kathy-beale"),)),
    )
    eligible = rules.eligibility(
        "Explain the relationship history between Phil Mitchell and Kathy Beale."
    )
    assert eligible.eligible
    assert eligible.query == RelationshipQuery(
        kind="relationship_history", character_id="phil-mitchell", partner_id="kathy-beale"
    )
    assert not rules.eligibility(
        "Explain the relationship history between Phil Mitchell and Sharon Watts."
    ).eligible
    assert not rules.eligibility(
        "Explain the relationship history between Phil Mitchell and Kathy Beale and why it ended."
    ).eligible


def test_events_and_connections_use_supported_roles_without_thematic_graphs() -> None:
    reference = json.loads(Path("data/references/parentage-v1.json").read_bytes())
    catalogue = IdentityCatalogue.model_validate(reference["catalogue"])
    rules = RoutingRules(
        catalogue,
        GraphCoverage(
            family_edges=(("phil-mitchell", "ben-mitchell"),),
            events=(
                CoveredEvent(
                    kind="crime_history", event_id="crash", character_ids=("phil-mitchell",)
                ),
            ),
        ),
    )
    event = rules.eligibility("Show Phil Mitchell's crime and justice history.")
    assert event.eligible
    assert event.query == EventQuery(kind="crime_history", character_id="phil-mitchell")
    connection = rules.eligibility("How are Ben Mitchell and Phil Mitchell connected?")
    assert connection.eligible
    assert connection.query == ConnectionQuery(
        kind="connection", character_id="ben-mitchell", target_id="phil-mitchell"
    )
    assert not rules.eligibility("Show Phil Mitchell's pregnancy and death history.").eligible
    assert not rules.eligibility(
        "How is Phil Mitchell connected to the theme of betrayal?"
    ).eligible
    theme = rules.eligibility(
        "Show themes", query=EventQuery(kind="theme", character_id="phil-mitchell")
    )
    assert not theme.eligible
    assert theme.reason == "unsupported_graph_family"


@pytest.mark.parametrize(
    "models,tools,reason",
    [
        (6, 2, "investigate_evidence_gap"),
        (4, 2, "no_escalation_budget"),
        (6, 1, "no_escalation_budget"),
    ],
)
def test_escalation_uses_remaining_authority_without_replenishing_it(
    models: int,
    tools: int,
    reason: str,
) -> None:
    budget = ExecutionBudget(ExecutionLimits(model_calls=models, tool_calls=tools))
    budget.model_call(Decimal(0))
    budget.model_call(Decimal(0))
    budget.tool_call("text_retrieval")
    before = budget.record()
    assert (
        RoutingPolicy().escalation(
            status="partial",
            reviewed=False,
            additional_evidence=True,
            published=True,
            budget=budget,
        )
        == reason
    )
    assert budget.record() == before


def test_automatic_routing_honors_existing_explicit_serving_limits() -> None:
    denied = ExecutionLimits(model_calls=0, tool_calls=0)
    policies = ExecutionPolicies(serving=denied)
    assert policies.for_request("auto") == denied
    explicit = ExecutionPolicies(serving=denied, automatic_serving=ExecutionLimits(model_calls=4))
    assert explicit.for_request("auto").model_calls == 4
