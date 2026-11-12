"""Adversarial & boundary tests for Bijou v2 cycles, unauthorized perspective mutations, and malformed payloads."""

from pathlib import Path

from fastapi.testclient import TestClient

from bijou.api.app import create_app
from bijou.config import BijouSettings


def _client(tmp_path: Path, max_bytes: int = 1_048_576) -> TestClient:
    app = create_app(
        BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/adv.db",
            duckdb_path=str(tmp_path / "adv.duckdb"),
            max_payload_bytes=max_bytes,
            enable_reasoning=False,
        )
    )
    return TestClient(app)


def test_cycle_protection_across_efforts_and_interests(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client.post("/api/v1/efforts", json={"id": "e1", "name": "E1"})
        client.post("/api/v1/efforts", json={"id": "e2", "name": "E2"})
        assert client.post("/api/v1/edges/effort-effort", json={"source_effort_id": "e1", "target_effort_id": "e2"}).status_code == 201
        # Reverse cycle must return 422
        assert client.post("/api/v1/edges/effort-effort", json={"source_effort_id": "e2", "target_effort_id": "e1"}).status_code == 422

        client.post("/api/v1/interests", json={"id": "i1", "name": "I1"})
        client.post("/api/v1/interests", json={"id": "i2", "name": "I2"})
        assert client.post("/api/v1/edges/interest-interest", json={"parent_interest_id": "i1", "child_interest_id": "i2"}).status_code == 201
        assert client.post("/api/v1/edges/interest-interest", json={"parent_interest_id": "i2", "child_interest_id": "i1"}).status_code == 422


def test_cross_org_owner_mutation_blocked_with_403(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        client.post("/api/v1/organizations", json={"id": "org-a", "name": "Org A", "is_managed": True})
        client.post("/api/v1/organizations", json={"id": "org-b", "name": "Org B", "is_managed": True})
        resp = client.post(
            "/api/v1/resource-pools",
            json={
                "id": "pool-a",
                "org_id": "org-a",
                "name": "Pool A",
                "category": "MONEY",
                "capacity": 100.0,
                "unit": "USD",
            },
            headers={"X-Bijou-Access-Mode": "MANAGED_ORG_OWNER", "X-Bijou-Active-Org": "org-b"},
        )
        assert resp.status_code == 403


def test_oversized_payload_rejected_with_413(tmp_path: Path) -> None:
    with _client(tmp_path, max_bytes=128) as client:
        resp = client.post(
            "/api/v1/organizations",
            json={"id": "org-big", "name": "Big", "description": "x" * 300},
        )
        assert resp.status_code == 413
