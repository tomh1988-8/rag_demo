"""One pinned snapshot and request budget for reviewed, typed graph execution."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import cached_property
from typing import overload

import psycopg

from ask_phil.connection_graph import ConnectionGraph, ConnectionQuery, ConnectionResult
from ask_phil.event_graph import EventGraph, EventQuery, EventResult
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionStopped
from ask_phil.family_graph import FamilyGraph, FamilyQuery, FamilyResult
from ask_phil.publications import ActivePublication, PublicationStore
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery, RelationshipResult
from ask_phil.storage import EvidenceStore

type GraphQuery = FamilyQuery | RelationshipQuery | EventQuery | ConnectionQuery
type GraphResult = FamilyResult | RelationshipResult | EventResult | ConnectionResult


class GraphExecution:
    def __init__(
        self,
        database_url: str,
        snapshot_id: str | None,
        *,
        execution: ExecutionBudget | ExecutionLimits,
        publication: ActivePublication | None = None,
    ) -> None:
        self._database_url = database_url
        self._budget = (
            execution if isinstance(execution, ExecutionBudget) else ExecutionBudget(execution)
        )
        with self._active():
            self.publication = PublicationStore(database_url).pin(snapshot_id, pinned=publication)
        self._snapshot_id = snapshot_id or (
            self.publication.manifest.snapshot_id if self.publication else ""
        )

    @cached_property
    def snapshot(self) -> SourceSnapshot:
        """Answers need captured passages; direct queries load them in their typed module."""
        with self._active():
            return EvidenceStore(self._database_url).snapshot(self._snapshot_id)

    @contextmanager
    def _active(self) -> Iterator[None]:
        with self._budget.activate():
            try:
                yield
            except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable):
                self._budget.record_stop("timeout")
                raise
            except ExecutionStopped as exc:
                self._budget.record_stop(str(exc))
                raise

    @overload
    def query(self, query: FamilyQuery) -> FamilyResult: ...

    @overload
    def query(self, query: RelationshipQuery) -> RelationshipResult: ...

    @overload
    def query(self, query: EventQuery) -> EventResult: ...

    @overload
    def query(self, query: ConnectionQuery) -> ConnectionResult: ...

    def query(self, query: GraphQuery) -> GraphResult:
        """Use the same publication and budget, including a caller's earlier consumption."""
        with self._active():
            self._budget.check()
            result: GraphResult
            if isinstance(query, ConnectionQuery):
                result = ConnectionGraph(self._database_url).query(
                    self._snapshot_id, query, publication=self.publication
                )
            elif isinstance(query, EventQuery):
                result = EventGraph(self._database_url).query(
                    self._snapshot_id, query, publication=self.publication
                )
            elif isinstance(query, RelationshipQuery):
                result = RelationshipGraph(self._database_url).query(
                    self._snapshot_id, query, publication=self.publication
                )
            else:
                result = FamilyGraph(self._database_url).query(
                    self._snapshot_id, query, publication=self.publication
                )
            self._budget.check()
            return result
