"""Tests for BijouOrchestrationService perspective permissions, skill mismatch risk creation, and commit flow."""

from pathlib import Path

import pytest

from bijou.adapters.db import SqlAlchemyGraphRepository
from bijou.adapters.llm import AuraRouterAdapter
from bijou.adapters.telemetry import DuckDbTelemetryStore
from bijou.core.contracts import (
    AccessMode,
    BillOfEffortsSimulationRequestDTO,
    EffortDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    SimulatedPoolAllocationDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine
from bijou.core.ports import AccessContext, PermissionDeniedError
from bijou.services import BijouOrchestrationService


def _make_service(tmp_path: Path) -> BijouOrchestrationService:
    repo = SqlAlchemyGraphRepository(db_uri=f"sqlite:///{tmp_path}/orch.db")
    tel = DuckDbTelemetryStore(db_path=str(tmp_path / "orch.duckdb"))
    llm = AuraRouterAdapter(aurarouter_url="http://offline.invalid:9999")
    engine = InMemoryGraphProjectionEngine()
    svc = BijouOrchestrationService(
        repository=repo,
        projection_engine=engine,
        telemetry_store=tel,
        reasoning_broker=llm,
    )
    svc.initialize()
    return svc


def test_orchestrator_enforces_perspective_seam_and_auto_registers_skill_mismatch_risk(tmp_path: Path) -> None:
    svc = _make_service(tmp_path)
    svc.upsert_organization(OrganizationDTO(id="org-a", name="Org A", is_managed=True))
    svc.upsert_organization(OrganizationDTO(id="org-b", name="Org B", is_managed=True))
    svc.upsert_resource_pool(
        ResourcePoolDTO(
            id="pool-a-staff",
            org_id="org-a",
            name="Org A Engineers",
            category=ResourceCategory.STAFF,
            capacity=3.0,
            unit="FTE",
            skill_tag="General Engineer",
        )
    )
    svc.upsert_effort(
        EffortDTO(
            id="eff-dsp",
            name="RF Filter",
            resource_requirements=[
                ResourceRequirementDTO(
                    id="req-rf",
                    category=ResourceCategory.STAFF,
                    label="RF Specialist",
                    quantity=1.0,
                    unit="FTE",
                    required_skill="TS/SCI RF DSP Engineer",
                    is_generic=False,
                )
            ],
            mitigators=[
                MitigatorDTO(id="mit-1", effort_id="eff-dsp", name="Tooling Assist", slip_reduction_days=10)
            ],
        )
    )

    owner_b_ctx = AccessContext(mode=AccessMode.MANAGED_ORG_OWNER, active_org_id="org-b")
    with pytest.raises(PermissionDeniedError):
        svc.upsert_org_effort_edge(
            OrgEffortEdgeDTO(org_id="org-a", effort_id="eff-dsp", allocation_amount=1.0),
            context=owner_b_ctx,
        )

    owner_a_ctx = AccessContext(mode=AccessMode.MANAGED_ORG_OWNER, active_org_id="org-a")
    svc.upsert_org_effort_edge(
        OrgEffortEdgeDTO(
            org_id="org-a",
            effort_id="eff-dsp",
            resourcing_type=ResourceCategory.STAFF,
            resource_pool_id="pool-a-staff",
            requirement_id="req-rf",
            allocation_amount=1.0,
            allocation_unit="FTE",
            assigned_skill="General Engineer",
            is_generic=False,
        ),
        context=owner_a_ctx,
        human_slip_penalty_days=40,
    )

    updated = svc.get_effort("eff-dsp")
    assert updated is not None
    assert any(r.is_skill_mismatch_risk and r.potential_slip_days == 40 for r in updated.risks)

    # Commit Bill of Efforts exercising mitigator
    svc.commit_bill_of_efforts(
        BillOfEffortsSimulationRequestDTO(
            toggle_mitigators={"mit-1": True},
            add_allocations=[
                SimulatedPoolAllocationDTO(
                    org_id="org-a",
                    effort_id="eff-dsp",
                    resourcing_type=ResourceCategory.MONEY,
                    amount=50000.0,
                    unit="USD",
                    is_generic=True,
                )
            ],
        ),
        context=owner_a_ctx,
    )
    committed = svc.get_effort("eff-dsp")
    assert committed is not None
    assert committed.mitigators[0].is_exercised is True
