import json
from decimal import Decimal
from pathlib import Path

import httpx
from test_relationship_claims import reference_batch

from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
from ask_phil.parentage_extraction import ClaimLLM
from ask_phil.relationship_extraction import extract_relationships
from ask_phil.relationships import ExtractedRelationships


def test_structured_extraction_uses_source_inputs_and_retains_candidates(tmp_path: Path) -> None:
    snapshot, reference, _ = reference_batch()
    candidate = reference.claims[0].model_copy(update={"claim_id": "provider-candidate"})
    outbound: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_reset": None,
                        "limit_remaining": 5,
                    }
                },
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": "test-provider",
                                "name": "Test | test/model-v1",
                                "supported_parameters": [
                                    "structured_outputs",
                                    "response_format",
                                    "reasoning",
                                    "max_tokens",
                                ],
                            }
                        ]
                    }
                },
            )
        body = json.loads(request.content)
        outbound.append(body["messages"][0]["content"])
        return httpx.Response(
            200,
            json={
                "id": "test-extraction",
                "model": "test/model-v1",
                "provider": "Test",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": ExtractedRelationships(
                                claims=(candidate,)
                            ).model_dump_json(),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.00001},
            },
        )

    profile = OpenRouterProfile(
        answer_model="test/model",
        canonical_slug="test/model-v1",
        provider="test-provider",
        input_price_per_million=Decimal("0.15"),
        output_price_per_million=Decimal("0.47"),
        output_tokens=4096,
        reasoning_effort="low",
    )
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        chat = OpenRouterChat(
            profile, "synthetic-provider-key", Budget(tmp_path / "budget.db"), client
        )
        batch, elapsed = extract_relationships(
            snapshot, reference.catalogue, ClaimLLM(chat, ExtractedRelationships)
        )
    assert batch.claims == (candidate,)
    assert batch.snapshot_sha256 == snapshot.fingerprint and elapsed > 0
    assert len(outbound) == 1
    assert candidate.evidence[0].quote in outbound[0]
    assert "phil-kathy-marriage" not in outbound[0]
    assert "review_note" not in outbound[0] and "synthetic-provider-key" not in outbound[0]
