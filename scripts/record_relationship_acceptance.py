"""Record actual public answers from raw-pilot and explicitly curated projections."""

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter
from record_family_acceptance import serve

from ask_phil.answering import application_fingerprint
from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import ClaimReview
from ask_phil.relationship_evaluation import score_relationships
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery
from ask_phil.relationships import ExtractedRelationships, RelationshipBatch
from ask_phil.storage import EvidenceStore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable PostgreSQL admin connection."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-12-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; evidence records are immutable.")
    directory = Path("docs/implementation/issue-12")
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/relationship-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/relationships-v2.json").read_bytes())
    expected = ExtractedRelationships(claims=reference["expected_claims"])
    cases = [
        ("repeated-marriages", "kat-slater", "alfie-moon", 20),
        ("separation-is-not-divorce", "phil-mitchell", "kathy-beale", 20),
        ("affair", "phil-mitchell", "sharon-watts", 20),
        ("divorce", "grant-mitchell", "sharon-watts", 20),
        ("adoptive-parent", "sharon-watts", "den-watts", 20),
        ("adoptive-direction", "den-watts", "sharon-watts", 20),
        ("step-parent", "denise-fox", "amy-mitchell", 20),
        ("step-direction", "amy-mitchell", "denise-fox", 20),
        ("biological-parent", "ben-mitchell", "phil-mitchell", 20),
        ("both-biological-parents", "ben-mitchell", None, 20),
        ("empty-is-not-negative", "kat-slater", "den-watts", 20),
        ("performer-is-not-character", "shane-richie", None, 20),
        ("bounded", "phil-mitchell", "kathy-beale", 1),
    ]
    responses: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    audits: dict[str, Any] = {}
    with psycopg.connect(args.database_url, autocommit=True) as admin:
        for phase, batch_file, review_file in (
            ("raw-pilot", "raw-claims.json", "raw-claim-reviews.json"),
            (
                "reviewed-with-raw-retained",
                "reviewed-claims-v2.json",
                "reviewed-claim-reviews-v2.json",
            ),
        ):
            name = "ask_phil_relationship_acceptance_" + uuid4().hex
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            database_url = make_conninfo(args.database_url, dbname=name)
            try:
                batch = RelationshipBatch.model_validate_json((directory / batch_file).read_bytes())
                reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_json(
                    (directory / review_file).read_bytes()
                )
                EvidenceStore(database_url).load(snapshot)
                audit = RelationshipGraph(database_url).install(batch, reviews)
                audits[phase] = audit.admission.model_dump(mode="json")
                with (
                    serve(database_url, args.tracking_uri) as url,
                    httpx.Client(
                        base_url=url,
                        trust_env=False,
                        timeout=30,
                    ) as client,
                ):
                    for case_id, character, partner, bound in cases:
                        query = RelationshipQuery(
                            kind="relationship_history",
                            character_id=character,
                            partner_id=partner,
                            max_events=bound,
                        )
                        request = {
                            "snapshot_id": snapshot.snapshot_id,
                            "route": "graph",
                            "question": f"Explain the history of {character} and {partner}",
                            "graph": query.model_dump(mode="json"),
                        }
                        response = client.post("/v1/answers", json=request)
                        response.raise_for_status()
                        receipt = response.json()
                        answer = receipt["response"]
                        for citation in answer["citations"]:
                            evidence = client.get(citation["resolve_path"])
                            evidence.raise_for_status()
                            assert evidence.json()["matches"][0]["sha256"] == citation["sha256"]
                        required = ExtractedRelationships(
                            claims=tuple(
                                c
                                for c in expected.claims
                                if character in (c.subject_id, c.object_id)
                                and (partner is None or partner in (c.subject_id, c.object_id))
                            )
                        )
                        value_score = score_relationships(
                            json.dumps({"claims": answer.get("graph", {}).get("claims", [])}),
                            required,
                            snapshot,
                            reference.get("alternatives"),
                        )
                        responses.append(
                            {
                                "phase": phase,
                                "case_id": case_id,
                                "transport": "api",
                                "response": answer,
                                "citations_resolve": True,
                                "reference_comparison": value_score.model_dump(mode="json"),
                            }
                        )
                    typed = client.post(
                        f"/v1/snapshots/{snapshot.snapshot_id}/relationships",
                        json={
                            "kind": "relationship_history",
                            "character_id": "kat-slater",
                        },
                    )
                    typed.raise_for_status()
                    invalid = client.post(
                        "/v1/answers",
                        json={
                            "route": "graph",
                            "question": "Invalid mixed meanings",
                            "graph": {
                                "kind": "relationship_history",
                                "character_id": "kat-slater",
                                "direction": "ancestors",
                            },
                        },
                    )
                    assert invalid.status_code == 422
                    cli = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "ask_phil.cli",
                            "--api-url",
                            url,
                            "ask",
                            "Explain Kat and Alfie's marriages",
                            "--route",
                            "graph",
                            "--history",
                            "--character",
                            "kat-slater",
                            "--partner",
                            "alfie-moon",
                            "--snapshot",
                            snapshot.snapshot_id,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                        env={**os.environ, "NO_PROXY": "127.0.0.1"},
                    )
                    responses.append(
                        {
                            "phase": phase,
                            "case_id": "cli-marriages",
                            "transport": "cli",
                            "response": json.loads(cli.stdout)["response"],
                        }
                    )
                    lookup = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/relationship-claims")
                    assert lookup.json() == audit.model_dump(mode="json")
                with (
                    serve(database_url, args.tracking_uri) as url,
                    httpx.Client(
                        base_url=url,
                        trust_env=False,
                        timeout=30,
                    ) as client,
                ):
                    saved = client.get(
                        f"/v1/responses/{receipt['response']['response_id']}",
                        headers={
                            "Authorization": f"Bearer {receipt['read_token']}",
                        },
                    )
                    assert saved.json() == receipt["response"]
                checks.append(
                    {
                        "phase": phase,
                        "typed_tool": typed.json(),
                        "invalid_mixed_query_http": 422,
                        "audit_readback_matches": True,
                        "original_response_survives_restart": True,
                    }
                )
            finally:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    for record in responses:
        answer = record["response"]
        trace = tracking.get_trace(answer["trace_id"], flush=True)
        assert trace is not None
        root = next(s for s in trace.data.spans if s.name == "graph")
        tool = next(s for s in trace.data.spans if s.name == "relationship_history")
        assert root.outputs == answer
        assert tool.outputs == answer["graph"]
        assert answer["execution"]["model_calls"] == 0 and answer["execution"]["tool_calls"] == 1
        record["trace_output_matches"] = True
        record["trace_span_names"] = [s.name for s in trace.data.spans]
    payload = {
        "captured_at": datetime.now(UTC).isoformat(),
        "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "application_sha256": application_fingerprint(),
        "snapshot_sha256": snapshot.fingerprint,
        "admissions": audits,
        "responses": responses,
        "checks": checks,
        "paid_serving_calls": 0,
        "serving_inference_usd": 0,
        "limitation": (
            "Raw model failures are retained. The second projection admits pre-pilot "
            "agent-reviewed claims and retains all raw candidates/holds. It demonstrates "
            "curated capability, not successful automatic extraction or held-out/canon "
            "acceptance. Hosting/database costs excluded."
        ),
    }
    with args.output.open("x") as output:
        json.dump(payload, output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(
        json.dumps({"output": str(args.output), "responses": len(responses), "traces_match": True})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
