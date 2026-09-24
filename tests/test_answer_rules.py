import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as SchemaError
from jsonschema import validate

from ask_phil.answers import AnswerRecord, AskRequest, Draft, assemble_context, cite_answer
from ask_phil.evidence import SourceSnapshot
from ask_phil.retrieval import RetrievedPassage


def test_schema_sent_to_model_rejects_a_timing_note_without_precision() -> None:
    raw = {
        "answer": "I arrived in February 1990.",
        "status": "answered",
        "evidence_ids": ["phil-arrival-001"],
        "unanswered": [],
        "qualifications": [
            {"kind": "timing", "detail": "February 1990", "evidence_ids": ["phil-arrival-001"]}
        ],
    }
    with pytest.raises(SchemaError):
        validate(raw, Draft.model_json_schema())


@pytest.mark.parametrize("missing", ["status", "unanswered", "qualifications"])
def test_generated_drafts_cannot_omit_policy_fields(missing: str) -> None:
    raw: dict[str, object] = {
        "answer": "A cited answer",
        "evidence_ids": ["phil-arrival-001"],
        "status": "answered",
        "unanswered": [],
        "qualifications": [],
    }
    del raw[missing]
    with pytest.raises(ValueError, match="Field required"):
        Draft.model_validate(raw)


def test_answer_cannot_cite_a_retrieved_passage_excluded_from_final_context(
    seed: SourceSnapshot,
) -> None:
    context = assemble_context((RetrievedPassage(passage=seed.passages[0], similarity=0.9),), 50)
    assert context == ()
    with pytest.raises(ValueError, match="assembled context"):
        cite_answer(
            Draft(
                answer="I arrived in February 1990.",
                evidence_ids=("phil-arrival-001",),
                status="answered",
                unanswered=(),
                qualifications=(),
            ),
            context,
            seed.snapshot_id,
        )


def test_multibyte_question_cannot_exceed_the_context_input_budget() -> None:
    with pytest.raises(ValueError, match="input budget"):
        AskRequest(snapshot_id="phil-arrival-v1", question="🦄" * 300)


@pytest.mark.parametrize(
    "status,ids,unanswered",
    [
        ("answered", [], []),
        ("answered", ["phil-arrival-001"], ["Mother?"]),
        ("partial", ["phil-arrival-001"], []),
        ("clarification", [], []),
        ("insufficient_evidence", ["phil-arrival-001"], []),
        ("answered", ["phil-arrival-001", "phil-arrival-001"], []),
    ],
)
def test_invalid_outcome_citation_combinations_are_rejected(
    seed: SourceSnapshot, status: str, ids: list[str], unanswered: list[str]
) -> None:
    draft = Draft.model_validate(
        {
            "answer": "An example",
            "status": status,
            "evidence_ids": ids,
            "unanswered": unanswered,
            "qualifications": [],
        }
    )
    with pytest.raises(ValueError, match="assembled context"):
        cite_answer(draft, seed.passages, seed.snapshot_id)


@pytest.mark.parametrize(
    "qualification",
    [
        {
            "kind": "false_premise",
            "detail": "Unsupported qualification",
            "evidence_ids": ["invented"],
        },
        {"kind": "conflict", "detail": "Only one account", "evidence_ids": ["phil-arrival-001"]},
        {"kind": "timing", "detail": "Precision missing", "evidence_ids": ["phil-arrival-001"]},
        {
            "kind": "false_premise",
            "detail": "Spurious precision",
            "precision": "exact",
            "evidence_ids": ["phil-arrival-001"],
        },
    ],
)
def test_qualifications_cannot_fabricate_citations_or_omit_required_information(
    seed: SourceSnapshot, qualification: dict[str, object]
) -> None:
    with pytest.raises(ValueError):
        draft = Draft.model_validate(
            {
                "answer": "An example",
                "evidence_ids": ["phil-arrival-001"],
                "qualifications": [qualification],
                "status": "answered",
                "unanswered": [],
            }
        )
        cite_answer(draft, seed.passages, seed.snapshot_id)


def test_saved_v1_response_keeps_its_original_document_shape() -> None:
    original = json.loads(Path("docs/implementation/issue-3/docker-serving.json").read_text())[
        "response"
    ]
    assert AnswerRecord.model_validate(original).model_dump(mode="json") == original
