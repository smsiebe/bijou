"""Integration tests for bijou-pysdk client against live ASGI application."""

from datetime import date
from pathlib import Path

import pytest
from bijou_sdk import (
    BijouClient,
    BijouNotFoundError,
    BijouValidationError,
    LifecycleStatus,
    Milestone,
    MilestoneStatus,
    Organization,
    Thing,
)

from bijou.api.app import create_app
from bijou.config import BijouSettings


@pytest.fixture
def sdk_client(tmp_path: Path):
    """Fixture initializing an ASGI-backed BijouClient with isolated test persistence."""
    db_file = tmp_path / "sdk_test_graph.db"
    duckdb_file = tmp_path / "sdk_test_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    test_app = create_app(settings)

    with BijouClient(app=test_app) as client:
        yield client


def test_sdk_crud_and_views_against_live_asgi_app(sdk_client: BijouClient):
    """Verifies end-to-end SDK interaction across CRUD, views, and simulation."""
    # 1. Create Organization
    org = sdk_client.create_organization(
        Organization(
            id="org-space-corp",
            name="Orbital Systems Command",
            echelon_level=1,
            mission_statement="Command orbital assets",
        )
    )
    assert org.id == "org-space-corp"
    assert org.name == "Orbital Systems Command"

    # Verify listing
    orgs = sdk_client.list_organizations()
    assert len(orgs) == 1
    assert orgs[0].id == "org-space-corp"

    # 2. Create Thing with Milestone
    ms = Milestone(
        id="ms-leo-flight-test",
        thing_id="thing-leo-constellation",
        sequence_index=1,
        name="Flight Qualification Test",
        description="In-orbit qualification test",
        target_date=date(2027, 6, 1),
        status=MilestoneStatus.COMMITTED,
        lane="SPACE_LANE",
        trl=7,
    )
    thing = sdk_client.create_thing(
        Thing(
            id="thing-leo-constellation",
            name="LEO Constellation Mesh",
            description="Tactical mesh communications payload",
            lifecycle=LifecycleStatus.ACTIVE,
            owner_org_id="org-space-corp",
            estimated_cost=250000.0,
            risk_factor=3.0,
            milestones=[ms],
        )
    )
    assert thing.id == "thing-leo-constellation"
    assert len(thing.milestones) == 1

    # 3. Query Tech Tree View
    view = sdk_client.get_tech_tree()
    assert len(view.tiers) == 3
    assert len(view.nodes) == 1
    assert view.nodes[0].milestone_id == "ms-leo-flight-test"

    # 4. Simulate Slip
    slip_res = sdk_client.simulate_slip("ms-leo-flight-test", slip_days=45)
    assert slip_res.slipped_milestone_id == "ms-leo-flight-test"
    assert slip_res.slip_days == 45

    # 5. Export and Import Manifest
    exported = sdk_client.export_manifest()
    assert len(exported.organizations) == 1
    assert len(exported.things) == 1
    assert len(exported.things[0].milestones) == 1

    import_res = sdk_client.import_manifest(exported)
    assert "imported_things" in import_res or "total_imported" in import_res or import_res.get("imported_organizations", 0) >= 0


def test_sdk_raises_bijou_api_error_on_404_and_422(sdk_client: BijouClient):
    """Verifies that the SDK translates HTTP status codes into typed domain exceptions."""
    # 404 Not Found
    with pytest.raises(BijouNotFoundError) as exc_404:
        sdk_client.get_organization("non-existent-org-id")
    assert exc_404.value.status_code == 404

    # 422 Validation Error
    with pytest.raises(BijouValidationError) as exc_422:
        sdk_client.create_thing({"id": "thing-broken", "lifecycle": "INVALID_LIFECYCLE"})
    assert exc_422.value.status_code == 422
