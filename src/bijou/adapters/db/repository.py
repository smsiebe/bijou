"""SQLAlchemy 2.0 repository implementing IGraphRepository with SQLite WAL thread-safety."""

import threading
from datetime import timezone
from typing import Any

from sqlalchemy import create_engine, delete, event, inspect, select, text
from sqlalchemy.orm import sessionmaker

from bijou.adapters.db.tables import (
    Base,
    DecisionLogRecord,
    EffortEffortEdgeRecord,
    EffortInterestEdgeRecord,
    EffortRecord,
    InterestInterestEdgeRecord,
    InterestRecord,
    OrgEffortEdgeRecord,
    OrgInterestEdgeRecord,
    OrgOrgEdgeRecord,
    OrganizationRecord,
    ResourcePoolRecord,
)
from bijou.core.contracts.enums import (
    BlockingMode,
    ConfidenceLevel,
    EffortInterestRelationType,
    EffortState,
    InterestInterestRelationType,
    InterestKind,
    OrgInterestStance,
    OrgOrgRelationType,
    ResourceCategory,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    DecisionLogEntryDTO,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    InterestInterestEdgeDTO,
    MitigatorDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    OrganizationDTO,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
)
from bijou.core.ports.exceptions import EntityNotFoundError
from bijou.core.ports.repository import IGraphRepository


