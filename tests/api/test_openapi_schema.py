"""Contract tests verifying OpenAPI 3.1 specification and 503 behavior for unwired dependencies."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from bijou.api.app import app
from bijou.api.deps import set_orchestrator

REQUIRED_V1_PATHS = {
    "/api/v1/organizations",
    "/api/v1/organizations/{org_id}",
    "/api/v1/concerns",
    "/api/v1/concerns/{concern_id}",
    "/api/v1/things",
    "/api/v1/things/{thing_id}",
    "/api/v1/causal-gates",
    "/api/v1/causal-gates/{gate_id}",
    "/api/v1/effects",
    "/api/v1/effects/{effect_id}",
    "/api/v1/edges",
    "/api/v1/edges/{edge_id}",
    "/api/v1/telemetry/events",
    "/api/v1/telemetry/provenance/{event_id}",
    "/api/v1/manifest/import",
    "/api/v1/manifest/export",
    "/api/v1/views/perspectives/{org_id}",
    "/api/v1/views/tech-tree",
    "/api/v1/views/things/{thing_id}/focal",
    "/api/v1/analysis/simulate-slip",
    "/api/v1/analysis/tradeoff",
}


def test_all_required_v1_endpoints_present_in_openapi() -> None:
    """Verifies all 21 required /api/v1/* paths exist in docs/openapi.json."""
    openapi_file = Path("docs/openapi.json")
    assert openapi_file.exists(), "docs/openapi.json does not exist"

    with open(openapi_file, encoding="utf-8") as f:
        schema = json.load(f)

    paths = set(schema.get("paths", {}).keys())
    assert len(REQUIRED_V1_PATHS) == 21, f"Expected 21 required paths, got {len(REQUIRED_V1_PATHS)}"
    missing = REQUIRED_V1_PATHS - paths
    assert not missing, f"Missing required paths in OpenAPI schema: {missing}"


def test_unwired_dependency_returns_503_service_unavailable() -> None:
    """Verifies calling an endpoint before backend injection returns HTTP 503."""
    set_orchestrator(None)
    client = TestClient(app)

    response = client.get("/api/v1/organizations")
    assert response.status_code == 503, f"Expected 503, got {response.status_code}: {response.text}"
    assert "Service backend not initialized" in response.json()["detail"]
