"""Authorized conversation turns and short-lived reference state, separate from saved answers."""

import hashlib
import secrets
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from ask_phil.answers import AnswerReceipt, AskRequest
from ask_phil.conversation import (
    MAX_CONTEXT_TURNS,
    ReferenceTurn,
    TurnIdentity,
)
from ask_phil.evidence import Record
from ask_phil.execution import database_options

SESSION_LIFETIME = timedelta(hours=2)
CONTEXT_IDLE_LIFETIME = timedelta(minutes=30)
FEEDBACK_LIFETIME = timedelta(days=30)


class SessionNotFound(LookupError):
    pass


class SessionState(Record):
    session_id: UUID
    created_at: datetime
    expires_at: datetime
    context_expires_at: datetime
    generation: int = 0
    turn_number: int = 0
    history: tuple[ReferenceTurn, ...] = ()


class SessionReceipt(Record):
    session: SessionState
    session_token: str
    feedback_token: str
    feedback_expires_at: datetime


class FeedbackContext(Record):
    session_id: UUID
    expires_at: datetime


class AnswerQuestion(Protocol):
    def __call__(
        self, request: AskRequest, *, turn: TurnIdentity, history: tuple[ReferenceTurn, ...]
    ) -> AnswerReceipt: ...


class ConversationSessions:
    def __init__(
        self, database_url: str, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self.database_url = database_url
        self._clock = clock

    def _ensure_schema(self) -> None:
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728196)")
            conn.execute("""CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id uuid PRIMARY KEY,
                token_sha256 text NOT NULL,
                expires_at timestamptz NOT NULL,
                document jsonb NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS conversation_feedback_contexts (
                session_id uuid PRIMARY KEY,
                token_sha256 text NOT NULL,
                expires_at timestamptz NOT NULL
            )""")

    def create(self) -> SessionReceipt:
        self._ensure_schema()
        now = self._clock()
        state = SessionState(
            session_id=uuid4(),
            created_at=now,
            expires_at=now + SESSION_LIFETIME,
            context_expires_at=now + CONTEXT_IDLE_LIFETIME,
        )
        token = secrets.token_urlsafe(32)
        feedback_token = secrets.token_urlsafe(32)
        feedback_expires_at = now + FEEDBACK_LIFETIME
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            conn.execute("DELETE FROM conversation_sessions WHERE expires_at <= %s", (now,))
            conn.execute(
                "DELETE FROM conversation_feedback_contexts WHERE expires_at <= %s", (now,)
            )
            conn.execute(
                "INSERT INTO conversation_sessions VALUES (%s, %s, %s, %s)",
                (
                    state.session_id,
                    hashlib.sha256(token.encode()).hexdigest(),
                    state.expires_at,
                    Jsonb(state.model_dump(mode="json")),
                ),
            )
            conn.execute(
                "INSERT INTO conversation_feedback_contexts VALUES (%s, %s, %s)",
                (
                    state.session_id,
                    hashlib.sha256(feedback_token.encode()).hexdigest(),
                    feedback_expires_at,
                ),
            )
        return SessionReceipt(
            session=state,
            session_token=token,
            feedback_token=feedback_token,
            feedback_expires_at=feedback_expires_at,
        )

    def ask(
        self,
        session_id: UUID,
        token: str,
        request: AskRequest,
        *,
        answer: AnswerQuestion,
    ) -> AnswerReceipt:
        """Return an answer only after its authorized turn and reference state are committed."""
        with self._locked(session_id, token) as (conn, state):
            turn = TurnIdentity(
                session_id=state.session_id,
                turn_id=uuid4(),
                turn_number=state.turn_number + 1,
                generation=state.generation,
            )
            receipt = answer(request, turn=turn, history=state.history)
            reference = receipt.response.conversation
            if reference is None or (
                reference.session_id,
                reference.turn_id,
                reference.turn_number,
                reference.generation,
            ) != (turn.session_id, turn.turn_id, turn.turn_number, turn.generation):
                raise ValueError("Answer does not belong to the current conversation turn.")
            self._save(
                conn,
                state.model_copy(
                    update={
                        "turn_number": turn.turn_number,
                        "context_expires_at": min(
                            self._clock() + CONTEXT_IDLE_LIFETIME, state.expires_at
                        ),
                        "history": (*state.history, reference.retained())[-MAX_CONTEXT_TURNS:],
                    }
                ),
            )
            return receipt

    @contextmanager
    def _locked(
        self, session_id: UUID, token: str
    ) -> Iterator[tuple[psycopg.Connection[tuple[object, ...]], SessionState]]:
        self._ensure_schema()
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            row = conn.execute(
                """SELECT document FROM conversation_sessions
                WHERE session_id = %s AND token_sha256 = %s AND expires_at > %s FOR UPDATE""",
                (session_id, hashlib.sha256(token.encode()).hexdigest(), self._clock()),
            ).fetchone()
            if not row:
                raise SessionNotFound("Session not found or expired.")
            state = SessionState.model_validate(row[0])
            now = self._clock()
            if state.expires_at <= now:
                raise SessionNotFound("Session not found or expired.")
            if state.context_expires_at <= now:
                state = state.model_copy(
                    update={
                        "history": (),
                        "generation": state.generation + (1 if state.history else 0),
                    }
                )
                self._save(conn, state)
            yield conn, state

    def _save(self, conn: psycopg.Connection[tuple[object, ...]], state: SessionState) -> None:
        conn.execute(
            "UPDATE conversation_sessions SET document = %s WHERE session_id = %s",
            (Jsonb(state.model_dump(mode="json")), state.session_id),
        )

    def reset(self, session_id: UUID, token: str) -> SessionState:
        with self._locked(session_id, token) as (conn, state):
            cleared = state.model_copy(
                update={
                    "generation": state.generation + 1,
                    "history": (),
                    "context_expires_at": min(
                        self._clock() + CONTEXT_IDLE_LIFETIME, state.expires_at
                    ),
                }
            )
            self._save(conn, cleared)
            return cleared

    def get(self, session_id: UUID, token: str) -> SessionState:
        with self._locked(session_id, token) as (_, state):
            return state

    def feedback_context(self, session_id: UUID, token: str) -> FeedbackContext | None:
        """Authorize only the anonymous feedback context; never read answer memory.

        #22 must also verify the selected response belongs to this session.
        """
        self._ensure_schema()
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            row = conn.execute(
                """SELECT expires_at FROM conversation_feedback_contexts
                WHERE session_id = %s AND token_sha256 = %s AND expires_at > %s""",
                (session_id, hashlib.sha256(token.encode()).hexdigest(), self._clock()),
            ).fetchone()
        return FeedbackContext(session_id=session_id, expires_at=row[0]) if row else None
