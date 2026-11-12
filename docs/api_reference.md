# Bijou v2 API & SDK Reference

Complete technical reference for the **Bijou REST API** (`/api/v1/...`), self-hosted **OpenAPI 3.1** documentation, the integrated **Python SDK (`bijou.sdk`)**, and CLI tools (`bijou`, `bijou-ingest`).

---

## 1. Self-Hosted OpenAPI & HTTP Conventions

When running the Bijou server (`bijou --mode standalone --port 8000`), FastAPI exposes full interactive documentation automatically:
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI 3.1 JSON**: `/openapi.json` (also exported offline to [`docs/openapi.json`](openapi.json) via `scripts/export_openapi.py`)

### Conventions
- **Versioned Prefix**: `/api/v1`
- **Idempotent Upserts**: Entity & edge `POST` routes accept explicit string `id` fields and create or update in place—safe for repeatable document extraction pipelines.
- **Perspective Headers**:
  - `X-Bijou-Access-Mode`: `GLOBAL_ANALYST` (default) or `MANAGED_ORG_OWNER`
  - `X-Bijou-Active-Org`: Required when acting as `MANAGED_ORG_OWNER`; restricts pool/allocation writes to the active organization (`403 Forbidden` otherwise).
- **Payload Limit**: 10 MB (`max_payload_bytes`) returning `413` if exceeded.

### Status Codes
- `200 OK` / `201 Created` / `202 Accepted` — Success
- `400 Bad Request` — Invalid category or request argument
- `403 Forbidden` — Organizational perspective boundary violation
- `404 Not Found` — Missing entity or edge ID
- `413 Content Too Large` — Payload exceeds server limit
- `422 Unprocessable Content` — Schema validation failure or DAG cycle detected (`EffortEffortEdge` or `InterestInterestEdge`)
- `503 Service Unavailable` — Optional upstream dependency offline

---

## 2. REST Endpoints Catalog

### Organizations & Resource Pools
- `POST /api/v1/organizations` — Upsert an `OrganizationDTO`
- `GET /api/v1/organizations` — List all organizations
- `GET /api/v1/organizations/{org_id}` — Fetch single organization
- `DELETE /api/v1/organizations/{org_id}` — Delete organization
- `POST /api/v1/resource-pools` — Upsert a `ResourcePoolDTO` (respects active Org perspective)
- `GET /api/v1/resource-pools?org_id=...` — List resource pools
- `DELETE /api/v1/resource-pools/{pool_id}` — Delete resource pool

### Interests (DAG) & Stateful Efforts
- `POST /api/v1/interests` / `GET /api/v1/interests` / `GET /api/v1/interests/{interest_id}` / `DELETE /api/v1/interests/{interest_id}`
- `POST /api/v1/efforts` / `GET /api/v1/efforts` / `GET /api/v1/efforts/{effort_id}` / `DELETE /api/v1/efforts/{effort_id}`

### Six Typed Relationships (with Intelligence Pedigree)
All edge types share optional provenance fields (`id`, `confidence`, `provenance_note`, `effective_start`, `effective_end`):
- `POST /api/v1/edges/org-org` — `OrgOrgEdgeDTO` (`HIERARCHICAL_PARENT`, `FORMAL_SUPPORTING`, `COLLABORATIVE_ADJACENT`, `CO_SPONSOR`)
- `POST /api/v1/edges/org-interest` — `OrgInterestEdgeDTO` (`stance`, `priority_rank`, `allow_hierarchy_inheritance`)
- `POST /api/v1/edges/interest-interest` — `InterestInterestEdgeDTO` (`SPECIALIZES`, `CONTRIBUTES_TO`, `RELATED_TO`; acyclic)
- `POST /api/v1/edges/org-effort` — `OrgEffortEdgeDTO` + optional query `human_slip_penalty_days`
- `POST /api/v1/edges/effort-interest` — `EffortInterestEdgeDTO` (`DIRECT_SOLUTION`, `INDIRECT_ENABLER`, `FUNDED_FOR`, `PARTIAL_ALIGNMENT`, `impact_weight`)
- `POST /api/v1/edges/effort-effort` — `EffortEffortEdgeDTO` (`BLOCKING`, `NON_BLOCKING_INFORMS`, `dependency_degree`; acyclic)
- `DELETE /api/v1/edges/{edge_category}/{edge_id}` — Valid categories: `org_org_edge`, `org_interest_edge`, `interest_interest_edge`, `org_effort_edge`, `effort_interest_edge`, `effort_effort_edge`

### Manifest Interchange & Pre-Flight Diagnostics
- `GET /api/v1/manifest/export` — Export complete `BijouManifestDTO` (`schema_version: "2.0.0"`)
- `POST /api/v1/manifest/import?replace_all=false` — Atomically import/merge or replace the entire graph
- `POST /api/v1/manifest/validate` — Validate cycles, Color-of-Money rules, pool over-allocations, and skill mismatches (`DiagnosticReportDTO`)

