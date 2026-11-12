"""Contract tests verifying OpenAPI 3.1 v2 endpoints and 503 behavior for unwired dependencies."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from bijou.api.app import app
from bijou.api.deps import set_orchestrator

REQUIRED_V2_PATHS = {
    "/api/v1/perspective",
    "/api/v1/organizations",
    "/api/v1/organizations/{org_id}",
    "/api/v1/resource-pools",
    "/api/v1/interests",
    "/api/v1/interests/{interest_id}",
    "/api/v1/efforts",
    "/api/v1/efforts/{effort_id}",
    "/api/v1/edges/org-org",
    "/api/v1/edges/org-interest",
    "/api/v1/edges/interest-interest",
    "/api/v1/edges/org-effort",
    "/api/v1/edges/effort-interest",
    "/api/v1/edges/effort-effort",
    "/api/v1/views/capability-tree",
    "/api/v1/views/tripartite-flow",
    "/api/v1/simulation/bill-of-efforts",
    "/api/v1/simulation/bill-of-efforts/commit",
    "/api/v1/views/efforts/{effort_id}/focal",
    "/api/v1/views/organizations/{org_id}/focal",
    "/api/v1/views/interests/{interest_id}/focal",
    "/api/v1/views/briefing",
    "/api/v1/manifest/import",
    "/api/v1/manifest/export",
    "/api/v1/manifest/validate",
    "/api/v1/telemetry/events",
    "/api/v1/telemetry/provenance/{event_id}",
    "/api/v1/decisions",
    "/api/v1/tools",
    "/api/v1/health",
}


def test_all_required_v2_endpoints_present_in_openapi() -> None:
    """Verifies all required Bijou v2 /api/v1/* paths exist in docs/openapi.json."""
    openapi_file = Path("docs/openapi.json")
    assert openapi_file.exists(), "docs/openapi.json does not exist"

    with open(openapi_file, encoding="utf-8") as f:
        schema = json.load(f)

    paths = set(schema.get("paths", {}).keys())
    missing = REQUIRED_V2_PATHS - paths
    assert not missing, f"Missing required v2 paths in OpenAPI schema: {missing}"


def test_unwired_dependency_returns_503_service_unavailable() -> None:
    """Verifies calling an endpoint before backend injection returns HTTP 503."""
    set_orchestrator(None)
    client = TestClient(app)

    response = client.get("/api/v1/organizations")
    assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.text}"
    assert "Service backend not initialized" in response.json()["detail"]
