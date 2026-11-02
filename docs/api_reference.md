# Bijou API & SDK Reference

Complete technical reference for the **Bijou REST API**, the **Python Client SDK (`bijou-pysdk`)**, and command-line interfaces.

---

## Table of Contents

1. [REST API Overview & Conventions](#1-rest-api-overview--conventions)
   - [Base URL & Protocol](#base-url--protocol)
   - [HTTP Status Codes & Error Handling](#http-status-codes--error-handling)
2. [REST Endpoints Catalog](#2-rest-endpoints-catalog)
   - [Organizations (`/api/v1/organizations`)](#organizations)
   - [Strategic Concerns (`/api/v1/concerns`)](#strategic-concerns)
   - [Things (`/api/v1/things`)](#things)
   - [Causal Gates (`/api/v1/causal-gates`)](#causal-gates)
   - [Effects (`/api/v1/effects`)](#effects)
   - [Graph Edges (`/api/v1/edges`)](#graph-edges)
   - [Portfolio Manifest (`/api/v1/manifest`)](#portfolio-manifest)
   - [Operational Telemetry (`/api/v1/telemetry`)](#operational-telemetry)
   - [Decision-Support Views (`/api/v1/views`)](#decision-support-views)
   - [Analysis & Simulation (`/api/v1/analysis`)](#analysis--simulation)
3. [Python SDK (`bijou-pysdk`) Reference](#3-python-sdk-bijou-pysdk-reference)
   - [Installation](#sdk-installation)
   - [Client Initialization](#client-initialization)
   - [Synchronous `BijouClient` Methods](#synchronous-bijouclient-methods)
   - [Asynchronous `AsyncBijouClient` Methods](#asynchronous-asyncbijouclient-methods)
   - [SDK Models & Data Classes](#sdk-models--data-classes)
   - [Exception Hierarchy](#sdk-exception-hierarchy)
4. [CLI Utilities Reference](#4-cli-utilities-reference)
   - [`bijou` Server CLI](#bijou-server-cli)
   - [`bijou-ingest` Ingestion Utility](#bijou-ingest-ingestion-utility)

---

## 1. REST API Overview & Conventions

### Base URL & Protocol

All REST endpoints are versioned under `/api/v1/`:
- **Format**: JSON (`Content-Type: application/json; charset=utf-8`).
- **Air-Gapped Friendly**: All client requests in the Web GUI use relative paths (`/api/v1/...`).
- **Maximum Request Size**: 10 MB (10,485,760 bytes) enforced by middleware.

### HTTP Status Codes & Error Handling

| Status Code | Meaning | Typical Trigger |
|---|---|---|
| `200 OK` | Request succeeded | Successful GET, manifest export, or simulation calculation. |
| `201 Created` | Resource created | Successful POST creating an entity. |
| `204 No Content` | Deleted | Successful DELETE of an entity or edge. |
| `400 Bad Request` | Malformed request or graph cycle | Attempting to create an edge that introduces a dependency cycle. |
| `404 Not Found` | Entity not found | Querying an ID that does not exist. |
| `413 Content Too Large` | Payload exceeded | Request body exceeds configured limit (10MB). |
| `422 Unprocessable Entity` | Validation error | Missing required fields, invalid enum, or out-of-range values. |
| `503 Service Unavailable` | Upstream failure | Optional external service (e.g., AuraRouter) unreachable. |

Standard error response format:
```json
{
  "detail": "Descriptive message or array of Pydantic validation errors"
}
```

---

## 2. REST Endpoints Catalog

### Organizations

#### `GET /api/v1/organizations`
Returns a list of all sovereign organizations.

#### `POST /api/v1/organizations`
Create or update an organization.
- **Request Body**:
  ```json
  {
    "id": "org-space-command",
    "name": "Strategic Space Command",
    "echelon_level": 0,
    "parent_org_id": null,
    "mission_statement": "Global orbital persistent sensing and missile warning."
  }
  ```
- **Response**: `201 Created` with created `OrganizationDTO`.

#### `GET /api/v1/organizations/{org_id}`
Retrieve a single organization by ID.

#### `DELETE /api/v1/organizations/{org_id}`
Remove an organization. Returns `204 No Content`.

---

### Strategic Concerns

#### `GET /api/v1/concerns`
Returns all strategic capability concerns.

#### `POST /api/v1/concerns`
Create a strategic concern.
- **Request Body**:
  ```json
  {
    "id": "concern-hypersonic-track",
    "title": "Hypersonic Threat Tracking",
    "priority": 0.95,
    "target_metric_sla": 99.5,
    "owner_org_id": "org-space-command"
  }
  ```
- **Response**: `201 Created` with `ConcernDTO`.

#### `GET /api/v1/concerns/{concern_id}`
Retrieve a single concern by ID.

---

### Things

#### `GET /api/v1/things`
Returns all things (capital assets, systems, research initiatives).

#### `POST /api/v1/things`
Create a thing with embedded milestones.
- **Request Body**:
  ```json
  {
    "id": "thing-space-constellation",
    "name": "Persistent Space Constellation",
    "owner_org_id": "org-space-command",
    "lifecycle": "ACTIVE",
    "estimated_cost": 450000000.0,
    "risk_factor": 1.25,
    "milestones": [
      {
        "id": "ms-constellation-pdr",
        "thing_id": "thing-space-constellation",
        "title": "Preliminary Design Review",
        "trl": 4,
        "sequence_index": 0,
        "target_date": "2026-06-01",
        "actual_date": "2026-05-15"
      }
    ]
  }
  ```
- **Response**: `201 Created` with `ThingDTO`.

#### `GET /api/v1/things/{thing_id}`
Retrieve a single thing including its internal milestones.

#### `DELETE /api/v1/things/{thing_id}`
Delete a thing and its associated milestones. Returns `204 No Content`.

---

### Causal Gates

#### `POST /api/v1/causal-gates`
Create a combinatorial synchronization gate.
- **Request Body**:
  ```json
  {
    "id": "gate-tracking-sync",
    "name": "Tracking Synchronization Gate",
    "mechanism": "COMBINATORIAL_AND",
    "threshold_k": null,
    "contributors": [
      {
        "thing_id": "thing-space-constellation",
        "milestone_id": "ms-constellation-cdr",
        "contribution_weight": 0.5
      },
      {
        "thing_id": "thing-edge-correlator",
        "milestone_id": "ms-correlator-flight",
        "contribution_weight": 0.5
      }
    ]
  }
  ```
- **Response**: `201 Created` with `CausalGateDTO`.

#### `GET /api/v1/causal-gates/{gate_id}`
Retrieve a causal gate by ID.

---

### Effects

#### `GET /api/v1/effects`
Returns all capability effects.

#### `POST /api/v1/effects`
Define an operational or strategic capability effect.
- **Request Body**:
  ```json
  {
    "id": "eff-persistent-hypersonic-track",
    "gate_id": "gate-tracking-sync",
    "tier": "STRATEGIC",
    "yield_value": 1.0,
    "description": "Continuous high-confidence track of hypersonic glide bodies."
  }
  ```
- **Response**: `201 Created` with `EffectDTO`.

#### `GET /api/v1/effects/{effect_id}`
Retrieve an effect by ID.

---

### Graph Edges

#### `GET /api/v1/edges`
Returns all graph edges across the portfolio.

#### `POST /api/v1/edges`
Create a directional graph dependency edge.
- **Request Body**:
  ```json
  {
    "id": "edge-pdr-to-cdr",
    "source_id": "ms-constellation-pdr",
    "target_id": "ms-constellation-cdr",
    "relationship": "PREREQUISITE_OF",
    "weight": 1.0,
    "valid_from": null,
    "valid_to": null
  }
  ```
- **Response**: `201 Created` with `GraphEdgeDTO`.
- **Error Response**: `400 Bad Request` if edge introduces a graph cycle.

#### `DELETE /api/v1/edges/{edge_id}`
Delete an edge. Returns `204 No Content`.

---

### Portfolio Manifest

#### `GET /api/v1/manifest/export`
Export the entire active portfolio graph as a single serialized manifest document.
- **Response**: `200 OK` with `BijouManifestDTO`.

#### `POST /api/v1/manifest/import`
Import a complete portfolio manifest.
- **Query Parameter**: `replace_all: bool` (default: `false`).
  - When `true`, executes an atomic database rollback and replacement.
- **Request Body**: `BijouManifestDTO`.
- **Response**: `200 OK` with `{"status": "success", "imported": { ... }}`.

---

### Operational Telemetry

#### `POST /api/v1/telemetry/events`
Ingest streaming operational telemetry events into DuckDB.
- **Request Body**: Single telemetry object or list of objects:
  ```json
  [
    {
      "event_id": "evt-track-001",
      "thing_id": "thing-space-constellation",
      "metric_name": "track_uptime_percentage",
      "metric_value": 99.8,
      "timestamp": "2026-10-30T12:00:00Z",
      "provenance_metadata": { "sensor_mode": "infrared_high_gain" }
    }
  ]
  ```
- **Response**: `200 OK` with `{"ingested_count": 1}`.

#### `GET /api/v1/telemetry/provenance/{event_id}`
Retrieve raw metadata and origin provenance for a specific ingested telemetry event.

---

### Decision-Support Views

#### `GET /api/v1/views/tech-tree`
Compute and return the 4X Stratified Tech Tree layout.
- **Query Parameters**:
  - `stratification_mode` (default: `TRL_TIERS`): Options: `TRL_TIERS`, `FISCAL_ERAS`, `TOPOLOGICAL_DEPTH`.
  - `as_of_date` (optional): Reference evaluation date (`YYYY-MM-DD`).
  - `org_filter` (optional): Filter to milestones owned by a specific organization.
- **Response**: `200 OK` with `TechTreeViewDTO` containing nodes, tiers, and dependency edges.

#### `GET /api/v1/views/perspectives/{org_id}`
Compute the 1-Slide Executive Briefing from the perspective of `{org_id}`.
- **Query Parameters**:
  - `perspective_org_id` (optional): Viewpoint organization. Defaults to `{org_id}`.
  - `include_descendants` (default: `true`): Whether to aggregate sub-organizations.
  - `as_of_date` (optional): Reference date (`YYYY-MM-DD`).
- **Response**: `200 OK` with `PerspectiveBriefingDTO` (Supported Concerns, Owned Things, Cross-Org Dependencies, Committed Cost, Strategic Narrative).

#### `GET /api/v1/views/things/{thing_id}/focal`
Compute the 2-Hop Ego-Network focal dashboard for a single Thing.
- **Query Parameters**:
  - `as_of_date` (optional): Reference date (`YYYY-MM-DD`).
- **Response**: `200 OK` with `ThingFocalDashboardDTO` (Milestones, Upstream Predecessors, Downstream Dependents, Unlocked Capabilities, DuckDB Telemetry Rollups).

---

### Analysis & Simulation

#### `POST /api/v1/analysis/simulate-slip`
Simulate a what-if milestone date slip or full cancellation.
- **Request Body**:
  ```json
  {
    "milestone_id": "ms-space-chamber-proto",
    "slip_days": 90,
    "simulate_cancellation": false
  }
  ```
- **Response**: `200 OK` with `SlipSimulationResultDTO`:
  ```json
  {
    "simulated_milestone_id": "ms-space-chamber-proto",
    "slip_days": 90,
    "baseline_roi": 0.0452,
    "simulated_roi": 0.0381,
    "roi_delta": -0.0071,
    "impacted_node_states": {
      "ms-space-chamber-proto": "ACTIVE",
      "ms-space-flight-proto": "BLOCKED"
    },
    "degraded_effects": ["eff-persistent-hypersonic-track"],
    "broken_concerns": ["concern-hypersonic-track"]
  }
  ```

#### `POST /api/v1/analysis/tradeoff`
Evaluate a portfolio tradeoff across multiple candidate Things.
- **Request Body**: Array of candidate Thing IDs:
  ```json
  ["thing-space-constellation", "thing-edge-correlator"]
  ```
- **Response**: `200 OK` with `TradeoffProposalComparisonDTO` (Total Cost, Aggregate ROI, Unlocked Capabilities, Concern Coverage Deltas).

---

## 3. Python SDK (`bijou-pysdk`) Reference

The `bijou-pysdk` package provides type-safe Python client access to Bijou.

### SDK Installation

```bash
pip install -e ./projects/bijou-pysdk
```

### Client Initialization

```python
from bijou_sdk import BijouClient

# Connect to a running Bijou server
client = BijouClient(base_url="http://0.0.0.0:8080", timeout=30.0)

# Or use as a context manager for automatic connection closing
with BijouClient(base_url="http://0.0.0.0:8080") as client:
    orgs = client.list_organizations()

# Direct in-memory ASGI testing without starting a network server:
from bijou.api.app import create_app
from bijou.config import BijouSettings

app = create_app(BijouSettings())
with BijouClient(app=app) as client:
    tree = client.get_tech_tree()
```

### Synchronous `BijouClient` Methods

#### Entity CRUD
- `client.create_organization(org: Organization | dict) -> Organization`
- `client.get_organization(org_id: str) -> Organization`
- `client.list_organizations() -> list[Organization]`
- `client.create_thing(thing: Thing | dict) -> Thing`
- `client.get_thing(thing_id: str) -> Thing`
- `client.list_things() -> list[Thing]`
- `client.create_concern(concern: Concern | dict) -> Concern`
- `client.get_concern(concern_id: str) -> Concern`
- `client.list_concerns() -> list[Concern]`
- `client.create_causal_gate(gate: CausalGate | dict) -> CausalGate`
- `client.get_causal_gate(gate_id: str) -> CausalGate`
- `client.create_effect(effect: Effect | dict) -> Effect`
- `client.get_effect(effect_id: str) -> Effect`
- `client.list_effects() -> list[Effect]`
- `client.create_edge(edge: GraphEdge | dict) -> GraphEdge`
- `client.list_edges() -> list[GraphEdge]`

#### Manifest Import/Export
- `client.export_manifest() -> ManifestPayload`
- `client.import_manifest(manifest: ManifestPayload | dict, replace_all: bool = False) -> dict`

#### Views & Decision Projections
- `client.get_tech_tree(stratification_mode: TechTreeStratificationMode | str = "TRL_TIERS", as_of_date: date | str | None = None, org_filter: str | None = None) -> TechTreeView`
- `client.simulate_slip(milestone_id: str, slip_days: int, simulate_cancellation: bool = False) -> SlipSimulationResult`
- `client.get_perspective_briefing(subject_org_id: str, perspective_org_id: str | None = None, include_descendants: bool = True, as_of_date: date | str | None = None) -> PerspectiveBriefing`
- `client.get_thing_focal_dashboard(thing_id: str, as_of_date: date | str | None = None) -> ThingFocalDashboard`
- `client.evaluate_tradeoff(proposed_thing_ids: list[str]) -> TradeoffProposalComparison`

### Asynchronous `AsyncBijouClient` Methods

For asynchronous applications (FastAPI services, asynchronous workers):

```python
from bijou_sdk import AsyncBijouClient

async with AsyncBijouClient(base_url="http://0.0.0.0:8080") as client:
    orgs = await client.list_organizations()
    tree = await client.get_tech_tree()
```

### SDK Models & Data Classes

All models are located in `bijou_sdk.models`:
- `Organization`
- `Concern`
- `Thing`
- `Milestone`
- `CausalGate`
- `Effect`
- `GraphEdge`
- `ManifestPayload`
- `TechTreeView`
- `SlipSimulationResult`
- `PerspectiveBriefing`
- `ThingFocalDashboard`
- `TradeoffProposalComparison`

### SDK Exception Hierarchy

All exceptions inherit from `BijouError`:
- `BijouError`: Base exception for all SDK errors.
  - `BijouConnectionError`: Raised on network failure or unreachable server.
  - `BijouApiError`: Base HTTP response error (includes `status_code`, `detail`, `response_body`).
    - `BijouNotFoundError`: Raised on HTTP 404.
    - `BijouValidationError`: Raised on HTTP 422.

---

## 4. CLI Utilities Reference

### `bijou` Server CLI

The `bijou` command manages server lifecycle and deployment modes:

```bash
bijou [OPTIONS]
```

#### Options:
- `--mode [standalone|api-only|worker|web-only]`: Runtime mode (default: `standalone`).
- `--host TEXT`: Network host interface to bind (default: `0.0.0.0`).
- `--port INTEGER`: Port to listen on (default: `8080`).
- `--db-uri TEXT`: SQLAlchemy relational URI (default: `sqlite:///./bijou_graph.db`).
- `--duckdb-path TEXT`: DuckDB analytical file path (default: `./bijou_telemetry.duckdb`).
- `--aurarouter-url TEXT`: HTTP endpoint for AuraRouter LLM reasoning.
- `--enable-reasoning / --no-reasoning`: Enable AI strategic narrative synthesis (default: false).

### `bijou-ingest` Ingestion Utility

The `bijou-ingest` command ingests manifest files and telemetry streams:

```bash
# Ingest both manifest and telemetry
bijou-ingest --manifest datasets/joint_isr_architecture.yaml --telemetry datasets/satellite_cascade_telemetry.jsonl

# Ingest into a custom server endpoint
bijou-ingest --manifest custom_manifest.json --server-url http://0.0.0.0:8080
```
