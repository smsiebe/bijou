"""SQLAlchemy 2.0 repository implementing IGraphRepository with SQLite WAL thread-safety."""

import threading
from typing import Any

from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import sessionmaker

from bijou.adapters.db.tables import (
    Base,
    CausalGateRecord,
    ConcernRecord,
    DecisionLogRecord,
    EdgeRecord,
    EffectRecord,
    MilestoneRecord,
    OrganizationRecord,
    ThingRecord,
)
from bijou.core.contracts.enums import (
    AccumulatorPattern,
    CausalMechanismType,
    EffectTier,
    LifecycleStatus,
    MilestoneStatus,
    RelationshipType,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    CausalContributorDTO,
    CausalGateDTO,
    ConcernDTO,
    ConcernSatisfactionLinkDTO,
    DecisionLogEntryDTO,
    EffectDTO,
    FederationSpecDTO,
    GraphEdgeDTO,
    MilestoneDTO,
    OrganizationDTO,
    ThingDTO,
)
from bijou.core.ports.exceptions import EntityNotFoundError
from bijou.core.ports.repository import IGraphRepository


class SqlAlchemyGraphRepository(IGraphRepository):
    """SQLAlchemy 2.0 repository adapter supporting SQLite (WAL) and PostgreSQL.

    <reasoning>
    1. Shared state identified: SQLite database file / connection pool under concurrent API requests.
    2. Concurrency model: SQLite WAL mode + threading.RLock around write transactions to eliminate
       'database is locked' race conditions under high thread contention.
    3. Resource lifecycle: Context-managed Session blocks with guaranteed rollback on error and
       close in finally block.
    </reasoning>
    """

    def __init__(self, db_uri: str = "sqlite:///./bijou_graph.db") -> None:
        self._db_uri = db_uri
        self._write_lock = threading.RLock()

        connect_args: dict[str, Any] = {}
        if db_uri.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            connect_args["timeout"] = 30.0

        self._engine = create_engine(
            db_uri,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

        if "sqlite" in db_uri:
            @event.listens_for(self._engine, "connect")
            def _set_sqlite_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
                cursor.execute("PRAGMA foreign_keys=ON;")
                cursor.close()

        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    def close(self) -> None:
        """Dispose of underlying connection pool."""
        self._engine.dispose()

    # --- Organization CRUD ---
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(OrganizationRecord, org.id)
                if record is None:
                    record = OrganizationRecord(id=org.id)
                    session.add(record)
                record.name = org.name
                record.echelon_level = org.echelon_level
                record.mission_statement = org.mission_statement
                record.parent_org_id = org.parent_org_id
                record.peer_org_ids = org.peer_org_ids
                record.tags = org.tags
                session.commit()
                return self._to_org_dto(record)
            except Exception:
                session.rollback()
                raise

    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        with self._session_factory() as session:
            record = session.get(OrganizationRecord, org_id)
            return self._to_org_dto(record) if record else None

    def list_organizations(self) -> list[OrganizationDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(OrganizationRecord).order_by(OrganizationRecord.id)).all()
            return [self._to_org_dto(r) for r in records]

    # --- Concern CRUD ---
    def upsert_concern(self, concern: ConcernDTO) -> ConcernDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(ConcernRecord, concern.id)
                if record is None:
                    record = ConcernRecord(id=concern.id)
                    session.add(record)
                record.name = concern.name
                record.description = concern.description
                record.owner_org_id = concern.owner_org_id
                record.parent_concern_id = concern.parent_concern_id
                record.priority = concern.priority
                record.target_metric_sla = concern.target_metric_sla
                session.commit()
                return self._to_concern_dto(record)
            except Exception:
                session.rollback()
                raise

    def get_concern(self, concern_id: str) -> ConcernDTO | None:
        with self._session_factory() as session:
            record = session.get(ConcernRecord, concern_id)
            return self._to_concern_dto(record) if record else None

    def list_concerns(self) -> list[ConcernDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(ConcernRecord).order_by(ConcernRecord.id)).all()
            return [self._to_concern_dto(r) for r in records]

    # --- Thing & Milestone CRUD ---
    def upsert_thing(self, thing: ThingDTO) -> ThingDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(ThingRecord, thing.id)
                if record is None:
                    record = ThingRecord(id=thing.id)
                    session.add(record)
                record.name = thing.name
                record.description = thing.description
                record.lifecycle = thing.lifecycle.value
                record.owner_org_id = thing.owner_org_id
                record.estimated_cost = thing.estimated_cost
                record.risk_factor = thing.risk_factor

                # Replace child milestones
                session.execute(delete(MilestoneRecord).where(MilestoneRecord.thing_id == thing.id))
                for ms in thing.milestones:
                    ms_rec = MilestoneRecord(
                        id=ms.id,
                        thing_id=thing.id,
                        sequence_index=ms.sequence_index,
                        name=ms.name,
                        description=ms.description,
                        target_date=ms.target_date,
                        actual_date=ms.actual_date,
                        status=ms.status.value,
                        cost_delta=ms.cost_delta,
                        lane=ms.lane,
                        trl=ms.trl,
                    )
                    session.add(ms_rec)

                session.commit()
                return self.get_thing(thing.id)  # type: ignore[return-value]
            except Exception:
                session.rollback()
                raise

    def get_thing(self, thing_id: str) -> ThingDTO | None:
        with self._session_factory() as session:
            record = session.get(ThingRecord, thing_id)
            return self._to_thing_dto(record) if record else None

    def list_things(self) -> list[ThingDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(ThingRecord).order_by(ThingRecord.id)).all()
            return [self._to_thing_dto(r) for r in records]

    # --- Causal Gate CRUD ---
    def upsert_causal_gate(self, gate: CausalGateDTO) -> CausalGateDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(CausalGateRecord, gate.id)
                if record is None:
                    record = CausalGateRecord(id=gate.id)
                    session.add(record)
                record.name = gate.name
                record.mechanism = gate.mechanism.value
                record.threshold_k = gate.threshold_k
                record.contributors = [c.model_dump(mode="json", by_alias=True) for c in gate.contributors]
                session.commit()
                return self._to_gate_dto(record)
            except Exception:
                session.rollback()
                raise

    def get_causal_gate(self, gate_id: str) -> CausalGateDTO | None:
        with self._session_factory() as session:
            record = session.get(CausalGateRecord, gate_id)
            return self._to_gate_dto(record) if record else None

    def list_causal_gates(self) -> list[CausalGateDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(CausalGateRecord).order_by(CausalGateRecord.id)).all()
            return [self._to_gate_dto(r) for r in records]

    # --- Effect CRUD ---
    def upsert_effect(self, effect: EffectDTO) -> EffectDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(EffectRecord, effect.id)
                if record is None:
                    record = EffectRecord(id=effect.id)
                    session.add(record)
                record.name = effect.name
                record.description = effect.description
                record.tier = effect.tier.value
                record.causal_gate_id = effect.causal_gate_id
                record.accumulator = effect.accumulator.value
                record.observed_value = effect.observed_value
                record.target_threshold = effect.target_threshold
                record.satisfies_concerns = [c.model_dump(mode="json", by_alias=True) for c in effect.satisfies_concerns]
                record.federation_spec = (
                    effect.federation_spec.model_dump(mode="json", by_alias=True)
                    if effect.federation_spec
                    else None
                )
                session.commit()
                return self._to_effect_dto(record)
            except Exception:
                session.rollback()
                raise

    def get_effect(self, effect_id: str) -> EffectDTO | None:
        with self._session_factory() as session:
            record = session.get(EffectRecord, effect_id)
            return self._to_effect_dto(record) if record else None

    def list_effects(self) -> list[EffectDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(EffectRecord).order_by(EffectRecord.id)).all()
            return [self._to_effect_dto(r) for r in records]

    # --- Edge CRUD ---
    def upsert_edge(self, edge: GraphEdgeDTO) -> GraphEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                record = session.get(EdgeRecord, edge.id)
                if record is None:
                    record = EdgeRecord(id=edge.id)
                    session.add(record)
                record.source_id = edge.source_id
                record.target_id = edge.target_id
                record.relationship = edge.relationship.value
                record.weight = edge.weight
                record.source_milestone_id = edge.source_milestone_id
                record.target_milestone_id = edge.target_milestone_id
                record.effective_start = edge.effective_start
                record.effective_end = edge.effective_end
                session.commit()
                return self._to_edge_dto(record)
            except Exception:
                session.rollback()
                raise

    def get_edge(self, edge_id: str) -> GraphEdgeDTO | None:
        with self._session_factory() as session:
            record = session.get(EdgeRecord, edge_id)
            return self._to_edge_dto(record) if record else None

    def list_edges(self) -> list[GraphEdgeDTO]:
        with self._session_factory() as session:
            records = session.scalars(select(EdgeRecord).order_by(EdgeRecord.id)).all()
            return [self._to_edge_dto(r) for r in records]

    # --- Entity Deletion ---
    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        with self._write_lock, self._session_factory() as session:
            try:
                table_map = {
                    "organization": OrganizationRecord,
                    "concern": ConcernRecord,
                    "thing": ThingRecord,
                    "causal_gate": CausalGateRecord,
                    "effect": EffectRecord,
                    "edge": EdgeRecord,
                }
                model_cls = table_map.get(entity_type.lower())
                if not model_cls:
                    return False
                record = session.get(model_cls, entity_id)
                if not record:
                    return False
                session.delete(record)
                session.commit()
                return True
            except Exception:
                session.rollback()
                raise

    # --- Manifest Import / Export ---
    def export_manifest(self) -> BijouManifestDTO:
        return BijouManifestDTO(
            organizations=self.list_organizations(),
            concerns=self.list_concerns(),
            things=self.list_things(),
            causal_gates=self.list_causal_gates(),
            effects=self.list_effects(),
            edges=self.list_edges(),
        )

    def import_manifest(self, manifest: BijouManifestDTO, replace_all: bool = False) -> dict[str, int]:
        with self._write_lock, self._session_factory() as session:
            try:
                # 1. Referential integrity validation across edges and node IDs
                existing_nodes: set[str] = set()
                if not replace_all:
                    for tbl in [OrganizationRecord, ConcernRecord, ThingRecord, CausalGateRecord, EffectRecord]:
                        existing_nodes.update(session.scalars(select(tbl.id)).all())

                manifest_nodes: set[str] = {
                    *(o.id for o in manifest.organizations),
                    *(c.id for c in manifest.concerns),
                    *(t.id for t in manifest.things),
                    *(g.id for g in manifest.causal_gates),
                    *(e.id for e in manifest.effects),
                }
                all_valid_nodes = existing_nodes | manifest_nodes

                for edge in manifest.edges:
                    if edge.source_id not in all_valid_nodes:
                        raise EntityNotFoundError(f"Dangling edge source_id '{edge.source_id}' on edge '{edge.id}'")
                    if edge.target_id not in all_valid_nodes:
                        raise EntityNotFoundError(f"Dangling edge target_id '{edge.target_id}' on edge '{edge.id}'")

                # 2. If replace_all, clear existing tables in dependency order
                if replace_all:
                    session.execute(delete(EdgeRecord))
                    session.execute(delete(EffectRecord))
                    session.execute(delete(CausalGateRecord))
                    session.execute(delete(MilestoneRecord))
                    session.execute(delete(ThingRecord))
                    session.execute(delete(ConcernRecord))
                    session.execute(delete(OrganizationRecord))

                # 3. Insert / update organizations
                for o in manifest.organizations:
                    rec = session.get(OrganizationRecord, o.id) or OrganizationRecord(id=o.id)
                    rec.name = o.name
                    rec.echelon_level = o.echelon_level
                    rec.mission_statement = o.mission_statement
                    rec.parent_org_id = o.parent_org_id
                    rec.peer_org_ids = o.peer_org_ids
                    rec.tags = o.tags
                    session.add(rec)

                # 4. Insert / update concerns
                for c in manifest.concerns:
                    c_rec = session.get(ConcernRecord, c.id) or ConcernRecord(id=c.id)
                    c_rec.name = c.name
                    c_rec.description = c.description
                    c_rec.owner_org_id = c.owner_org_id
                    c_rec.parent_concern_id = c.parent_concern_id
                    c_rec.priority = c.priority
                    c_rec.target_metric_sla = c.target_metric_sla
                    session.add(c_rec)

                # 5. Insert / update things and milestones
                for t in manifest.things:
                    t_rec = session.get(ThingRecord, t.id) or ThingRecord(id=t.id)
                    t_rec.name = t.name
                    t_rec.description = t.description
                    t_rec.lifecycle = t.lifecycle.value
                    t_rec.owner_org_id = t.owner_org_id
                    t_rec.estimated_cost = t.estimated_cost
                    t_risk = t.risk_factor
                    t_rec.risk_factor = t_risk
                    session.add(t_rec)

                    session.execute(delete(MilestoneRecord).where(MilestoneRecord.thing_id == t.id))
                    for ms in t.milestones:
                        session.add(
                            MilestoneRecord(
                                id=ms.id,
                                thing_id=t.id,
                                sequence_index=ms.sequence_index,
                                name=ms.name,
                                description=ms.description,
                                target_date=ms.target_date,
                                actual_date=ms.actual_date,
                                status=ms.status.value,
                                cost_delta=ms.cost_delta,
                                lane=ms.lane,
                                trl=ms.trl,
                            )
                        )

                # 6. Insert / update causal gates
                for g in manifest.causal_gates:
                    g_rec = session.get(CausalGateRecord, g.id) or CausalGateRecord(id=g.id)
                    g_rec.name = g.name
                    g_rec.mechanism = g.mechanism.value
                    g_rec.threshold_k = g.threshold_k
                    g_rec.contributors = [contrib.model_dump(mode="json", by_alias=True) for contrib in g.contributors]
                    session.add(g_rec)

                # 7. Insert / update effects
                for e in manifest.effects:
                    e_rec = session.get(EffectRecord, e.id) or EffectRecord(id=e.id)
                    e_rec.name = e.name
                    e_rec.description = e.description
                    e_rec.tier = e.tier.value
                    e_rec.causal_gate_id = e.causal_gate_id
                    e_rec.accumulator = e.accumulator.value
                    e_rec.observed_value = e.observed_value
                    e_rec.target_threshold = e.target_threshold
                    e_rec.satisfies_concerns = [s.model_dump(mode="json", by_alias=True) for s in e.satisfies_concerns]
                    e_rec.federation_spec = (
                        e.federation_spec.model_dump(mode="json", by_alias=True)
                        if e.federation_spec
                        else None
                    )
                    session.add(e_rec)

                # 8. Insert / update edges
                for edge in manifest.edges:
                    ed_rec = session.get(EdgeRecord, edge.id) or EdgeRecord(id=edge.id)
                    ed_rec.source_id = edge.source_id
                    ed_rec.target_id = edge.target_id
                    ed_rec.relationship = edge.relationship.value
                    ed_rec.weight = edge.weight
                    ed_rec.source_milestone_id = edge.source_milestone_id
                    ed_rec.target_milestone_id = edge.target_milestone_id
                    ed_rec.effective_start = edge.effective_start
                    ed_rec.effective_end = edge.effective_end
                    session.add(ed_rec)

                session.commit()
                return {
                    "organizations": len(manifest.organizations),
                    "concerns": len(manifest.concerns),
                    "things": len(manifest.things),
                    "causal_gates": len(manifest.causal_gates),
                    "effects": len(manifest.effects),
                    "edges": len(manifest.edges),
                }
            except Exception:
                session.rollback()
                raise

    def upsert_decision_log(self, entry: DecisionLogEntryDTO) -> DecisionLogEntryDTO:
        with self._write_lock, self._session_scope() as session:
            record = session.get(DecisionLogRecord, entry.id)
            if record:
                record.target_milestone_id = entry.target_milestone_id
                record.author = entry.author
                record.justification = entry.justification
                record.timestamp = entry.timestamp
            else:
                record = DecisionLogRecord(
                    id=entry.id,
                    target_milestone_id=entry.target_milestone_id,
                    author=entry.author,
                    justification=entry.justification,
                    timestamp=entry.timestamp,
                )
                session.add(record)
            session.commit()
            return entry

    def list_decision_logs(self, target_milestone_id: str | None = None) -> list[DecisionLogEntryDTO]:
        with self._session_scope() as session:
            stmt = select(DecisionLogRecord)
            if target_milestone_id:
                stmt = stmt.where(DecisionLogRecord.target_milestone_id == target_milestone_id)
            stmt = stmt.order_by(DecisionLogRecord.timestamp.desc())
            records = session.scalars(stmt).all()
            return [
                DecisionLogEntryDTO(
                    id=r.id,
                    target_milestone_id=r.target_milestone_id,
                    author=r.author,
                    justification=r.justification,
                    timestamp=r.timestamp,
                )
                for r in records
            ]

    # --- DTO Conversion Helpers ---
    @staticmethod
    def _to_org_dto(record: OrganizationRecord) -> OrganizationDTO:
        return OrganizationDTO(
            id=record.id,
            name=record.name,
            echelon_level=record.echelon_level,
            mission_statement=record.mission_statement,
            parent_org_id=record.parent_org_id,
            peer_org_ids=list(record.peer_org_ids or []),
            tags=list(record.tags or []),
        )

    @staticmethod
    def _to_concern_dto(record: ConcernRecord) -> ConcernDTO:
        return ConcernDTO(
            id=record.id,
            name=record.name,
            description=record.description,
            owner_org_id=record.owner_org_id,
            parent_concern_id=record.parent_concern_id,
            priority=record.priority,
            target_metric_sla=record.target_metric_sla,
        )

    @staticmethod
    def _to_thing_dto(record: ThingRecord) -> ThingDTO:
        milestones = [
            MilestoneDTO(
                id=ms.id,
                thing_id=ms.thing_id,
                sequence_index=ms.sequence_index,
                name=ms.name,
                description=ms.description,
                target_date=ms.target_date,
                actual_date=ms.actual_date,
                status=MilestoneStatus(ms.status),
                cost_delta=ms.cost_delta,
                lane=ms.lane,
                trl=ms.trl,
            )
            for ms in (record.milestones or [])
        ]
        return ThingDTO(
            id=record.id,
            name=record.name,
            description=record.description,
            lifecycle=LifecycleStatus(record.lifecycle),
            owner_org_id=record.owner_org_id,
            estimated_cost=record.estimated_cost,
            risk_factor=record.risk_factor,
            milestones=milestones,
        )

    @staticmethod
    def _to_gate_dto(record: CausalGateRecord) -> CausalGateDTO:
        contributors = [
            CausalContributorDTO.model_validate(c) for c in (record.contributors or [])
        ]
        return CausalGateDTO(
            id=record.id,
            name=record.name,
            mechanism=CausalMechanismType(record.mechanism),
            threshold_k=record.threshold_k,
            contributors=contributors,
        )

    @staticmethod
    def _to_effect_dto(record: EffectRecord) -> EffectDTO:
        satisfies = [
            ConcernSatisfactionLinkDTO.model_validate(s)
            for s in (record.satisfies_concerns or [])
        ]
        fed_spec = (
            FederationSpecDTO.model_validate(record.federation_spec)
            if record.federation_spec
            else None
        )
        return EffectDTO(
            id=record.id,
            name=record.name,
            description=record.description,
            tier=EffectTier(record.tier),
            causal_gate_id=record.causal_gate_id,
            accumulator=AccumulatorPattern(record.accumulator),
            observed_value=record.observed_value,
            target_threshold=record.target_threshold,
            satisfies_concerns=satisfies,
            federation_spec=fed_spec,
        )

    @staticmethod
    def _to_edge_dto(record: EdgeRecord) -> GraphEdgeDTO:
        return GraphEdgeDTO(
            id=record.id,
            source_id=record.source_id,
            target_id=record.target_id,
            relationship=RelationshipType(record.relationship),
            weight=record.weight,
            source_milestone_id=record.source_milestone_id,
            target_milestone_id=record.target_milestone_id,
            effective_start=record.effective_start,
            effective_end=record.effective_end,
        )
