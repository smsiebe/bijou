# Bijou Developer & Contributing Guide

Welcome to the **Bijou** developer guide. This document provides technical specifications, development environment setup, architectural guidelines, testing workflows, and instructions for extending Bijou.

---

## Table of Contents

1. [Development Environment Setup](#1-development-environment-setup)
   - [Prerequisites](#prerequisites)
   - [Virtual Environment & Editable Installation](#virtual-environment--editable-installation)
2. [Repository Structure & Hexagonal Architecture](#2-repository-structure--hexagonal-architecture)
   - [Core Domain & Ports](#core-domain--ports)
   - [Adapters & Infrastructure](#adapters--infrastructure)
   - [Services & Web Application](#services--web-application)
   - [Subprojects (`bijou-pysdk` & `bijou-doc-ingest`)](#subprojects-bijou-pysdk--bijou-doc-ingest)
3. [Coding Standards & Compliance](#3-coding-standards--compliance)
   - [Air-Gapped & Offline-First Policy](#air-gapped--offline-first-policy)
   - [Banned Token Audit](#banned-token-audit)
   - [Linting & Type Safety](#linting--type-safety)
4. [Testing Strategy & Test Suites](#4-testing-strategy--test-suites)
   - [Overview of Test Suites](#overview-of-test-suites)
   - [Running Unit & Contract Tests](#running-unit--contract-tests)
   - [Adversarial Red-Team Torture Tests](#adversarial-red-team-torture-tests)
   - [Selenium Headless Chrome GUI Tests](#selenium-headless-chrome-gui-tests)
5. [GUI Snapshot Capture & Maintenance](#5-gui-snapshot-capture--maintenance)
   - [How the Snapshot Generator Works](#how-the-snapshot-generator-works)
   - [Regenerating Snapshots](#regenerating-snapshots)
6. [Extension Guidelines](#6-extension-guidelines)
   - [Adding a New Causal Gate Mechanism](#adding-a-new-causal-gate-mechanism)
   - [Adding a New Telemetry Metric Accumulator](#adding-a-new-telemetry-metric-accumulator)
   - [Adding a New Decision-Support Lens](#adding-a-new-decision-support-lens)
7. [Packaging & Distribution](#7-packaging--distribution)

---

## 1. Development Environment Setup

### Prerequisites

- **Python 3.10+** (Python 3.11, 3.12, 3.13, 3.14 supported).
- **Google Chrome** (required for headless Selenium GUI tests and snapshot generation).
- **Git**.

### Virtual Environment & Editable Installation

Bijou is structured as a root Python package with two accompanying subprojects under `projects/`:

```bash
# Clone repository
git clone https://github.com/smsiebe/bijou.git
cd bijou

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# Upgrade build tools
pip install --upgrade pip setuptools wheel

# Install Bijou in editable mode with development dependencies
pip install -e ".[dev]"

# Install subprojects in editable mode
pip install -e ./projects/bijou-pysdk
pip install -e ./projects/bijou-doc-ingest
```

Verify your installation:

```bash
bijou --version
pytest --version
ruff --version
```

---

## 2. Repository Structure & Hexagonal Architecture

Bijou strictly adheres to the **Hexagonal (Ports & Adapters)** architectural pattern to decouple domain logic and projection graph math from external database engines, transport protocols, and UI frameworks.

```
bijou/
+-- src/bijou/
|   +-- core/
|   |   +-- domain/          # Pydantic DTOs & Domain Schemas (immutable data transfer)
|   |   |   +-- dtos.py
|   |   +-- engine/          # Pure computational graph projection math & CPM algorithms
|   |   |   +-- causal.py
|   |   |   +-- tech_tree.py
|   |   +-- ports/           # Abstract interface definitions (Protocols / ABCs)
|   |       +-- repository.py
|   |       +-- telemetry.py
|   |       +-- projection.py
|   +-- adapters/            # Concrete infrastructure implementations
|   |   +-- db/              # SQLite transactional storage (WAL mode, atomic rollback)
|   |   |   +-- sqlite_repo.py
|   |   +-- telemetry/       # DuckDB analytical columnar store
|   |   |   +-- duckdb_store.py
|   |   +-- external/        # External bridge adapters (AuraRouter reasoning)
|   |       +-- aurarouter.py
|   +-- services/            # Application orchestration & thread-safe projection cache
|   |   +-- orchestrator.py
|   +-- web/                 # FastAPI REST routing & Air-Gapped Web GUI
|       +-- app.py
|       +-- static/          # Zero-CDN Vanilla JS/CSS/SVG static web bundle
|           +-- index.html
|           +-- style.css
|           +-- tech_tree.js
|           +-- executive.js
|           +-- focal.js
|           +-- manifest.js
+-- projects/
|   +-- bijou-pysdk/         # Lightweight, dependency-minimal Python Client SDK
|   +-- bijou-doc-ingest/    # Manifest & telemetry file parser / CLI ingest utility
+-- datasets/                # Standardized reference architectures & telemetry streams
+-- docs/                    # Self-contained documentation & visual snapshot assets
+-- scripts/                 # Developer tooling (banned token audits, snapshot capture)
+-- tests/                   # Multi-tier test suite (unit, contract, e2e, adversarial, selenium)
```

### Core Domain & Ports

The `src/bijou/core/` package has zero external infrastructure dependencies. It imports only Python standard libraries and Pydantic:
- **`core/domain/dtos.py`**: Declares immutable models for Organizations, Concerns, Things, Milestones, Causal Gates, Effects, and Telemetry Events.
- **`core/engine/causal.py`**: Implements NetworkX graph construction, cycle detection, date propagation, Critical Path Method (CPM) slack calculation, and gate yield formulas.
- **`core/engine/tech_tree.py`**: Calculates 4X Tech Tree matrix stratification (TRL, Fiscal Era, Depth) and evaluates downstream slip cascade deltas.
- **`core/ports/`**: Declares abstract interfaces (`RepositoryPort`, `TelemetryStorePort`, `ProjectionEnginePort`) that allow switching out SQLite, DuckDB, or memory structures without touching business logic.

### Adapters & Infrastructure

The `src/bijou/adapters/` package implements concrete ports:
- **`adapters/db/sqlite_repo.py`**: SQLite database repository utilizing Write-Ahead Logging (WAL) and atomic transaction rollbacks.
- **`adapters/telemetry/duckdb_store.py`**: Embedded DuckDB analytics engine executing parameterized aggregations (`SUM`, `AVG`, `MIN`, `MAX`, `LAST`) over time-series telemetry events without SQL injection risk.
- **`adapters/external/aurarouter.py`**: Optional HTTP client adapter for delegating natural language strategic narrative synthesis to an AuraRouter service.

### Services & Web Application

- **`services/orchestrator.py`**: Coordinates data persistence, in-memory projection invalidation, thread-safe Read/Write locking, and multi-perspective caching.
- **`web/app.py`**: FastAPI application exposing versioned REST endpoints under `/api/v1/...`, payload size-limiting middleware, and serving the offline static bundle.
- **`web/static/`**: Air-gapped UI with zero CDN links, zero web fonts, and native SVG rendering.

---

## 3. Coding Standards & Compliance

### Air-Gapped & Offline-First Policy

Bijou is deployed in secure, air-gapped environments. The web application shell and static assets **must never** reference external resources:
- No external CDNs (`cdnjs`, `unpkg`, `cdn.jsdelivr.net`, etc.).
- No Google Fonts or external web font services.
- No remote telemetry or analytics scripts.
- All styles, scripts, and SVG icons must be committed locally to `src/bijou/web/static/`.

Offline compliance is verified continuously by `tests/web/test_web_ui_offline_compliance.py`.

### Banned Token Audit

To prevent accidental hardcoding of development hostnames, IP addresses, or unfinished stubs in source packages, Bijou enforces an automated banned token audit.

Run the audit script:

```bash
python scripts/audit_banned_tokens.py
```

The script scans `src/` and `projects/` for:
- `localhost`
- `127.0.0.1`
- `TODO`
- `FIXME`
- `NotImplementedException`

When referencing server endpoints in source code, use relative URLs (`/api/v1/...`), configurable settings, or `0.0.0.0` for bind interfaces.

### Linting & Type Safety

Bijou uses **Ruff** for linting and code formatting:

```bash
# Check for lint violations
ruff check .

# Automatically apply safe fixes
ruff check --fix .

# Format code
ruff format .
```

---

## 4. Testing Strategy & Test Suites

Bijou maintains a comprehensive 37-test quality gate spanning five testing tiers:

```
+-------------------------------------------------------------+
|                      Test Architecture                      |
+-------------------------------------------------------------+
| Tier 1: Unit & Contract Tests (Pydantic, Ports, Validation) |
| Tier 2: Storage & Adapter Tests (SQLite WAL, DuckDB SQL)    |
| Tier 3: Engine Math Tests (CPM Slack, Causal Gates, Cycles) |
| Tier 4: Adversarial Torture Tests (Edge cases, Invalidation)|
| Tier 5: E2E Integration & Headless Selenium GUI Tests       |
+-------------------------------------------------------------+
```

### Overview of Test Suites

| Directory | Purpose | Tests |
|---|---|---|
| `tests/contracts/` | Validates DTO validation, byte-level manifest roundtrips, and abstract port enforcement. | 5 |
| `tests/adapters/` | Verifies SQLite CRUD, concurrency without deadlocks, and DuckDB SQL injection resistance. | 6 |
| `tests/engine/` | Tests combinatorial gates, cycle detection, and thread-safe concurrent projection rebuilds. | 4 |
| `tests/adversarial/` | Red-team torture tests: slip propagation, temporal edge bounds, parent-org DAG resolution. | 8 |
| `tests/api/` & `services/` | Tests OpenAPI schema conformance, 503 fallback handling, and size-limit middleware. | 5 |
| `tests/sdk/` & `ingest/` | Tests `bijou-pysdk` and `bijou-doc-ingest` CLI tools against live ASGI apps. | 4 |
| `tests/web/` | Verifies air-gapped compliance, print stylesheets, and automated headless Selenium GUI flows. | 4 |

### Running Unit & Contract Tests

To run the standard pytest suite:

```bash
pytest -v
```

To run a specific test module:

```bash
pytest tests/engine/test_graph_projection_engine.py -v
```

### Adversarial Red-Team Torture Tests

The adversarial suite (`tests/adversarial/test_redteam_torture.py`) subjects Bijou's mathematical algorithms to stressful edge cases:
- Incomplete gate prerequisites under `COMBINATORIAL_AND` and `THRESHOLD_K_OF_N`.
- Temporal edge filtering excluding future and expired dependencies.
- Multi-generation `parent_org_id` hierarchy aggregation without explicit graph edges.
- Deep milestone slip cascade degradation and portfolio ROI delta math.

```bash
pytest tests/adversarial/test_redteam_torture.py -v
```

### Selenium Headless Chrome GUI Tests

The Selenium test suite (`tests/web/test_gui_selenium.py`) executes end-to-end browser workflows against a live ASGI server:
1. Spawns an ephemeral background server thread with an isolated SQLite and DuckDB store.
2. Ingests the full reference dataset over HTTP via `BijouClient`.
3. Launches Headless Google Chrome using Selenium WebDriver.
4. Switches between all 4 decision lenses.
5. Simulates a 90-day milestone slip and verifies computed UI cascade deltas.
6. Switches executive perspectives and tests tradeoff evaluations.

To run the Selenium suite:

```bash
pytest tests/web/test_gui_selenium.py -v
```

---

## 5. GUI Snapshot Capture & Maintenance

Bijou includes an automated visual snapshot generator at `scripts/capture_gui_snapshots.py`. This script produces the high-resolution reference screenshots embedded in documentation.

### How the Snapshot Generator Works

```
                        scripts/capture_gui_snapshots.py
                                       |
    +----------------------------------+----------------------------------+
    |                                                                     |
1. Initialize isolated SQLite/DuckDB                 2. Launch Headless Chrome
   in tempdir & start background Uvicorn                (1440x960 viewport)
   server on ephemeral port                                               |
    |                                                                     |
3. Ingest joint_isr_architecture.yaml                                     |
   and satellite_cascade_telemetry.jsonl                                  |
    |                                                                     |
4. Navigate Chrome to server instance                                     |
    |                                                                     |
5. Exercise 4 Lenses, trigger Slip Drawer, switch perspectives             |
    |                                                                     |
6. Capture 6 high-res PNG snapshots to docs/assets/snapshots/             |
    |                                                                     |
7. Gracefully terminate Chrome and background Uvicorn server               |
```

### Regenerating Snapshots

Whenever you modify HTML structure, CSS layouts, or SVG connector routing, update the reference snapshots:

```bash
python scripts/capture_gui_snapshots.py
```

Generated snapshots are saved directly to `docs/assets/snapshots/`:
- `01_tech_tree_canvas.png`
- `02_slip_simulation_drawer.png`
- `03_executive_briefing.png`
- `04_focal_dashboard.png`
- `05_tradeoff_matrix.png`
- `06_manifest_crud_studio.png`

Commit the updated snapshots along with your code changes.

---

## 6. Extension Guidelines

### Adding a New Causal Gate Mechanism

Causal Gates are evaluated in `src/bijou/core/engine/causal.py`.

To add a new mechanism (e.g., `WEIGHTED_MAJORITY`):
1. **Update Enum**: Add the new mechanism to `CausalGateMechanism` in `src/bijou/core/domain/dtos.py`.
2. **Implement Yield Math**: In `src/bijou/core/engine/causal.py`, update `evaluate_gate_yield()`:
   ```python
   elif gate.mechanism == CausalGateMechanism.WEIGHTED_MAJORITY:
       total_weight = sum(w for _, w in contributors)
       achieved_weight = sum(w for (item, w) in contributors if is_achieved(item))
       yield_value = 1.0 if achieved_weight > (total_weight / 2.0) else 0.0
   ```
3. **Add Contract Test**: Add a test case in `tests/contracts/test_domain_dto_validation.py`.
4. **Update Frontend**: Update `src/bijou/web/static/tech_tree.js` to render any specific badge styling for the new gate type.

### Adding a New Telemetry Metric Accumulator

Telemetry metric rollups are executed in `src/bijou/adapters/telemetry/duckdb_store.py`.

To add a new accumulator (e.g., `MEDIAN` or `PERCENTILE_95`):
1. **Update Domain Enum**: Add `PERCENTILE_95` to `TelemetryAccumulator` in `src/bijou/core/domain/dtos.py`.
2. **Update SQL Query**: In `src/bijou/adapters/telemetry/duckdb_store.py`, map the accumulator to DuckDB's analytical functions:
   ```python
   if accumulator == TelemetryAccumulator.PERCENTILE_95:
       sql = "SELECT quantile_cont(metric_value, 0.95) FROM telemetry_events WHERE thing_id = ?"
   ```
3. **Verify SQL Injection Safety**: Always execute queries using parameterized arguments (`?` placeholders). Never format strings directly into SQL queries.

### Adding a New Decision-Support Lens

To add a 5th decision lens (e.g., a "Risk Heatmap"):
1. **Define DTO**: Create the response schema in `src/bijou/core/domain/dtos.py`.
2. **Engine Projection**: Add the projection builder method in `src/bijou/core/engine/`.
3. **Service Orchestration**: Expose the projection via `src/bijou/services/orchestrator.py` with caching.
4. **FastAPI Route**: Add a GET endpoint in `src/bijou/web/app.py` under `/api/v1/views/risk-heatmap`.
5. **Web Navigation**:
   - Add a navigation tab button `<button id="nav-heatmap" class="nav-tab">Risk Heatmap</button>` in `src/bijou/web/static/index.html`.
   - Add a container section `<section id="view-heatmap" class="view-panel hidden">...</section>`.
   - Implement the view rendering function in a dedicated JavaScript file (e.g., `heatmap.js`).
6. **Selenium Verification**: Extend `tests/web/test_gui_selenium.py` to navigate to the new tab, assert elements are rendered, and add a snapshot capture step in `scripts/capture_gui_snapshots.py`.

---

## 7. Packaging & Distribution

Bijou is configured for distribution via standard Python wheels:

```bash
# Build distribution packages
python -m pip install --upgrade build
python -m build

# Inspect generated artifacts in dist/
ls dist/
```

Before cutting a release or publishing:
1. Run `pytest` to ensure 100% test pass rate across all 37 tests.
2. Run `ruff check .` to verify zero linting errors.
3. Run `python scripts/audit_banned_tokens.py` to verify zero banned tokens.
4. Run `python scripts/capture_gui_snapshots.py` to update reference screenshots.