### Analytical Views, Focal Dashboards & Simulation
- `GET /api/v1/views/capability-tree` — View A (`as_of_date`, `include_hierarchy_priorities`, `min_confidence`, `org_filter`)
- `GET /api/v1/views/tripartite-flow` — View B & Global Neural Graph payload
- `GET /api/v1/views/efforts/{effort_id}/focal` — `EffortFocalDashboardDTO`
- `GET /api/v1/views/organizations/{org_id}/focal` — `OrgFocalDashboardDTO`
- `GET /api/v1/views/interests/{interest_id}/focal` — `InterestFocalDashboardDTO`
- `GET /api/v1/views/briefing?subject_org_id=...` — 1-Slide Executive Briefing (`PerspectiveBriefingDTO`)
- `POST /api/v1/simulation/bill-of-efforts` — Transient What-If simulation (`BillOfEffortsSimulationResponseDTO`)
- `POST /api/v1/simulation/bill-of-efforts/commit` — Commit scenario mutations into persistent storage

### Operational Telemetry, Decisions & Tools
- `POST /api/v1/telemetry/events` — Batch ingest `list[EffortTelemetryEventDTO]` into DuckDB
- `GET /api/v1/telemetry/provenance/{event_id}?max_depth=10` — Trace causal telemetry lineage
- `POST /api/v1/decisions` / `GET /api/v1/decisions?target_effort_id=...` — Decision provenance ledger
- `GET /api/v1/perspective` — Current active perspective & managed org list
- `GET /api/v1/tools` — Available analytical tool descriptors
- `GET /api/v1/health` — Server health probe

---

## 3. Integrated Python SDK (`bijou.sdk`)

Both synchronous ([`BijouClient`](../src/bijou/sdk/client.py)) and asynchronous ([`AsyncBijouClient`](../src/bijou/sdk/client.py)) clients support remote HTTP servers (`base_url=...`, optional `api_key` / `extra_headers`) as well as in-process FastAPI testing (`app=...`).

### Example Usage

```python
from bijou.sdk import (
    AccessMode,
    AsyncBijouClient,
    BijouClient,
    BijouValidationError,
    Effort,
    ManifestIngestor,
)

# Synchronous HTTP client + batch manifest ingestor
with BijouClient(base_url="http://0.0.0.0:8000") as client:
    ingestor = ManifestIngestor(client)
    counts = ingestor.ingest_manifest_file(
        "datasets/joint_isr_architecture.json",
        replace_all=False,
        validate_first=True,
    )
    client.upsert_effort(Effort(id="eff-sensor-x", name="Sensor X"))
```

```python
# Asynchronous HTTP client
async with AsyncBijouClient(base_url="http://0.0.0.0:8000") as client:
    orgs = await client.list_organizations()
    view_b = await client.get_tripartite_flow()
```

### Complete Client Method Summary (`BijouClient` / `AsyncBijouClient`)
- **System**: `health()`, `get_openapi_schema()`, `get_perspective_state()`, `set_perspective(...)`, `list_tools()`
- **CRUD & Deletes**: `upsert_organization`, `get_organization`, `list_organizations`, `delete_organization`, `upsert_resource_pool`, `list_resource_pools`, `delete_resource_pool`, `upsert_interest`, `get_interest`, `list_interests`, `delete_interest`, `upsert_effort`, `get_effort`, `list_efforts`, `delete_effort`
- **Edges**: `upsert_org_org_edge`, `upsert_org_interest_edge`, `upsert_interest_interest_edge`, `upsert_org_effort_edge`, `upsert_effort_interest_edge`, `upsert_effort_effort_edge`, `delete_edge(edge_category, edge_id)`
- **Manifest**: `export_manifest()`, `import_manifest(manifest, replace_all=False)`, `validate_manifest(manifest=None)`
- **Views & Simulation**: `get_capability_tree(...)`, `get_tripartite_flow(...)`, `get_effort_focal_dashboard(...)`, `get_org_focal_dashboard(...)`, `get_interest_focal_dashboard(...)`, `get_perspective_briefing(...)`, `simulate_bill_of_efforts(...)`, `commit_bill_of_efforts(...)`
- **Telemetry & Decisions**: `ingest_telemetry_events(...)`, `trace_event_provenance(...)`, `log_decision(...)`, `list_decision_logs(...)`

### SDK Exceptions (`bijou.sdk.exceptions`)
- `BijouApiError` (base)
- `BijouValidationError` (`400`, `422`)
- `BijouPermissionDeniedError` (`403`)
- `BijouNotFoundError` (`404`)
- `BijouPayloadTooLargeError` (`413`)
- `BijouServiceUnavailableError` (`503`)
- `BijouConnectionError` (transport errors)

---

## 4. CLI Utilities

- `bijou --mode [standalone|api-only|worker|web-only] --port 8000`
- `bijou-ingest --server-url http://0.0.0.0:8000 --manifest <path> --telemetry <path> [--replace-all] [--validate-first]`
