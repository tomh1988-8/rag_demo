import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from starlette.types import ASGIApp

from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventClaim, EventReview, admit_events


def life_reference() -> tuple[SourceSnapshot, EventBatch, tuple[EventReview, ...]]:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/life-events-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/life-events-v1.json").read_bytes())
    batch = EventBatch.model_validate(
        {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "catalogue": reference["catalogue"],
            "extractor": "source-reviewed-reference",
            "claims": reference["expected_claims"],
            "context_claims": reference["expected_context_claims"],
        }
    )
    claims: tuple[EventClaim | ContextClaim, ...] = (*batch.claims, *batch.context_claims)
    reviews = tuple(
        EventReview(
            claim_id=claim.claim_id,
            claim_sha256=claim.fingerprint,
            verdict="supported",
            reviewer="source-review-before-extraction",
            note="See issue-14/reference-review.md and the frozen source reference.",
        )
        for claim in claims
    )
    return snapshot, batch, reviews


def test_life_event_admission_preserves_roles_unknown_dates_and_uncertain_paternity() -> None:
    snapshot, batch, reviews = life_reference()
    admission = admit_events(snapshot, batch, reviews)
    assert all(d.status == "admitted" for d in admission.decisions)
    assert [(c.event_type, c.story_time) for c in batch.claims] == [
        ("pregnancy", "unknown"),
        ("pregnancy", "Christmas Day 2005"),
        ("pregnancy", "unknown"),
        ("death", "unknown"),
        ("death", "unknown"),
    ]
    assert {(p.character_id, p.role) for c in batch.claims for p in c.participants} == {
        ("peggy-mitchell", "pregnant_person"),
        ("sharon-watts", "pregnant_person"),
        ("peggy-mitchell", "deceased"),
        ("lucy-beale", "deceased"),
    }


def test_themes_and_classification_gaps_are_admitted_only_as_text() -> None:
    snapshot, batch, reviews = life_reference()
    report = admit_events(snapshot, batch, reviews)
    assert [d.claim_id for d in report.text_decisions if d.status == "admitted"] == [
        "peggy-abuse-theme",
        "tape-revelation",
    ]
    assert not {d.claim_id for d in report.decisions} & {
        "peggy-abuse-theme",
        "tape-revelation",
    }
    assert batch.context_claims[0].theme == "domestic_abuse"
    assert batch.context_claims[1].classification_gap == (
        "Public revelation of an affair has no checked event category in this graph."
    )


@pytest.mark.parametrize(
    "event_index,change,reason",
    [
        (
            0,
            {"participants": [{"character_id": "phil-mitchell", "role": "perpetrator"}]},
            "participant_role",
        ),
        (
            3,
            {"participants": [{"character_id": "pat-butcher", "role": "witness"}]},
            "participant_role",
        ),
        (3, {"certainty": "uncertain"}, "uncertain"),
        (3, {"polarity": "negated"}, "negated"),
        (0, {"basis": "allegation"}, "account_basis"),
    ],
)
def test_life_event_role_uncertainty_and_negation_errors_are_held(
    event_index: int, change: dict[str, object], reason: str
) -> None:
    snapshot, batch, reviews = life_reference()
    claim = EventClaim.model_validate({**batch.claims[event_index].model_dump(), **change})
    changed = batch.model_copy(update={"claims": (claim,), "context_claims": ()})
    review = reviews[event_index].model_copy(update={"claim_sha256": claim.fingerprint})
    decision = admit_events(snapshot, changed, (review,)).decisions[0]
    assert decision.status == "held" and reason in decision.reasons


def test_funeral_date_or_changed_theme_cannot_reuse_a_source_review() -> None:
    snapshot, batch, reviews = life_reference()
    death = batch.claims[3].model_copy(
        update={"story_time": "4 July 2016", "time_precision": "exact"}
    )
    theme = batch.context_claims[0].model_copy(update={"theme": "manosphere"})
    changed = batch.model_copy(update={"claims": (death,), "context_claims": (theme,)})
    report = admit_events(snapshot, changed, (reviews[3], reviews[5]))
    assert report.decisions[0].status == report.text_decisions[0].status == "held"
    assert "support_review_required" in report.decisions[0].reasons
    assert "support_review_required" in report.text_decisions[0].reasons


def test_theme_or_unclassified_fact_cannot_be_parsed_as_an_event() -> None:
    from pydantic import ValidationError

    _, batch, _ = life_reference()
    for kind in ("theme", "unclassified"):
        with pytest.raises(ValidationError):
            EventClaim.model_validate({**batch.claims[0].model_dump(), "event_type": kind})


def test_graph_filters_life_events_and_retains_classification_without_creating_edges(
    database_url: str,
) -> None:
    snapshot, batch, reviews = life_reference()
    EvidenceStore(database_url).load(snapshot)
    graph = EventGraph(database_url)
    installed = graph.install(batch, reviews)
    query = EventQuery(kind="life_events", character_id="peggy-mitchell")
    result = graph.query(snapshot.snapshot_id, query)
    assert result.status == "found"
    assert {c.event_type for c in result.claims} == {"pregnancy", "death"}
    assert graph.audit(snapshot.snapshot_id) == installed
    for character, participant in (
        ("peggy-mitchell", "phil-mitchell"),
        ("grant-mitchell", "sharon-watts"),
    ):
        shared = graph.query(
            snapshot.snapshot_id,
            EventQuery(kind="life_events", character_id=character, participant_id=participant),
        )
        assert shared.status == "empty" and not shared.claims
    crime = graph.query(
        snapshot.snapshot_id, EventQuery(kind="crime_history", character_id="peggy-mitchell")
    )
    assert crime.status == "empty" and not crime.claims
    for kind in ("theme", "unclassified"):
        ineligible = graph.query(
            snapshot.snapshot_id,
            EventQuery.model_validate({"kind": kind, "character_id": "grant-mitchell"}),
        )
        assert ineligible.status == "ineligible" and not ineligible.claims
        assert "text" in ineligible.limitation
    annotations = graph.text_context(snapshot.snapshot_id, ("tape-revelation",))
    assert len(annotations) == 1 and annotations[0].kind == "unclassified"
    assert graph.text_context(snapshot.snapshot_id, ("lucy-death",)) == ()


