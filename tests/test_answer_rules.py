import pytest

from ask_phil.answers import AskRequest, Draft, assemble_context, cite_answer
from ask_phil.evidence import SourceSnapshot
from ask_phil.retrieval import RetrievedPassage


def test_answer_cannot_cite_a_retrieved_passage_excluded_from_final_context(
    seed: SourceSnapshot,
) -> None:
    context = assemble_context((RetrievedPassage(passage=seed.passages[0], similarity=0.9),), 50)
    assert context == ()
    with pytest.raises(ValueError, match="assembled context"):
        cite_answer(
            Draft(answer="I arrived in February 1990.", evidence_ids=("phil-arrival-001",)),
            context,
            seed.snapshot_id,
        )


def test_multibyte_question_cannot_exceed_the_context_input_budget() -> None:
    with pytest.raises(ValueError, match="input budget"):
        AskRequest(snapshot_id="phil-arrival-v1", question="🦄" * 300)
