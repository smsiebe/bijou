"""Tests for Bijou v2 integrated Python SDK (bijou.sdk) — sync & async endpoint parity."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.sdk import (
    AccessMode,
    AsyncBijouClient,
    BijouClient,
    BijouNotFoundError,
    BijouPermissionDeniedError,
    BijouValidationError,
    DecisionLogEntry,
    Effort,
    EffortEffortEdge,
    EffortInterestEdge,
    EffortTelemetryEvent,
    Interest,
    InterestInterestEdge,
    Organization,
    OrgEffortEdge,
    OrgInterestEdge,
    OrgOrgEdge,
    OrgOrgRelationType,
    ResourceCategory,
    ResourcePool,
)


def _make_app(tmp_path: Path, name: str = "sdk"):
    return create_app(
        BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/{name}.db",
            duckdb_path=str(tmp_path / f"{name}.duckdb"),
            enable_reasoning=False,
        )
    )


def test_sdk_client_full_crud_views_telemetry_and_errors(tmp_path: Path) -> None:
    app = _make_app(tmp_path, "sync_sdk")
    with BijouClient(app=app) as client:
        assert client.health()["engine"] == "bijou-v2"
        schema = client.get_openapi_schema()
        assert "/api/v1/organizations" in schema["paths"]

        # Orgs & Pools
        org1 = client.upsert_organization(Organization(id="org-1", name="Org One", is_managed=True))
        org2 = client.upsert_organization(Organization(id="org-2", name="Org Two", is_managed=True))
        assert client.get_organization("org-1").name == org1.name
        assert len(client.list_organizations()) == 2

        pool = client.upsert_resource_pool(
            ResourcePool(
                id="pool-1",
                org_id=org1.id,
                name="FY27 Ops",
                category=ResourceCategory.MONEY,
                capacity=500000.0,
            )
        )
        assert len(client.list_resource_pools(org_id=org1.id)) == 1
        assert pool.id == "pool-1"

        # Interests & Taxonomy
        intr_parent = client.upsert_interest(Interest(id="intr-parent", name="Resiliency"))
        intr_child = client.upsert_interest(Interest(id="intr-child", name="Optical Link"))
        assert client.get_interest("intr-child").name == intr_child.name
        client.upsert_interest_interest_edge(
            InterestInterestEdge(
                id="edge-ii-1",
                parent_interest_id=intr_parent.id,
                child_interest_id=intr_child.id,
            )
        )

        # Efforts & Dependency DAG
        eff1 = client.upsert_effort(Effort(id="eff-1", name="Effort One"))
        eff2 = client.upsert_effort(Effort(id="eff-2", name="Effort Two"))
        assert client.get_effort("eff-1").name == eff1.name
        client.upsert_effort_effort_edge(
            EffortEffortEdge(id="edge-ee-1", source_effort_id=eff1.id, target_effort_id=eff2.id)
        )

        # Remaining Edge Families
        client.upsert_org_org_edge(
            OrgOrgEdge(
                id="edge-oo-1",
                source_org_id=org1.id,
                target_org_id=org2.id,
                relation_type=OrgOrgRelationType.COLLABORATIVE_ADJACENT,
            )
        )
        client.upsert_org_interest_edge(
            OrgInterestEdge(id="edge-oi-1", org_id=org1.id, interest_id=intr_parent.id)
        )
        client.upsert_org_effort_edge(
            OrgEffortEdge(
                id="edge-oe-1",
                org_id=org1.id,
                effort_id=eff1.id,
                resource_pool_id=pool.id,
                resourcing_type=ResourceCategory.MONEY,
                allocation_amount=10000.0,
                allocation_unit="USD",
                is_generic=False,
            )
        )
        client.upsert_effort_interest_edge(
            EffortInterestEdge(id="edge-ei-1", effort_id=eff1.id, interest_id=intr_child.id)
        )

        # Validation & NotFound exceptions
        with pytest.raises(BijouValidationError):
            client.upsert_effort_effort_edge(
                EffortEffortEdge(source_effort_id="eff-2", target_effort_id="eff-1")
            )
        with pytest.raises(BijouNotFoundError):
            client.get_effort("non-existent-effort")

        # Permission enforcement on Managed Org Owner perspective
        client.set_perspective(AccessMode.MANAGED_ORG_OWNER, "org-1")
        p_state = client.get_perspective_state()
        assert p_state.mode == AccessMode.MANAGED_ORG_OWNER
        with pytest.raises(BijouPermissionDeniedError):
            client.upsert_org_effort_edge(
                OrgEffortEdge(org_id="org-2", effort_id="eff-2", allocation_amount=10.0)
            )

        # Views & Focal Dashboards & Briefing
        view_a = client.get_capability_tree()
        assert len(view_a.nodes) == 2
        view_b = client.get_tripartite_flow()
        assert len(view_b.capability_tree.nodes) == 2
        assert client.get_effort_focal_dashboard("eff-1").forecast.effort.id == "eff-1"
        assert client.get_org_focal_dashboard("org-1").organization.id == "org-1"
        assert client.get_interest_focal_dashboard("intr-child").interest.id == "intr-child"

        briefing = client.get_perspective_briefing("org-1")
        assert briefing.active_access_mode == AccessMode.MANAGED_ORG_OWNER

        # Telemetry & Decision Provenance & Tools
        ingested = client.ingest_telemetry_events(
            [
                EffortTelemetryEvent(
                    event_id="ev-1",
                    effort_id="eff-1",
                    source_org_id="org-1",
                    causal_verb="COLLECTED",
                    occurred_at=datetime.now(timezone.utc),
                    metric_name="latency_ms",
                    metric_value=12.4,
                )
            ]
        )
        assert ingested == 1
        assert len(client.trace_event_provenance("ev-1")) == 1

        client.log_decision(
            DecisionLogEntry(target_effort_id="eff-1", author="Lead", justification="Baseline funded")
        )
        assert len(client.list_decision_logs(target_effort_id="eff-1")) == 1
        assert len(client.list_tools()) >= 1

        # Diagnostics & Manifest Export
        assert client.validate_manifest().blockers == []
        exported = client.export_manifest()
        assert len(exported.efforts) == 2

        # Deletes
        client.set_perspective(AccessMode.GLOBAL_ANALYST, None)
        assert client.delete_edge("effort_effort_edge", "edge-ee-1") is True
        assert client.delete_effort("eff-2") is True
        assert client.delete_interest("intr-child") is True
        assert client.delete_resource_pool("pool-1") is True
        assert client.delete_organization("org-2") is True


@pytest.mark.asyncio
async def test_async_sdk_client_parity(tmp_path: Path) -> None:
    app = _make_app(tmp_path, "async_sdk")
    async with app.router.lifespan_context(app):
        async with AsyncBijouClient(app=app) as client:
            assert (await client.health())["engine"] == "bijou-v2"
            org = await client.upsert_organization(Organization(id="org-a", name="Async Org"))
            assert org.name == "Async Org"
            eff = await client.upsert_effort(Effort(id="eff-a", name="Async Effort"))
            assert eff.name == "Async Effort"
            tree = await client.get_capability_tree()
            assert len(tree.nodes) == 1
            assert await client.delete_effort("eff-a") is True
            assert await client.delete_organization("org-a") is True

