"""Service and API integration tests verifying full wiring and middleware."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bijou.adapters.llm import AuraRouterAdapter
from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.core.contracts import (
    CausalContributorDTO,
    CausalGateDTO,
    CausalMechanismType,
    ConcernDTO,
    ConcernSatisfactionLinkDTO,
    EffectDTO,
    EffectTier,
    LifecycleStatus,
    MilestoneDTO,
    MilestoneStatus,
    OrganizationDTO,
    PerspectiveBriefingDTO,
    ThingDTO,
)
from bijou.core.ports.exceptions import ServiceUnavailableError


@pytest.fixture
def wired_client(tmp_path: Path) -> TestClient:
    """Fixture providing a TestClient backed by live isolated SQLite and DuckDB."""
    db_file = tmp_path / "test_wiring_graph.db"
    duckdb_file = tmp_path / "test_wiring_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        max_payload_bytes=1024,  # Small payload limit for testing
        enable_reasoning=False,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


def test_full_api_crud_triggers_projection_rebuild_and_briefing_update(wired_client: TestClient) -> None:
    """Creates entities via FastAPI TestClient, then queries perspective briefing and verifies non-zero ROI and concern coverage."""
    client = wired_client

    # 1. Create Organization
    org = OrganizationDTO(
        id="org-c2",
        name="C2 Directorate",
        echelon_level=1,
        mission_statement="Orchestrate tactical fires",
    )
    resp_org = client.post("/api/v1/organizations", json=org.model_dump(mode="json", by_alias=True))
    assert resp_org.status_code == 201

    # 2. Create Concern
    con = ConcernDTO(
        id="con-fires",
        name="Fires Latency < 30s",
        description="Fires sensor to shooter",
        owner_org_id="org-c2",
        priority=1.0,
    )
    resp_con = client.post("/api/v1/concerns", json=con.model_dump(mode="json", by_alias=True))
    assert resp_con.status_code == 201

    # 3. Create Thing and Milestone
    ms = MilestoneDTO(
        id="ms-f1",
        thing_id="th-f1",
        sequence_index=0,
        name="Fires Node Prototype",
        description="Lab test",
        target_date="2026-05-01",
        actual_date="2026-05-01",
        status=MilestoneStatus.ACHIEVED,
        lane="Tactical Fires",
        trl=7,
    )
    th = ThingDTO(
        id="th-f1",
        name="Automated Fires Controller",
        description="Tactical controller",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-c2",
        estimated_cost=100000.0,
        risk_factor=1.0,
        milestones=[ms],
    )
    resp_th = client.post("/api/v1/things", json=th.model_dump(mode="json", by_alias=True))
    assert resp_th.status_code == 201

    # 4. Create Causal Gate
    gate = CausalGateDTO(
        id="gate-f1",
        name="Fires Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-f1", milestone_id="ms-f1", contribution_weight=1.0)],
    )
    resp_gate = client.post("/api/v1/causal-gates", json=gate.model_dump(mode="json", by_alias=True))
    assert resp_gate.status_code == 201

    # 5. Create Effect satisfying Concern
    effect = EffectDTO(
        id="eff-f1",
        name="Fires Operational",
        description="Delivery",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-f1",
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-fires", weight=1.0)],
    )
    resp_eff = client.post("/api/v1/effects", json=effect.model_dump(mode="json", by_alias=True))
    assert resp_eff.status_code == 201

    # 6. Query Perspective Briefing
    resp_briefing = client.get("/api/v1/views/perspectives/org-c2?as_of_date=2026-06-01")
    assert resp_briefing.status_code == 200
    briefing_data = resp_briefing.json()

    assert briefing_data["portfolio_roi_score"] > 0.0
    assert len(briefing_data["supported_concerns"]) == 1
    assert briefing_data["supported_concerns"][0]["coverage_score"] == 1.0


def test_aurarouter_adapter_raises_service_unavailable_when_endpoint_down() -> None:
    """Verifies AuraRouterAdapter makes a real transport attempt and raises ServiceUnavailableError when target socket refuses connection."""
    adapter = AuraRouterAdapter(
        aurarouter_url="http://240.0.0.1:9999",  # Non-routable IP
        model="bijou-strategic-reasoner",
        timeout=1.0,
    )
    briefing = PerspectiveBriefingDTO(
        subject_org_id="org-c2",
        as_of_date="2026-06-01",
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        adapter.synthesize_executive_briefing(briefing, "Tactical mission")

    assert "AuraRouter connection to" in str(exc_info.value)
    adapter.close()


def test_payload_size_limit_middleware_rejects_oversized_body(wired_client: TestClient) -> None:
    """Sends a payload exceeding max_payload_bytes and verifies HTTP 413 response."""
    client = wired_client
    # max_payload_bytes was set to 1024 bytes in wired_client fixture
    large_payload = {"oversized_junk": "X" * 2048}

    response = client.post(
        "/api/v1/manifest/import",
        json=large_payload,
    )
    assert response.status_code == 413
    assert "Payload exceeds maximum allowed bytes limit" in response.json()["detail"]
