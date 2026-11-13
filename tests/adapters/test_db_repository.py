"""Integration tests for SqlAlchemyGraphRepository (Bijou v2 relational persistence)."""

from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, text

from bijou.adapters.db import SqlAlchemyGraphRepository
from bijou.core.contracts import (
    BijouManifestDTO,
    ConfidenceLevel,
    DecisionLogEntryDTO,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortState,
    InterestDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
    RiskSeverity,
)


def test_sqlalchemy_repository_crud_and_atomic_manifest(tmp_path: Path) -> None:
    db_uri = f"sqlite:///{tmp_path}/v2_repo.db"
    repo = SqlAlchemyGraphRepository(db_uri=db_uri)
    try:
        org = OrganizationDTO(id="org-1", name="Space Cmd", is_managed=True, tags=["space"])
        repo.upsert_organization(org)
        assert repo.get_organization("org-1") is not None

        pool = ResourcePoolDTO(
            id="pool-1",
            org_id="org-1",
            name="Resiliency FY27",
            category=ResourceCategory.MONEY,
            capacity=500000.0,
            unit="USD",
            restricted_interest_ids=["intr-res"],
        )
        repo.upsert_resource_pool(pool)
        assert len(repo.list_resource_pools("org-1")) == 1

        intr = InterestDTO(id="intr-res", name="Resiliency")
        repo.upsert_interest(intr)

        eff = EffortDTO(
            id="eff-1",
            name="Optical Link",
            state=EffortState.IN_WORK,
            start_date=date(2026, 2, 1),
            resource_requirements=[
                ResourceRequirementDTO(
                    id="req-1",
                    category=ResourceCategory.STAFF,
                    label="DSP Eng",
                    quantity=1.0,
                    unit="FTE",
                    required_skill="TS/SCI RF DSP",
                    is_generic=False,
                )
            ],
            risks=[
                RiskDTO(
                    id="r-1",
                    effort_id="eff-1",
                    title="Test Risk",
                    severity=RiskSeverity.MEDIUM,
                    potential_slip_days=20,
                )
            ],
            mitigators=[
                MitigatorDTO(
                    id="m-1",
                    effort_id="eff-1",
                    risk_id="r-1",
                    name="Extra Testbed",
                    slip_reduction_days=15,
                )
            ],
        )
        repo.upsert_effort(eff)
        loaded_eff = repo.get_effort("eff-1")
        assert loaded_eff is not None
        assert len(loaded_eff.resource_requirements) == 1
        assert len(loaded_eff.risks) == 1
        assert len(loaded_eff.mitigators) == 1

        repo.upsert_org_effort_edge(
            OrgEffortEdgeDTO(
                id="oe-1",
                org_id="org-1",
                effort_id="eff-1",
                resourcing_type=ResourceCategory.MONEY,
                resource_pool_id="pool-1",
                allocation_amount=150000.0,
                allocation_unit="USD",
                confidence=ConfidenceLevel.CONFIRMED,
                provenance_note="POM line 42",
                is_generic=False,
            )
        )

        exported = repo.export_manifest()
        assert len(exported.organizations) == 1
        assert len(exported.efforts) == 1
        assert exported.org_effort_edges[0].provenance_note == "POM line 42"

        # Atomic replace_all manifest import
        new_manifest = BijouManifestDTO(
            organizations=[OrganizationDTO(id="org-2", name="Replaced Org")],
            efforts=[EffortDTO(id="eff-a", name="Replaced Effort"), EffortDTO(id="eff-b", name="Second")],
            effort_effort_edges=[EffortEffortEdgeDTO(source_effort_id="eff-a", target_effort_id="eff-b")],
        )
        counts = repo.import_manifest(new_manifest, replace_all=True)
        assert counts["organizations"] == 1
        assert repo.get_organization("org-1") is None
        assert repo.get_effort("eff-b") is not None

        repo.upsert_decision_log(
            DecisionLogEntryDTO(
                author="owner",
                justification="Committed portfolio rebalancing scenario",
                target_effort_id="eff-a",
            )
        )
        assert len(repo.list_decision_logs("eff-a")) == 1
    finally:
        repo.close()


def test_legacy_v1_schema_is_safely_replaced_by_v2_tables(tmp_path: Path) -> None:
    """Ensures lingering pre-v2 SQLite files reset cleanly without crashing."""
    db_file = tmp_path / "legacy.db"
    eng = create_engine(f"sqlite:///{db_file}")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE organizations (id TEXT PRIMARY KEY, name TEXT)"))
        conn.execute(text("CREATE TABLE things (id TEXT PRIMARY KEY, name TEXT)"))
    eng.dispose()

    repo = SqlAlchemyGraphRepository(db_uri=f"sqlite:///{db_file}")
    try:
        repo.upsert_effort(EffortDTO(id="eff-v2", name="Clean v2 Effort"))
        assert repo.get_effort("eff-v2") is not None
    finally:
        repo.close()
