"""Immutable original responses, with a scoped bearer capability for reading one response."""

import hashlib
import secrets
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from ask_phil.answers import AnswerReceipt, AnswerRecord


class ResponseLedger:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def save(self, response: AnswerRecord) -> AnswerReceipt:
        token = secrets.token_urlsafe(32)
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728194)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS answer_responses (
                    response_id uuid PRIMARY KEY,
                    token_sha256 text NOT NULL,
                    document jsonb NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO answer_responses VALUES (%s, %s, %s)",
                (
                    response.response_id,
                    hashlib.sha256(token.encode()).hexdigest(),
                    Jsonb(response.model_dump(mode="json")),
                ),
            )
        return AnswerReceipt(response=response, read_token=token)

    def get(self, response_id: UUID, token: str) -> AnswerRecord | None:
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            if conn.execute("SELECT to_regclass('answer_responses')").fetchone() == (None,):
                return None
            row = conn.execute(
                """SELECT document FROM answer_responses
                   WHERE response_id = %s AND token_sha256 = %s""",
                (response_id, hashlib.sha256(token.encode()).hexdigest()),
            ).fetchone()
        return AnswerRecord.model_validate(row[0]) if row else None
