"""Bounded character connections composed from immutable admitted SQL projections."""

from typing import TYPE_CHECKING, Annotated, Literal, Self

import psycopg
from psycopg import sql
from pydantic import Field, TypeAdapter, model_validator

from ask_phil.claim_projections import FamilyEdge, GraphVersions, graph_versions
from ask_phil.claims import ClaimEvidence
from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, read_options
from ask_phil.relationships import DIRECTED_RELATIONS, RelationshipClaim
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventClaim

if TYPE_CHECKING:
    from ask_phil.publications import ActivePublication

CONNECTION_LIMITATION = (
    "Only admitted relationships and shared incident roles in this captured snapshot are "
    "traversed, within the stated depth, path and expansion bounds. No path is limited "
    "coverage, not proof that no connection exists in the programme. Social ties do not "
    "establish biological ancestry. Historical ties do not establish a current relationship. "
    "Shared incidents do not transfer guilt, parentage or presence between participants. "
    "Themes, co-appearance and performers do not create connections. "
    "Source-supported does not mean independently cross-checked."
)


class ConnectionQuery(Record):
    kind: Literal["connection"]
    character_id: Identifier
    target_id: Identifier
    max_depth: int = Field(default=3, ge=1, le=6)
    max_paths: int = Field(default=5, ge=1, le=20)
    max_expansions: int = Field(default=500, ge=1, le=5000)

    @model_validator(mode="after")
    def distinct_characters(self) -> Self:
        if self.character_id == self.target_id:
            raise ValueError("A connection requires two distinct characters.")
        return self


class BiologicalStep(Record):
    kind: Literal["biological"]
    from_id: Identifier
    to_id: Identifier
    direction: Literal["parent_to_child", "child_to_parent"]
    edge: FamilyEdge

    @model_validator(mode="after")
    def directed_endpoints(self) -> Self:
        expected = (self.edge.parent_id, self.edge.child_id)
        if self.direction == "child_to_parent":
            expected = expected[::-1]
        if self.from_id == self.to_id or (self.from_id, self.to_id) != expected:
            raise ValueError("Biological step endpoints must preserve parentage direction.")
        return self

    @property
    def evidence(self) -> tuple[ClaimEvidence, ...]:
        return self.edge.evidence


class RelationshipStep(Record):
    kind: Literal["relationship"]
    from_id: Identifier
    to_id: Identifier
    direction: Literal["subject_to_object", "object_to_subject", "symmetric"]
    claim: RelationshipClaim

    @model_validator(mode="after")
    def directed_endpoints(self) -> Self:
        endpoints = (self.claim.subject_id, self.claim.object_id)
        expected = (
            "subject_to_object" if (self.from_id, self.to_id) == endpoints else "object_to_subject"
        )
        if self.claim.relation not in DIRECTED_RELATIONS:
            expected = "symmetric"
        if (
            self.from_id == self.to_id
            or {self.from_id, self.to_id} != set(endpoints)
            or self.direction != expected
        ):
            raise ValueError("Relationship step endpoints must preserve the assertion's direction.")
        return self

    @property
    def evidence(self) -> tuple[ClaimEvidence, ...]:
        return self.claim.evidence