class SqlAlchemyGraphRepository(IGraphRepository):
    """Thread-safe SQLAlchemy repository supporting SQLite (WAL) and PostgreSQL."""

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

        # Check for legacy v1 schema on existing DB files and upgrade cleanly to v2
        inspector = inspect(self._engine)
        existing_tables = set(inspector.get_table_names())
        if "organizations" in existing_tables and "efforts" not in existing_tables:
            with self._engine.begin() as conn:
                conn.execute(text("PRAGMA foreign_keys=OFF;")) if "sqlite" in db_uri else None
                for tbl in reversed(inspector.get_sorted_table_and_fkc_names()):
                    t_name = tbl[0]
                    if t_name:
                        conn.execute(text(f'DROP TABLE IF EXISTS "{t_name}"'))
                conn.execute(text("PRAGMA foreign_keys=ON;")) if "sqlite" in db_uri else None

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

    # --- Converters ---
    @staticmethod
    def _to_org_dto(rec: OrganizationRecord) -> OrganizationDTO:
        return OrganizationDTO(
            id=rec.id,
            name=rec.name,
            description=rec.description,
            echelon_level=rec.echelon_level,
            is_managed=rec.is_managed,
            tags=list(rec.tags or []),
        )

    @staticmethod
    def _to_pool_dto(rec: ResourcePoolRecord) -> ResourcePoolDTO:
        return ResourcePoolDTO(
            id=rec.id,
            org_id=rec.org_id,
            name=rec.name,
            category=ResourceCategory(rec.category),
            capacity=rec.capacity,
            unit=rec.unit,
            skill_tag=rec.skill_tag,
            restricted_interest_ids=list(rec.restricted_interest_ids or []),
            description=rec.description,
        )

    @staticmethod
    def _to_interest_dto(rec: InterestRecord) -> InterestDTO:
        return InterestDTO(
            id=rec.id,
            name=rec.name,
            description=rec.description,
            interest_kind=InterestKind(rec.interest_kind),
            start_date=rec.start_date,
            end_date=rec.end_date,
        )

    @staticmethod
    def _to_effort_dto(rec: EffortRecord) -> EffortDTO:
        reqs = [ResourceRequirementDTO.model_validate(r) for r in (rec.resource_requirements or [])]
        risks = [RiskDTO.model_validate(r) for r in (rec.risks or [])]
        mits = [MitigatorDTO.model_validate(m) for m in (rec.mitigators or [])]
        return EffortDTO(
            id=rec.id,
            name=rec.name,
            description=rec.description,
            state=EffortState(rec.state),
            start_date=rec.start_date,
            end_date=rec.end_date,
            estimated_duration_days=rec.estimated_duration_days,
            resource_requirements=reqs,
            risks=risks,
            mitigators=mits,
        )

    @staticmethod
    def _to_oo_dto(rec: OrgOrgEdgeRecord) -> OrgOrgEdgeDTO:
        return OrgOrgEdgeDTO(
            id=rec.id,
            source_org_id=rec.source_org_id,
            target_org_id=rec.target_org_id,
            relation_type=OrgOrgRelationType(rec.relation_type),
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    @staticmethod
    def _to_oi_dto(rec: OrgInterestEdgeRecord) -> OrgInterestEdgeDTO:
        return OrgInterestEdgeDTO(
            id=rec.id,
            org_id=rec.org_id,
            interest_id=rec.interest_id,
            stance=OrgInterestStance(rec.stance),
            priority_rank=rec.priority_rank,
            allow_hierarchy_inheritance=rec.allow_hierarchy_inheritance,
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    @staticmethod
    def _to_ii_dto(rec: InterestInterestEdgeRecord) -> InterestInterestEdgeDTO:
        return InterestInterestEdgeDTO(
            id=rec.id,
            parent_interest_id=rec.parent_interest_id,
            child_interest_id=rec.child_interest_id,
            relation_type=InterestInterestRelationType(rec.relation_type),
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    @staticmethod
    def _to_oe_dto(rec: OrgEffortEdgeRecord) -> OrgEffortEdgeDTO:
        return OrgEffortEdgeDTO(
            id=rec.id,
            org_id=rec.org_id,
            effort_id=rec.effort_id,
            resourcing_type=ResourceCategory(rec.resourcing_type),
            resource_pool_id=rec.resource_pool_id,
            requirement_id=rec.requirement_id,
            allocation_amount=rec.allocation_amount,
            allocation_unit=rec.allocation_unit,
            assigned_skill=rec.assigned_skill,
            is_generic=rec.is_generic,
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    @staticmethod
    def _to_ei_dto(rec: EffortInterestEdgeRecord) -> EffortInterestEdgeDTO:
        return EffortInterestEdgeDTO(
            id=rec.id,
            effort_id=rec.effort_id,
            interest_id=rec.interest_id,
            relation_type=EffortInterestRelationType(rec.relation_type),
            impact_weight=rec.impact_weight,
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    @staticmethod
    def _to_ee_dto(rec: EffortEffortEdgeRecord) -> EffortEffortEdgeDTO:
        return EffortEffortEdgeDTO(
            id=rec.id,
            source_effort_id=rec.source_effort_id,
            target_effort_id=rec.target_effort_id,
            blocking_mode=BlockingMode(rec.blocking_mode),
            dependency_degree=rec.dependency_degree,
            confidence=ConfidenceLevel(rec.confidence),
            provenance_note=rec.provenance_note,
            effective_start=rec.effective_start,
            effective_end=rec.effective_end,
        )

    # --- Organizations ---
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(OrganizationRecord, org.id) or OrganizationRecord(id=org.id)
                rec.name = org.name
                rec.description = org.description
                rec.echelon_level = org.echelon_level
                rec.is_managed = org.is_managed
                rec.tags = list(org.tags)
                session.add(rec)
                session.commit()
                return org
            except Exception:
                session.rollback()
                raise

    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        with self._session_factory() as session:
            rec = session.get(OrganizationRecord, org_id)
            return self._to_org_dto(rec) if rec else None

    def list_organizations(self) -> list[OrganizationDTO]:
        with self._session_factory() as session:
            rows = session.scalars(select(OrganizationRecord).order_by(OrganizationRecord.name)).all()
            return [self._to_org_dto(r) for r in rows]

    # --- Resource Pools ---
    def upsert_resource_pool(self, pool: ResourcePoolDTO) -> ResourcePoolDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(ResourcePoolRecord, pool.id) or ResourcePoolRecord(id=pool.id)
                rec.org_id = pool.org_id
                rec.name = pool.name
                rec.category = pool.category.value
                rec.capacity = pool.capacity
                rec.unit = pool.unit
                rec.skill_tag = pool.skill_tag
                rec.restricted_interest_ids = list(pool.restricted_interest_ids)
                rec.description = pool.description
                session.add(rec)
                session.commit()
                return pool
            except Exception:
                session.rollback()
                raise

    def get_resource_pool(self, pool_id: str) -> ResourcePoolDTO | None:
        with self._session_factory() as session:
            rec = session.get(ResourcePoolRecord, pool_id)
            return self._to_pool_dto(rec) if rec else None

    def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePoolDTO]:
        with self._session_factory() as session:
            stmt = select(ResourcePoolRecord)
            if org_id:
                stmt = stmt.where(ResourcePoolRecord.org_id == org_id)
            rows = session.scalars(stmt.order_by(ResourcePoolRecord.name)).all()
            return [self._to_pool_dto(r) for r in rows]

    # --- Interests ---
    def upsert_interest(self, interest: InterestDTO) -> InterestDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(InterestRecord, interest.id) or InterestRecord(id=interest.id)
                rec.name = interest.name
                rec.description = interest.description
                rec.interest_kind = interest.interest_kind.value
                rec.start_date = interest.start_date
                rec.end_date = interest.end_date
                session.add(rec)
                session.commit()
                return interest
            except Exception:
                session.rollback()
                raise

    def get_interest(self, interest_id: str) -> InterestDTO | None:
        with self._session_factory() as session:
            rec = session.get(InterestRecord, interest_id)
            return self._to_interest_dto(rec) if rec else None

    def list_interests(self) -> list[InterestDTO]:
        with self._session_factory() as session:
            rows = session.scalars(select(InterestRecord).order_by(InterestRecord.name)).all()
            return [self._to_interest_dto(r) for r in rows]

    # --- Efforts ---
    def upsert_effort(self, effort: EffortDTO) -> EffortDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(EffortRecord, effort.id) or EffortRecord(id=effort.id)
                rec.name = effort.name
                rec.description = effort.description
                rec.state = effort.state.value
                rec.start_date = effort.start_date
                rec.end_date = effort.end_date
                rec.estimated_duration_days = effort.estimated_duration_days
                rec.resource_requirements = [r.model_dump(mode="json") for r in effort.resource_requirements]
                rec.risks = [r.model_dump(mode="json") for r in effort.risks]
                rec.mitigators = [m.model_dump(mode="json") for m in effort.mitigators]
                session.add(rec)
                session.commit()
                return effort
            except Exception:
                session.rollback()
                raise

    def get_effort(self, effort_id: str) -> EffortDTO | None:
        with self._session_factory() as session:
            rec = session.get(EffortRecord, effort_id)
            return self._to_effort_dto(rec) if rec else None

    def list_efforts(self) -> list[EffortDTO]:
        with self._session_factory() as session:
            rows = session.scalars(select(EffortRecord).order_by(EffortRecord.name)).all()
            return [self._to_effort_dto(r) for r in rows]

    # --- Six Typed Edges ---
    def upsert_org_org_edge(self, edge: OrgOrgEdgeDTO) -> OrgOrgEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(OrgOrgEdgeRecord, edge.id) or OrgOrgEdgeRecord(id=edge.id)
                rec.source_org_id = edge.source_org_id
                rec.target_org_id = edge.target_org_id
                rec.relation_type = edge.relation_type.value
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def upsert_org_interest_edge(self, edge: OrgInterestEdgeDTO) -> OrgInterestEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(OrgInterestEdgeRecord, edge.id) or OrgInterestEdgeRecord(id=edge.id)
                rec.org_id = edge.org_id
                rec.interest_id = edge.interest_id
                rec.stance = edge.stance.value
                rec.priority_rank = edge.priority_rank
                rec.allow_hierarchy_inheritance = edge.allow_hierarchy_inheritance
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def upsert_interest_interest_edge(self, edge: InterestInterestEdgeDTO) -> InterestInterestEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(InterestInterestEdgeRecord, edge.id) or InterestInterestEdgeRecord(id=edge.id)
                rec.parent_interest_id = edge.parent_interest_id
                rec.child_interest_id = edge.child_interest_id
                rec.relation_type = edge.relation_type.value
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def upsert_org_effort_edge(self, edge: OrgEffortEdgeDTO) -> OrgEffortEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(OrgEffortEdgeRecord, edge.id) or OrgEffortEdgeRecord(id=edge.id)
                rec.org_id = edge.org_id
                rec.effort_id = edge.effort_id
                rec.resourcing_type = edge.resourcing_type.value
                rec.resource_pool_id = edge.resource_pool_id
                rec.requirement_id = edge.requirement_id
                rec.allocation_amount = edge.allocation_amount
                rec.allocation_unit = edge.allocation_unit
                rec.assigned_skill = edge.assigned_skill
                rec.is_generic = edge.is_generic
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def upsert_effort_interest_edge(self, edge: EffortInterestEdgeDTO) -> EffortInterestEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(EffortInterestEdgeRecord, edge.id) or EffortInterestEdgeRecord(id=edge.id)
                rec.effort_id = edge.effort_id
                rec.interest_id = edge.interest_id
                rec.relation_type = edge.relation_type.value
                rec.impact_weight = edge.impact_weight
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def upsert_effort_effort_edge(self, edge: EffortEffortEdgeDTO) -> EffortEffortEdgeDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(EffortEffortEdgeRecord, edge.id) or EffortEffortEdgeRecord(id=edge.id)
                rec.source_effort_id = edge.source_effort_id
                rec.target_effort_id = edge.target_effort_id
                rec.blocking_mode = edge.blocking_mode.value
                rec.dependency_degree = edge.dependency_degree
                rec.confidence = edge.confidence.value
                rec.provenance_note = edge.provenance_note
                rec.effective_start = edge.effective_start
                rec.effective_end = edge.effective_end
                session.add(rec)
                session.commit()
                return edge
            except Exception:
                session.rollback()
                raise

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        model_map = {
            "organization": OrganizationRecord,
            "resource_pool": ResourcePoolRecord,
            "interest": InterestRecord,
            "effort": EffortRecord,
            "org_org_edge": OrgOrgEdgeRecord,
            "org_interest_edge": OrgInterestEdgeRecord,
            "interest_interest_edge": InterestInterestEdgeRecord,
            "org_effort_edge": OrgEffortEdgeRecord,
            "effort_interest_edge": EffortInterestEdgeRecord,
            "effort_effort_edge": EffortEffortEdgeRecord,
        }
        model_cls = model_map.get(entity_type)
        if model_cls is None:
            raise ValueError(f"Unsupported entity_type '{entity_type}'")

        with self._write_lock, self._session_factory() as session:
            try:
                rec = session.get(model_cls, entity_id)
                if rec is None:
                    raise EntityNotFoundError(f"{entity_type} '{entity_id}' not found")
                session.delete(rec)
                session.commit()
                return True
            except Exception:
                session.rollback()
                raise

    def export_manifest(self) -> BijouManifestDTO:
        with self._session_factory() as session:
            orgs = [self._to_org_dto(r) for r in session.scalars(select(OrganizationRecord)).all()]
            pools = [self._to_pool_dto(r) for r in session.scalars(select(ResourcePoolRecord)).all()]
            interests = [self._to_interest_dto(r) for r in session.scalars(select(InterestRecord)).all()]
            efforts = [self._to_effort_dto(r) for r in session.scalars(select(EffortRecord)).all()]
            oo_edges = [self._to_oo_dto(r) for r in session.scalars(select(OrgOrgEdgeRecord)).all()]
            oi_edges = [self._to_oi_dto(r) for r in session.scalars(select(OrgInterestEdgeRecord)).all()]
            ii_edges = [self._to_ii_dto(r) for r in session.scalars(select(InterestInterestEdgeRecord)).all()]
            oe_edges = [self._to_oe_dto(r) for r in session.scalars(select(OrgEffortEdgeRecord)).all()]
            ei_edges = [self._to_ei_dto(r) for r in session.scalars(select(EffortInterestEdgeRecord)).all()]
            ee_edges = [self._to_ee_dto(r) for r in session.scalars(select(EffortEffortEdgeRecord)).all()]

            return BijouManifestDTO(
                organizations=orgs,
                resource_pools=pools,
                interests=interests,
                efforts=efforts,
                org_org_edges=oo_edges,
                org_interest_edges=oi_edges,
                interest_interest_edges=ii_edges,
                org_effort_edges=oe_edges,
                effort_interest_edges=ei_edges,
                effort_effort_edges=ee_edges,
            )

    def import_manifest(self, manifest: BijouManifestDTO, replace_all: bool = False) -> dict[str, int]:
        with self._write_lock, self._session_factory() as session:
            try:
                if replace_all:
                    for tbl in (
                        EffortEffortEdgeRecord,
                        EffortInterestEdgeRecord,
                        OrgEffortEdgeRecord,
                        InterestInterestEdgeRecord,
                        OrgInterestEdgeRecord,
                        OrgOrgEdgeRecord,
                        ResourcePoolRecord,
                        EffortRecord,
                        InterestRecord,
                        OrganizationRecord,
                    ):
                        session.execute(delete(tbl))

                valid_org_ids = {o.id for o in manifest.organizations} | (
                    set(session.scalars(select(OrganizationRecord.id)).all()) if not replace_all else set()
                )

                for org in manifest.organizations:
                    session.merge(
                        OrganizationRecord(
                            id=org.id,
                            name=org.name,
                            description=org.description,
                            echelon_level=org.echelon_level,
                            is_managed=org.is_managed,
                            tags=list(org.tags),
                        )
                    )

                for pool in manifest.resource_pools:
                    if pool.org_id not in valid_org_ids:
                        raise ValueError(f"ResourcePool '{pool.id}' references unknown org '{pool.org_id}'")
                    session.merge(
                        ResourcePoolRecord(
                            id=pool.id,
                            org_id=pool.org_id,
                            name=pool.name,
                            category=pool.category.value,
                            capacity=pool.capacity,
                            unit=pool.unit,
                            skill_tag=pool.skill_tag,
                            restricted_interest_ids=list(pool.restricted_interest_ids),
                            description=pool.description,
                        )
                    )

                for intr in manifest.interests:
                    session.merge(
                        InterestRecord(
                            id=intr.id,
                            name=intr.name,
                            description=intr.description,
                            interest_kind=intr.interest_kind.value,
                            start_date=intr.start_date,
                            end_date=intr.end_date,
                        )
                    )

                for eff in manifest.efforts:
                    session.merge(
                        EffortRecord(
                            id=eff.id,
                            name=eff.name,
                            description=eff.description,
                            state=eff.state.value,
                            start_date=eff.start_date,
                            end_date=eff.end_date,
                            estimated_duration_days=eff.estimated_duration_days,
                            resource_requirements=[r.model_dump(mode="json") for r in eff.resource_requirements],
                            risks=[r.model_dump(mode="json") for r in eff.risks],
                            mitigators=[m.model_dump(mode="json") for m in eff.mitigators],
                        )
                    )

                for e in manifest.org_org_edges:
                    session.merge(
                        OrgOrgEdgeRecord(
                            id=e.id,
                            source_org_id=e.source_org_id,
                            target_org_id=e.target_org_id,
                            relation_type=e.relation_type.value,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                for e in manifest.org_interest_edges:
                    session.merge(
                        OrgInterestEdgeRecord(
                            id=e.id,
                            org_id=e.org_id,
                            interest_id=e.interest_id,
                            stance=e.stance.value,
                            priority_rank=e.priority_rank,
                            allow_hierarchy_inheritance=e.allow_hierarchy_inheritance,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                for e in manifest.interest_interest_edges:
                    session.merge(
                        InterestInterestEdgeRecord(
                            id=e.id,
                            parent_interest_id=e.parent_interest_id,
                            child_interest_id=e.child_interest_id,
                            relation_type=e.relation_type.value,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                for e in manifest.org_effort_edges:
                    session.merge(
                        OrgEffortEdgeRecord(
                            id=e.id,
                            org_id=e.org_id,
                            effort_id=e.effort_id,
                            resourcing_type=e.resourcing_type.value,
                            resource_pool_id=e.resource_pool_id,
                            requirement_id=e.requirement_id,
                            allocation_amount=e.allocation_amount,
                            allocation_unit=e.allocation_unit,
                            assigned_skill=e.assigned_skill,
                            is_generic=e.is_generic,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                for e in manifest.effort_interest_edges:
                    session.merge(
                        EffortInterestEdgeRecord(
                            id=e.id,
                            effort_id=e.effort_id,
                            interest_id=e.interest_id,
                            relation_type=e.relation_type.value,
                            impact_weight=e.impact_weight,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                for e in manifest.effort_effort_edges:
                    session.merge(
                        EffortEffortEdgeRecord(
                            id=e.id,
                            source_effort_id=e.source_effort_id,
                            target_effort_id=e.target_effort_id,
                            blocking_mode=e.blocking_mode.value,
                            dependency_degree=e.dependency_degree,
                            confidence=e.confidence.value,
                            provenance_note=e.provenance_note,
                            effective_start=e.effective_start,
                            effective_end=e.effective_end,
                        )
                    )

                session.commit()
                return {
                    "organizations": len(manifest.organizations),
                    "resource_pools": len(manifest.resource_pools),
                    "interests": len(manifest.interests),
                    "efforts": len(manifest.efforts),
                    "org_org_edges": len(manifest.org_org_edges),
                    "org_interest_edges": len(manifest.org_interest_edges),
                    "interest_interest_edges": len(manifest.interest_interest_edges),
                    "org_effort_edges": len(manifest.org_effort_edges),
                    "effort_interest_edges": len(manifest.effort_interest_edges),
                    "effort_effort_edges": len(manifest.effort_effort_edges),
                }
            except Exception:
                session.rollback()
                raise

    # --- Decision Provenance ---
    def upsert_decision_log(self, entry: DecisionLogEntryDTO) -> DecisionLogEntryDTO:
        with self._write_lock, self._session_factory() as session:
            try:
                rec = DecisionLogRecord(
                    id=entry.id,
                    target_effort_id=entry.target_effort_id,
                    author=entry.author,
                    justification=entry.justification,
                    timestamp=entry.timestamp,
                )
                session.merge(rec)
                session.commit()
                return entry
            except Exception:
                session.rollback()
                raise

    def list_decision_logs(self, target_effort_id: str | None = None) -> list[DecisionLogEntryDTO]:
        with self._session_factory() as session:
            stmt = select(DecisionLogRecord).order_by(DecisionLogRecord.timestamp.desc())
            if target_effort_id:
                stmt = stmt.where(DecisionLogRecord.target_effort_id == target_effort_id)
            rows = session.scalars(stmt).all()
            return [
                DecisionLogEntryDTO(
                    id=r.id,
                    target_effort_id=r.target_effort_id,
                    author=r.author,
                    justification=r.justification,
                    timestamp=r.timestamp.replace(tzinfo=timezone.utc) if r.timestamp.tzinfo is None else r.timestamp,
                )
                for r in rows
            ]