def test_shared_incident_selection_respects_event_family_participant_roles(
    database_url: str,
) -> None:
    import hashlib

    snapshot, batch, _ = life_reference()
    text = "Synthetic fixture: Peggy dies. Phil is falsely accused of causing her death."
    passage = snapshot.passages[3].model_copy(
        update={
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "start": 0,
            "end": len(text),
            "location": None,
            "source": snapshot.source.model_copy(update={"support_status": "synthetic_fixture"}),
        }
    )
    snapshot = snapshot.model_copy(
        update={
            "snapshot_id": "synthetic-mixed-event",
            "passages": (passage,),
            "source": passage.source,
        }
    )
    death = EventClaim.model_validate(
        {
            **batch.claims[3].model_dump(),
            "event_label": "Synthetic incident",
            "evidence": [
                {"evidence_id": passage.evidence_id, "start": 0, "end": len(text), "quote": text}
            ],
        }
    )
    accusation = EventClaim.model_validate(
        {
            **death.model_dump(),
            "claim_id": "synthetic-accusation",
            "event_type": "accusation",
            "basis": "allegation",
            "account_status": "explicitly_false",
            "participants": [{"character_id": "phil-mitchell", "role": "accused"}],
        }
    )
    batch = batch.model_copy(
        update={
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "claims": (death, accusation),
            "context_claims": (),
        }
    )
    reviews = tuple(
        EventReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="synthetic-rule-test",
            note="Manufactured fixture, not canon.",
        )
        for c in batch.claims
    )
    EvidenceStore(database_url).load(snapshot)
    graph = EventGraph(database_url)
    graph.install(batch, reviews)
    for kind, character in (("life_events", "phil-mitchell"), ("crime_history", "peggy-mitchell")):
        result = graph.query(
            snapshot.snapshot_id,
            EventQuery.model_validate(
                {
                    "kind": kind,
                    "character_id": character,
                }
            ),
        )
        assert result.status == "empty"
    shared = graph.query(
        snapshot.snapshot_id,
        EventQuery(
            kind="life_events", character_id="peggy-mitchell", participant_id="phil-mitchell"
        ),
    )
    assert shared.status == "empty"


def test_api_life_answers_preserve_timing_and_disclose_ineligible_categories(
    database_url: str, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app

    snapshot, batch, reviews = life_reference()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/life.db")
    ) as client:
        for character, event, words in (
            ("peggy-mitchell", "peggy-death", "Peggy Mitchell died; story date unknown"),
            ("sharon-watts", "sharon-christmas-pregnancy", "Christmas Day 2005 (exact)"),
            ("sharon-watts", "sharon-uncertain-paternity", "Sharon Watts was pregnant"),
        ):
            query = {"kind": "life_events", "character_id": character, "event_id": event}
            response = client.post(
                "/v1/answers",
                json={
                    "snapshot_id": snapshot.snapshot_id,
                    "question": "What life event is supported and when did it happen?",
                    "route": "graph",
                    "graph": query,
                },
            )
            assert response.status_code == 200, response.text
            answer = response.json()["response"]
            assert answer["status"] == "partial" and words in answer["answer"]
            assert "pregnancy and death history" in answer["answer"]
            assert "does not establish unmentioned parentage" in answer["answer"]
            assert answer["execution"]["model_calls"] == 0
            assert (
                answer["graph"]
                == client.post(f"/v1/snapshots/{snapshot.snapshot_id}/events", json=query).json()
            )
            assert all(
                client.get(c["resolve_path"]).status_code == 200 for c in answer["citations"]
            )
        unsupported = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Does a shared manosphere theme connect Grant and Phil?",
                "route": "graph",
                "graph": {
                    "kind": "theme",
                    "character_id": "grant-mitchell",
                    "participant_id": "phil-mitchell",
                },
            },
        ).json()["response"]
        assert unsupported["status"] == "insufficient_evidence" and not unsupported["citations"]
        assert unsupported["graph"]["status"] == "ineligible"
        assert "Use the text route" in unsupported["answer"]


def test_cli_can_select_life_events_and_receive_limited_theme_outcomes(
    database_url: str,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    import os
    import subprocess
    import sys

    from ask_phil.api import create_app

    snapshot, batch, reviews = life_reference()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    with http_server(create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/cli.db")) as url:
        for kind, status in (("life_events", "partial"), ("theme", "insufficient_evidence")):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ask_phil.cli",
                    "--api-url",
                    url,
                    "ask",
                    "What is supported about Peggy?",
                    "--snapshot",
                    snapshot.snapshot_id,
                    "--route",
                    "graph",
                    "--event-kind",
                    kind,
                    "--character",
                    "peggy-mitchell",
                    "--event",
                    "peggy-pregnancy",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "NO_PROXY": "127.0.0.1"},
            )
            assert result.returncode == 0, result.stderr
            answer = json.loads(result.stdout)["response"]
            assert answer["status"] == status
            assert answer["graph"]["query"]["kind"] == kind