class SharedEventStep(Record):
    kind: Literal["shared_event"]
    from_id: Identifier
    to_id: Identifier
    direction: Literal["shared_incident"] = "shared_incident"
    event_id: Identifier
    claims: tuple[EventClaim, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def shared_incident(self) -> Self:
        participants = {p.character_id for c in self.claims for p in c.participants}
        if (
            self.from_id == self.to_id
            or not {self.from_id, self.to_id} <= participants
            or any(c.event_id != self.event_id for c in self.claims)
        ):
            raise ValueError("Both characters must have explicit roles in the same incident.")
        return self

    @property
    def evidence(self) -> tuple[ClaimEvidence, ...]:
        return tuple(e for c in self.claims for e in c.evidence)


type ConnectionStep = Annotated[
    BiologicalStep | RelationshipStep | SharedEventStep, Field(discriminator="kind")
]
type ConnectionMeaning = Literal[
    "connection",
    "biological_parent",
    "biological_child",
    "biological_grandparent",
    "biological_grandchild",
    "biological_sibling",
]


def _meaning(steps: tuple[ConnectionStep, ...]) -> ConnectionMeaning:
    directions = []
    for step in steps:
        if isinstance(step, BiologicalStep):
            directions.append(step.direction)
        elif isinstance(step, RelationshipStep) and step.claim.relation == "biological_parent":
            directions.append(
                "parent_to_child" if step.direction == "subject_to_object" else "child_to_parent"
            )
        else:
            return "connection"
    meanings: dict[tuple[str, ...], ConnectionMeaning] = {
        ("parent_to_child",): "biological_parent",
        ("child_to_parent",): "biological_child",
        ("parent_to_child", "parent_to_child"): "biological_grandparent",
        ("child_to_parent", "child_to_parent"): "biological_grandchild",
        ("child_to_parent", "parent_to_child"): "biological_sibling",
    }
    return meanings.get(tuple(directions), "connection")


class ConnectionPath(Record):
    characters: tuple[Identifier, ...] = Field(min_length=2, max_length=7)
    steps: tuple[ConnectionStep, ...] = Field(min_length=1, max_length=6)
    meaning: ConnectionMeaning

    @model_validator(mode="after")
    def supported_chain(self) -> Self:
        if len(set(self.characters)) != len(self.characters):
            raise ValueError("Connection paths cannot repeat characters.")
        if len(self.characters) != len(self.steps) + 1 or any(
            (s.from_id, s.to_id) != (self.characters[i], self.characters[i + 1])
            for i, s in enumerate(self.steps)
        ):
            raise ValueError("Each step must explain the next pair of path characters.")
        if self.meaning != _meaning(self.steps):
            raise ValueError("Derived meaning must follow from the typed path.")
        incidents = [s.event_id for s in self.steps if isinstance(s, SharedEventStep)]
        if len(incidents) != len(set(incidents)):
            raise ValueError("Connection paths cannot repeat a shared incident.")
        return self


class ConnectionResult(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graphs: GraphVersions = GraphVersions()
    query: ConnectionQuery
    status: Literal["found", "empty", "truncated", "unavailable", "unknown_character"]
    paths: tuple[ConnectionPath, ...] = ()
    names: dict[str, str] = Field(default_factory=dict)
    examined_paths: int = Field(default=0, ge=0)
    expansion_limit_reached: bool = False
    limitation: str = CONNECTION_LIMITATION


class ConnectionGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def query(
        self,
        snapshot_id: str,
        query: ConnectionQuery,
        *,
        publication: "ActivePublication | None" = None,
    ) -> ConnectionResult:
        from ask_phil.publications import PublicationStore

        pinned = PublicationStore(self.database_url).pin(snapshot_id, pinned=publication)
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        budget = current_execution.get()
        if budget:
            budget.tool_call("connection_graph")
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            versions = graph_versions(conn, snapshot_id)
            if pinned and pinned.manifest.graphs is not None and pinned.manifest.graphs != versions:
                raise ValueError("Connection graphs differ from the pinned publication.")
            names: dict[str, str] = {}
            for kind, version in versions.model_dump().items():
                if version is None:
                    continue
                row = conn.execute(
                    sql.SQL("SELECT document FROM {} WHERE snapshot_id=%s").format(
                        sql.Identifier(kind + "_projections")
                    ),
                    (snapshot_id,),
                ).fetchone()
                assert row is not None
                document = row[0]
                if document["batch"]["snapshot_sha256"] != snapshot.fingerprint:
                    raise ValueError("Graph source differs from the connection snapshot.")
                for character in document["batch"]["catalogue"]["characters"]:
                    cid, name = character["character_id"], character["name"]
                    if cid in names and names[cid] != name:
                        raise ValueError("Graph catalogues disagree about a character identity.")
                    names[cid] = name
            result = ConnectionResult(
                snapshot_id=snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                graphs=versions,
                query=query,
                status="unavailable",
                names=names,
            )
            if not names:
                return result
            if query.character_id not in names or query.target_id not in names:
                return result.model_copy(update={"status": "unknown_character"})
            links = []
            if versions.family:
                links.append(
                    sql.SQL("""
                SELECT e.parent_id AS origin, e.child_id AS target,
                    jsonb_build_object('kind','biological','from_id',e.parent_id,
                    'to_id',e.child_id,'direction','parent_to_child','edge',e.document) AS step
                FROM family_edges e WHERE graph_sha256={version}
                UNION ALL
                SELECT e.child_id, e.parent_id,
                    jsonb_build_object('kind','biological','from_id',e.child_id,
                    'to_id',e.parent_id,'direction','child_to_parent','edge',e.document)
                FROM family_edges e WHERE graph_sha256={version}
                """).format(version=sql.Literal(versions.family))
                )
            if versions.relationship:
                biological_filter = (
                    sql.SQL("""NOT EXISTS (SELECT 1 FROM family_edges f
                        WHERE f.graph_sha256={version}
                        AND f.parent_id=a.subject_id AND f.child_id=a.object_id)""").format(
                        version=sql.Literal(versions.family)
                    )
                    if versions.family
                    else sql.SQL("true")
                )
                links.append(
                    sql.SQL("""
                    SELECT endpoints.origin, endpoints.target,
                        jsonb_build_object('kind','relationship','from_id',endpoints.origin,
                        'to_id',endpoints.target,'direction',
                        CASE WHEN a.document->>'relation'=ANY({directed})
                        THEN endpoints.direction ELSE 'symmetric' END,'claim',a.document) AS step
                    FROM relationship_assertions a
                    CROSS JOIN LATERAL (VALUES
                        (a.subject_id,a.object_id,'subject_to_object'),
                        (a.object_id,a.subject_id,'object_to_subject')
                    ) AS endpoints(origin,target,direction)
                    WHERE a.graph_sha256={version}
                        AND (a.document->>'relation'<>'biological_parent' OR {biological_filter})
                """).format(
                        directed=sql.Literal(sorted(DIRECTED_RELATIONS)),
                        version=sql.Literal(versions.relationship),
                        biological_filter=biological_filter,
                    )
                )
            if versions.event:
                links.append(
                    sql.SQL("""
                    SELECT a.character_id AS origin, b.character_id AS target,
                        jsonb_build_object('kind','shared_event','from_id',a.character_id,
                        'to_id',b.character_id,'event_id',a.event_id,'claims',
                            (SELECT jsonb_agg(c.document ORDER BY c.claim_id)
                            FROM event_assertions c WHERE c.graph_sha256=a.graph_sha256
                            AND c.event_id=a.event_id)) AS step
                    FROM event_participants a JOIN event_participants b
                        ON b.graph_sha256=a.graph_sha256 AND b.event_id=a.event_id
                        AND b.character_id<>a.character_id
                    WHERE a.graph_sha256={version}
                """).format(version=sql.Literal(versions.event))
                )
            if not links:
                return result
            rows = conn.execute(
                sql.SQL("""
                WITH RECURSIVE links AS ({links}),
                walk(node, characters, steps, depth) AS (
                    SELECT %s::text, ARRAY[%s]::text[], '[]'::jsonb, 0
                    UNION ALL
                    SELECT l.target, w.characters || l.target,
                        w.steps || jsonb_build_array(l.step), w.depth+1
                    FROM walk w JOIN links l ON l.origin=w.node
                    WHERE w.depth<%s AND w.node<>%s AND NOT l.target=ANY(w.characters)
                    AND (l.step->>'kind'<>'shared_event' OR NOT w.steps @>
                        jsonb_build_array(jsonb_build_object('event_id',l.step->>'event_id')))
                ) SELECT node, characters, steps FROM walk WHERE depth>0 LIMIT %s
                """).format(links=sql.SQL(" UNION ALL ").join(links)),
                (
                    query.character_id,
                    query.character_id,
                    query.max_depth,
                    query.target_id,
                    query.max_expansions + 1,
                ),
            ).fetchall()
        if budget:
            budget.check()
        bounded = rows[: query.max_expansions]
        matches = [r for r in bounded if r[0] == query.target_id]
        paths = []
        for row in matches[: query.max_paths]:
            steps = TypeAdapter(tuple[ConnectionStep, ...]).validate_python(row[2])
            paths.append(ConnectionPath(characters=row[1], steps=steps, meaning=_meaning(steps)))
        truncated = len(rows) > query.max_expansions or len(matches) > query.max_paths
        return result.model_copy(
            update={
                "paths": tuple(paths),
                "examined_paths": len(bounded),
                "expansion_limit_reached": len(rows) > query.max_expansions,
                "status": "truncated" if truncated else "found" if paths else "empty",
            }
        )
