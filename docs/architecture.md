# Bijou System Architecture Specification

This document provides a comprehensive architectural specification of the **Bijou Multi-Echelon Impact & Causal Graph Engine**, detailing its domain ontology, mathematical engines, storage subsystems, concurrency model, and offline-first security design.

---

## Table of Contents

1. [Architectural Overview & Design Philosophy](#1-architectural-overview--design-philosophy)
2. [Hexagonal Architecture (Ports & Adapters)](#2-hexagonal-architecture-ports--adapters)
3. [Domain Ontology & Graph Structure](#3-domain-ontology--graph-structure)
   - [Node Entities & Schemas](#node-entities--schemas)
   - [Edge Classifications & Temporal Bounds](#edge-classifications--temporal-bounds)
4. [Engine Mechanics & Mathematical Formulations](#4-engine-mechanics--mathematical-formulations)
   - [DAG Construction & Cycle Prevention](#dag-construction--cycle-prevention)
   - [Critical Path Method (CPM) Slack & Slip Propagation](#critical-path-method-cpm-slack--slip-propagation)
   - [Causal Gate Evaluation Mechanisms](#causal-gate-evaluation-mechanisms)
   - [Strategic Concern Coverage & Portfolio ROI Formula](#strategic-concern-coverage--portfolio-roi-formula)
   - [Sovereign Multi-Perspective Projection Algorithm](#sovereign-multi-perspective-projection-algorithm)
5. [Storage & Persistence Architecture](#5-storage--persistence-architecture)
   - [SQLite Transactional Store (WAL Mode & Atomic Rollback)](#sqlite-transactional-store-wal-mode--atomic-rollback)
   - [DuckDB Columnar Analytical Store](#duckdb-columnar-analytical-store)
6. [In-Memory Projection & Concurrency Control](#6-in-memory-projection--concurrency-control)
7. [Web GUI & Visualization Architecture](#7-web-gui--visualization-architecture)
   - [Stratified 4X Tech Tree Matrix](#stratified-4x-tech-tree-matrix)
   - [Native SVG Orthogonal Bézier Routing](#native-svg-orthogonal-bézier-routing)
   - [Executive 1-Slide Print Engine](#executive-1-slide-print-engine)
8. [Security & Air-Gapped Compliance](#8-security--air-gapped-compliance)

---

## 1. Architectural Overview & Design Philosophy

Complex multi-echelon technology portfolios—such as defense architectures, orbital satellite constellations, and integrated industrial ecosystems—cannot be modeled accurately as linear roadmaps or static Gantt charts. They are **non-linear, multi-echelon causal systems** characterized by:
1. **Combinatorial Synchronization**: Downstream capabilities often require multiple disparate technology initiatives to reach specific Technology Readiness Levels (TRLs) simultaneously.
2. **Asymmetric Blast Radii**: A schedule delay in a foundational sensor payload can cascade through communication links and automated correlation gates, disabling multi-billion-dollar interceptors.
3. **Sovereign Perspectives**: Different organizational echelons (enterprise commands, operational wings, tactical units) view the same portfolio through distinct boundaries of ownership, external dependencies, and risk exposure.

**Bijou** addresses these challenges by maintaining a centralized, verified causal Directed Acyclic Graph (DAG) coupled with high-speed analytical telemetry rollups and deterministic projection algorithms.

```
+-----------------------------------------------------------------------------------+
|                                  Client Layer                                     |
|  Air-Gapped Web GUI (Vanilla JS/SVG)   |   Python SDK (bijou-pysdk)   |   CLI     |
+------------------------------------------+----------------------------------------+
                                           | HTTP / REST (Relative paths)
+------------------------------------------v----------------------------------------+
|                             FastAPI Web Service Layer                             |
|       Routing  |  Payload Limit Middleware  |  Static Bundle File Serving         |
+------------------------------------------+----------------------------------------+
                                           |
+------------------------------------------v----------------------------------------+
|                          Application Orchestration Service                        |
|   Thread-Safe Lock  |  Projection Cache  |  Multi-Perspective Resolver            |
+-------------------+----------------------+--------------------+-------------------+
                    |                      |                    |
+-------------------v---+          +-------v-----------+  +-----v-------------------+
|  Graph Projection     |          | SQLite Repository |  | DuckDB Analytics        |
|  Engine (NetworkX)    |          | (Atomic CRUD /    |  | (Columnar Telemetry     |
|  CPM Slack & Slip Math|          |  WAL Transactions)|  |  Aggregation Rollups)   |
+-----------------------+          +-------------------+  +-------------------------+
```

---

## 2. Hexagonal Architecture (Ports & Adapters)

Bijou follows strict **Hexagonal Architecture** principles. The application core contains zero knowledge of HTTP servers, database drivers, or frontend rendering technologies.

```
       [ HTTP Clients ]       [ SDK Clients ]       [ CLI Utilities ]
              |                      |                      |
              +----------------------+----------------------+
                                     |
                          +----------v-----------+
                          |   Driving Adapter    |
                          | (FastAPI Web Layer)  |
                          +----------+-----------+
                                     |
                     +---------------v---------------+
                     |   Application Orchestrator    |
                     +---------------+---------------+
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
           +-----v-----+       +-----v-----+       +-----v-----+
           | Port:     |       | Port:     |       | Port:     |
           | RepoPort  |       | Telemetry |       | Reasoner  |
           +-----+-----+       +-----+-----+       +-----+-----+
                 |                   |                   |
           +-----v-----+       +-----v-----+       +-----v-----+
           | Adapter:  |       | Adapter:  |       | Adapter:  |
           | SQLiteRepo|       | DuckDB    |       | AuraRouter|
           +-----------+       +-----------+       +-----------+
```

- **Core Ports (`src/bijou/core/ports/`)**:
  - `RepositoryPort`: Defines abstract CRUD, entity listing, and atomic manifest replacement operations.
  - `TelemetryStorePort`: Defines telemetry event ingestion and parameterized analytical metric aggregations.
  - `ProjectionEnginePort`: Defines in-memory DAG compilation, milestone state evaluation, and slip propagation.
  - `ReasoningServicePort`: Defines optional natural language synthesis.
- **Driven Adapters (`src/bijou/adapters/`)**:
  - `SqliteRepository`: Implements `RepositoryPort` using standard library `sqlite3` with WAL mode.
  - `DuckDBTelemetryStore`: Implements `TelemetryStorePort` using embedded DuckDB.
  - `AuraRouterClient`: Implements `ReasoningServicePort` over HTTP with graceful 503 fallback.

---

## 3. Domain Ontology & Graph Structure

### Node Entities & Schemas

The domain model is defined in `src/bijou/core/domain/dtos.py` using immutable Pydantic models:

1. **Organization**: Sovereign administrative or operational unit.
   - `id`: Unique string identifier (e.g., `org-space-command`).
   - `name`: Display name.
   - `echelon_level`: Hierarchy depth ($0 = \text{Enterprise}, 1 = \text{Operational}, 2 = \text{Tactical}$).
   - `parent_org_id`: Direct sovereign lineage identifier.
   - `mission_statement`: High-level charter.
2. **Strategic Concern**: Top-level strategic objective or mission need.
   - `id`: Identifier (e.g., `concern-deep-sensing`).
   - `title`: Name of capability requirement.
   - `priority`: Normalized weight in $[0.0, 1.0]$.
   - `target_metric_sla`: Numerical performance SLA threshold.
   - `owner_org_id`: Responsible organization.
3. **Thing**: Tangible asset, software platform, or capital initiative.
   - `id`: Identifier (e.g., `thing-space-constellation`).
   - `name`: Program title.
   - `owner_org_id`: Owning organization.
   - `lifecycle`: `PROPOSED`, `ACTIVE`, `DELIVERED`, or `DIVESTED`.
   - `estimated_cost`: Budget footprint in base currency units.
   - `risk_factor`: Multiplier $\ge 1.0$.
4. **Milestone**: Developmental deliverable within a Thing.
   - `id`: Identifier (e.g., `ms-space-chamber-proto`).
   - `thing_id`: Parent Thing reference.
   - `title`: Deliverable title.
   - `trl`: Technology Readiness Level ($1 \le \text{TRL} \le 9$).
   - `sequence_index`: Internal chronological order ($0, 1, 2, \dots$).
   - `target_date`: Scheduled delivery date (`YYYY-MM-DD`).
   - `actual_date`: Historical delivery date, or `null`.
5. **Causal Gate**: Combinatorial synchronization mechanism.
   - `id`: Identifier (e.g., `gate-sensor-sync`).
   - `name`: Synchronization title.
   - `mechanism`: `ADDITIVE`, `COMBINATORIAL_AND`, or `THRESHOLD_K_OF_N`.
   - `threshold_k`: Integer parameter for threshold gates.
6. **Effect**: Operational or strategic capability produced by a gate.
   - `id`: Identifier (e.g., `eff-track-persistence`).
   - `gate_id`: Feeding gate reference.
   - `tier`: `STRATEGIC` (maps to concerns), `OPERATIONAL` (maps to telemetry), or `FEDERATED`.
   - `yield_value`: Computed capability output in $[0.0, 1.0]$.

### Edge Classifications & Temporal Bounds

Graph edges define relationships across the heterogeneous node graph:
- `PREREQUISITE_OF`: Milestone $\to$ Milestone dependency.
- `INPUT_TO`: Milestone $\to$ Causal Gate or Thing $\to$ Causal Gate contributor link.
- `FEEDS`: Causal Gate $\to$ Effect capability activation link.
- `SATISFIES`: Effect $\to$ Strategic Concern satisfaction link.
- `OWNS`: Organization $\to$ Thing or Organization $\to$ Concern ownership link.
- `PARENT_OF`: Organization $\to$ Sub-Organization sovereign hierarchy link.

Every edge supports optional temporal boundaries:
- `valid_from`: Analysis timestamp before which the edge is inactive.
- `valid_to`: Analysis timestamp after which the edge is expired.

Edges falling outside the analysis `as_of_date` are filtered out during DAG compilation.

---

## 4. Engine Mechanics & Mathematical Formulations

### DAG Construction & Cycle Prevention

Bijou utilizes NetworkX directed graphs (`nx.DiGraph`) to represent the portfolio topology. Before any mutation is committed:
1. A candidate DAG is constructed containing all active nodes and temporal-filtered edges.
2. The engine executes `nx.is_directed_acyclic_graph(G)`.
3. If cycles are detected, `nx.simple_cycles(G)` extracts the cyclical path, and the transaction is aborted with a `GraphCycleError`.

### Critical Path Method (CPM) Slack & Slip Propagation

Bijou computes date propagation and milestone states using a forward-pass topological evaluation:

```
               +-------------------------------------------------+
               |  Determine Effective Arrival Date of Predecessors|
               +-----------------------+-------------------------+
                                       |
                Predecessor Effective Date > Target Date?
                                       |
                       +---------------+---------------+
                       |                               |
                     [ YES ]                         [ NO ]
                       |                               |
          +------------v------------+     +------------v------------+
          | Schedule Violation:     |     | Schedule Buffer Intact: |
          | Milestone State =       |     | Milestone State =       |
          |         BLOCKED         |     |         LOCKED          |
          +-------------------------+     +-------------------------+
```

1. **Effective Date Computation**:
   For each milestone $M$, let $T(M)$ be its planned target date, and $\Delta_{\text{slip}}(M)$ be any simulated schedule slip:
   $$\text{EffectiveDate}(M) = T(M) + \Delta_{\text{slip}}(M)$$
2. **Topological Forward Pass**:
   For every downstream milestone $D$ with direct prerequisites $\text{Pred}(D)$:
   $$\text{MaxPredecessorDate}(D) = \max_{P \in \text{Pred}(D)} \text{EffectiveDate}(P)$$
3. **State Resolution**:
   - **`ACHIEVED`**: Historical `actual_date` $\le \text{as\_of\_date}$, and Effective Date $\le \text{as\_of\_date}$.
   - **`ACTIVE`**: Predecessors are all `ACHIEVED`, but milestone is currently in progress.
   - **`UNLOCKED_READY`**: Predecessors are all `ACHIEVED`, and work is eligible to commence.
   - **`LOCKED`**: One or more predecessors are unachieved, but $\text{MaxPredecessorDate}(D) \le T(D)$ (slack absorbs the delay).
   - **`BLOCKED`**: The milestone is explicitly cancelled, or $\text{MaxPredecessorDate}(D) > T(D)$ (critical path slip violates downstream schedule).

### Causal Gate Evaluation Mechanisms

Causal gates aggregate upstream contributors into a normalized yield $Y \in [0.0, 1.0]$:

1. **`ADDITIVE`**:
   $$Y_{\text{additive}} = \min\left(1.0, \sum_{c \in \text{Achieved}} w_c\right)$$
   Where $w_c$ is the normalized contributor weight assigned on the incoming `INPUT_TO` edge.
2. **`COMBINATORIAL_AND`**:
   $$Y_{\text{and}} = \begin{cases} 1.0 & \text{if } \text{Achieved} = \text{TotalContributors} \\ 0.0 & \text{otherwise} \end{cases}$$
3. **`THRESHOLD_K_OF_N`**:
   $$Y_{k\text{-of-}n} = \begin{cases} 1.0 & \text{if } |\text{Achieved}| \ge k \\ 0.0 & \text{otherwise} \end{cases}$$

### Strategic Concern Coverage & Portfolio ROI Formula

1. **Strategic Concern Coverage**:
   For concern $C$ satisfied by effects $\text{Eff}(C)$:
   $$\text{Coverage}(C) = \min\left(100\%, \sum_{e \in \text{Eff}(C)} w_{e,C} \times Y(e) \times 100\%\right)$$
2. **Portfolio Return on Investment (ROI)**:
   Bijou balances strategic utility against total committed financial cost adjusted for technology risk:
   $$\text{ROI} = \frac{\sum_{C} \left(\text{Priority}(C) \times \frac{\text{Coverage}(C)}{100}\right) \times \sum_{e} Y(e)}{\sum_{T \in \text{ActiveThings}} \left(\text{EstimatedCost}(T) \times \text{RiskFactor}(T)\right)}$$

When a slip is simulated, Bijou recomputes the entire graph in memory and returns:
$$\Delta\text{ROI} = \text{ROI}_{\text{simulated}} - \text{ROI}_{\text{baseline}}$$

### Sovereign Multi-Perspective Projection Algorithm

When generating an Executive Briefing through the lens of Organization $O_{\text{perspective}}$:
1. **Organizational Hierarchy DAG**: Resolves descendant organizations by following both explicit `PARENT_OF` edges and inline `parent_org_id` attributes.
2. **Sovereign Boundary Filtering**:
   - **Owned Assets**: Things where `owner_org_id` $\in \text{ResolvedOrgs}$.
   - **Supported Concerns**: Concerns where `owner_org_id` $\in \text{ResolvedOrgs}$.
   - **Cross-Boundary Dependencies**: Milestones owned by external organizations that have outgoing `PREREQUISITE_OF` or `INPUT_TO` edges entering owned assets or gates.

### Pareto Optimal Frontier Evaluation Algorithm (`REC-008`)

To solve the multi-objective capital allocation problem (maximizing Aggregate ROI while minimizing Total Cost under a budget ceiling $B_{\text{ceiling}}$), Bijou performs non-dominated sorting over the candidate acquisition space:
1. **Candidate Portfolio Space**: Enumerates valid portfolios $P \subseteq \text{Things}_{\text{proposed}}$ such that $\sum_{T \in P} \text{Cost}(T) \le B_{\text{ceiling}}$.
2. **Non-Dominated Criterion**: Portfolio $A$ strictly dominates portfolio $B$ ($A \succ B$) if and only if:
   $$\text{Cost}(A) \le \text{Cost}(B) \quad \land \quad \text{ROI}(A) \ge \text{ROI}(B)$$
   $$\text{with at least one strict inequality } (\text{Cost}(A) < \text{Cost}(B) \lor \text{ROI}(A) > \text{ROI}(B))$$
3. **Micro-Precision Protection**: To prevent floating-point underflow on multi-million dollar defense acquisitions ($10M–$500M), ROI calculation maintains $\ge 10$ decimal places:
   $$\text{ROI}_{\text{candidate}} = \text{round}\left(\frac{\text{Yield}}{\text{Cost}}, 10\right)$$
4. The resulting Pareto frontier $\mathcal{P}^*$ forms an ascending non-dominated frontier curve rendered on the 2D SVG scatterplot.

### Pre-Flight Diagnostic Linting Algorithm (`REC-017`)

Prior to manifest import, Bijou executes topological diagnostic linting:
1. **Cycle Detection**: Builds a directed graph $G = (V, E)$ from all entity nodes and relationship edges and computes `nx.simple_cycles(G)`. Any detected loop paths are flagged as **Critical Blockers** (`blockers`), blocking import.
2. **Orphan Node Identification**: Identifies nodes where $\text{deg}_{\text{in}}(v) + \text{deg}_{\text{out}}(v) = 0$. Flagged as architectural smells (`warnings`).
3. **Anchor Verification**: Validates that all milestone anchor IDs referenced by incoming/outgoing edges exist within their parent Thing.

---

## 5. Storage & Persistence Architecture

```
+---------------------------------------------------------------+
|                      Storage Subsystems                       |
+-------------------------------+-------------------------------+
|     SQLite (Transactional)    |       DuckDB (Columnar)       |
+-------------------------------+-------------------------------+
| - Relational integrity        | - Analytical telemetry events |
| - Foreign key constraints     | - High-throughput append      |
| - WAL mode concurrency        | - Parameterized SQL rollups   |
| - Atomic manifest swap        | - Zero-copy metric extraction |
+-------------------------------+-------------------------------+
```

### SQLite Transactional Store (WAL Mode & Atomic Rollback)

All entities, relationships, and manifests are persisted in an embedded SQLite database (`src/bijou/adapters/db/sqlite_repo.py`).
- **Write-Ahead Logging (WAL)**: Enabled via `PRAGMA journal_mode=WAL;` to allow non-blocking concurrent readers while a write transaction is in flight.
- **Busy Timeout**: Configured with `PRAGMA busy_timeout=5000;` to eliminate table lock contention under concurrent load.
- **Atomic Manifest Replacement**: When importing a new portfolio manifest with `replace_all=True`, the entire dataset is replaced within a single atomic database transaction. If any foreign key or schema validation fails, the transaction automatically rolls back.

### DuckDB Columnar Analytical Store

High-frequency operational telemetry events are routed to an embedded DuckDB columnar engine (`src/bijou/adapters/telemetry/duckdb_store.py`).
- **High Ingestion Throughput**: Appends telemetry records into columnar storage without degrading SQLite relational performance.
- **Parameterized Aggregation**: Executes rollups (`SUM`, `AVG`, `MIN`, `MAX`, `LAST`) using parameterized SQL queries (`?` markers) to completely eliminate SQL injection vulnerabilities.

### Decision Provenance Ledger (`REC-019`)

Strategic decision justifications are persisted in a dedicated relational table `decision_logs` managed by `SqlAlchemyGraphRepository`:
- **Schema**: Columns for `id` (UUIDv4), `target_milestone_id`, `author`, `justification`, and `timestamp` (UTC ISO-8601).
- **Concurrency & WAL Mode**: Write transactions are guarded by `_write_lock` and context-managed SQLAlchemy sessions with explicit commits and rollback on error.
- **Audit Traceability**: Allows leadership to review the historical chain of justifications that led to schedule shifts and milestone reorganizations.

---

## 6. In-Memory Projection & Concurrency Control

Bijou decouples analytical graph traversal from disk I/O using an in-memory projection engine cached inside `ApplicationOrchestrator`:

1. **Thread-Safe Concurrency**: All mutations acquire a mutual exclusion lock (`threading.Lock`). Readers acquire the lock to read or clone cached projections.
2. **Deterministic Rebuild**: Any entity insertion, update, or deletion automatically triggers `rebuild_projection_graph()`.
3. **Perspective Caching**: Computed executive briefings and Tech Tree layouts are cached by their parameter signatures (`(org_id, perspective_id, include_descendants)`). Caches are invalidated instantly upon any graph mutation.

---

## 7. Web GUI & Visualization Architecture

Bijou's user interface is built as a **zero-dependency, air-gapped web application** residing in `src/bijou/web/static/`.

### Stratified 4X Tech Tree Matrix

The Tech Tree arranges nodes deterministically into an $M \times N$ CSS Grid layout:
- **TRL Tiers**: Nodes are partitioned into 3 columns:
  - Foundational (TRL 1-3)
  - Developmental (TRL 4-6)
  - Operational (TRL 7-9)
- **Fiscal Eras**: Nodes are bucketed by target completion half-years (e.g., `FY26-H1`, `FY26-H2`, `FY27-H1`).
- **Topological Depth**: Columns are generated based on the length of the longest path from any root prerequisite.

### Native SVG Orthogonal Bézier Routing

Dependency connectors are rendered in an inline `<svg id="connections-svg">` overlay:
- For each edge $(u, v)$, the engine reads the bounding client rectangles of the source and target milestone cards.
- It computes start point $(x_1, y_1)$ at the right anchor of $u$, and end point $(x_2, y_2)$ at the left anchor of $v$.
- It renders an orthogonal Bézier curve using native SVG path syntax:
  $$M(x_1, y_1) \quad C(x_1 + dx, y_1) \quad (x_2 - dx, y_2) \quad (x_2, y_2)$$
- Upstream critical-path spines are highlighted dynamically on hover by traversing prerequisite edges recursively in JavaScript.

### 2-Hop Concentric Radial Ego-Network (`REC-013`)

In Lens 3, focal asset relationships are rendered on an HTML5 `<canvas id="ego-network-canvas">`:
- **Center**: Focal Thing illuminated with glowing cyan aesthetic (`#06b6d4`, `#38bdf8`).
- **Concentric Orbits**:
  - Inner-left semi-circle arc ($r_1 \approx 110\text{px}$): 1-hop upstream predecessor Things (`#3b82f6`) with inward directed arrows.
  - Inner-right semi-circle arc ($r_1 \approx 110\text{px}$): 1-hop downstream dependent Things (`#10b981`) with outward directed arrows.
  - Outer-right semi-circle arc ($r_2 \approx 190\text{px}$): 2-hop produced strategic Effects (`#f59e0b`) with incident arrows.
- Interactive canvas mousemove listener calculates Euclidean distance to detect node hover, highlighting connected edges and rendering entity tooltips.

### Telemetry Sparklines & Horizontal SLA Threshold Bands (`REC-014`)

Operational telemetry rollups feature compact inline SVG sparklines:
- 8-point trendline polyline rendered in `#38bdf8`.
- Horizontal red dashed line (`#ef4444`, `stroke-dasharray="2,2"`) indicating the target metric SLA threshold.

### Interactive 2D SVG Pareto Scatterplot (`REC-008`)

The Trade-Off Matrix section renders an interactive 2D SVG coordinate plane:
- $X$-Axis: Total Cost ($0 to $BudgetCeiling).
- $Y$-Axis: Aggregate ROI ($0 to $\text{MaxROI}$).
- Non-dominated portfolios are rendered as illuminated gold circular points (`#f59e0b`) connected by an ascending frontier curve.
- Hover tooltips display proposed Thing IDs, total cost in millions, and aggregate ROI. Clicking any point selects candidate checkboxes and re-evaluates the trade-off.

### Direct Manipulation Lifecycle Workbench (`REC-016`)

In the Manifest Studio, entities are rendered across 4 lifecycle columns: `PROPOSED`, `ACTIVE`, `DELIVERED`, `RETIRED`.
- HTML5 Drag and Drop API (`dragstart`, `dragover`, `drop`) allows dragging cards between lanes.
- Dropping a card updates the entity's lifecycle state in the manifest JSON and re-renders the workbench in real-time.

### Executive 1-Slide Print Engine

The Executive Briefing lens incorporates a specialized print stylesheet:
- `@page { size: landscape; margin: 0; }`
- Forces dark-theme contrast retention via `-webkit-print-color-adjust: exact;`.
- Automatically hides header bars, navigation tabs, and scroll controls during browser print or PDF export.

---

## 8. Security & Air-Gapped Compliance

Bijou enforces strict security controls suitable for classified and air-gapped deployments:

1. **Zero External Network Calls**: Static bundles contain no third-party CDN scripts, analytics beacons, or remote font stylesheets.
2. **Payload Size-Limiting Middleware**: Enforces a strict 10 MB maximum request body size on all incoming HTTP requests to prevent memory exhaustion denial-of-service attacks.
3. **Path Traversal Protection**: The document ingestion engine (`bijou-doc-ingest`) resolves and sanitizes all file paths against directory traversal sequences (`../`).
4. **Parameterized SQL Queries**: All queries across both SQLite and DuckDB utilize parameterized prepared statements, preventing SQL injection.
5. **Fault Isolation**: External service adapters (e.g., AuraRouter) handle connection failures gracefully, returning standard HTTP 503 Service Unavailable responses without crashing the application shell.
