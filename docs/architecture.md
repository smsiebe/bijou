# Bijou v2 System Architecture Specification

Bijou follows **Hexagonal (Ports & Adapters)** architecture to keep domain contracts, DAG projection math, persistence adapters, HTTP APIs, Python SDK clients, and the offline Web UI strictly decoupled.

---

## 1. Architecture Overview

```
+-------------------------------------------------------------------------+
|                            Client Layer                                 |
|   Offline Web UI (Pure Vanilla JS/SVG)  |  bijou.sdk (HTTP/ASGI) | CLI  |
+------------------------------------+------------------------------------+
                                     | REST (/api/v1) + OpenAPI 3.1
+------------------------------------v------------------------------------+
|                         FastAPI Application Layer                       |
|    Routing (v1_router) | Payload Limit | Static Web UI Bundle           |
+------------------------------------+------------------------------------+
                                     |
+------------------------------------v------------------------------------+
|                       BijouOrchestrationService                         |
|   Perspective Enforcement  |  Thread-Safe Cache  |  Manifest Diagnostics|
+-----------------+------------------+-------------------+----------------+
                  |                  |                   |
+-----------------v--+     +---------v--------+    +-----v---------------+
| Projection Engine  |     | SQLAlchemy Repo  |    | DuckDB Telemetry    |
| (NetworkX / Forecast)    | (SQLite WAL CRUD)|    | (Causal Rollups)    |
+--------------------+     +------------------+    +---------------------+
```

---

## 2. Core Packages

- **`src/bijou/core/contracts/`**: Immutable Pydantic v2 DTOs and enums (`OrganizationDTO`, `ResourcePoolDTO`, `InterestDTO`, `EffortDTO`, 6 edge DTOs with pedigree, `BijouManifestDTO`, view projections, simulation requests/responses).
- **`src/bijou/core/engine/`**: Pure Python + NetworkX projection engine computing Effort timing horizons, critical-path slack, SPOF bottlenecks, Color-of-Money Interest DAG inheritance, indirect benefits, partnership discovery, and Bill of Efforts simulation deltas.
- **`src/bijou/adapters/`**: SQLAlchemy repository (`db/`), DuckDB operational telemetry store (`telemetry/`), and optional offline-safe AuraRouter reasoning bridge (`llm/`).
- **`src/bijou/services/`**: `BijouOrchestrationService` coordinating repository commits, perspective boundaries (`GLOBAL_ANALYST` vs `MANAGED_ORG_OWNER`), and diagnostics.
- **`src/bijou/sdk/`**: Integrated synchronous (`BijouClient`) & asynchronous (`AsyncBijouClient`) SDK plus `ManifestIngestor` (`validate_safe_path` traversal guard + pre-flight validation) and `bijou-ingest` CLI.
- **`src/bijou/web/static/`**: Bundled zero-CDN offline Web UI.
- **`src/bijou/web/bridge.py`**: Optional [`BijouDesktopBridge`](../src/bijou/web/bridge.py) allowing desktop WebViews (`pywebview`, Tkinter + WebView2, Qt `QWebEngineView`) to embed the exact same FastAPI app & Web UI in-process with zero open TCP ports.

### Standalone Web Server vs. In-Process Desktop Bridge

Both runtime options share 100% of the FastAPI routing and static assets:
- **Standalone HTTP Server (`bijou --mode standalone`)**: `api.js` issues standard `fetch('/api/v1/...')` calls against FastAPI.
- **Zero-Webserver Desktop Bridge (`BijouDesktopBridge`)**: Wraps `create_app()` in Starlette's in-memory `TestClient` lifecycle and exposes:
  - `bridge.dispatch(method, path, headers, body)` / `dispatch_json(...)` (automatically picked up by `api.js` via `window.__BIJOU_BRIDGE__`, `BijouApi.setTransport(...)`, or `window.pywebview.api.dispatch`), with `bridge.render_desktop_html()` rewriting `/static/` to local `file://` `<base>` paths.
  - `bridge.serve_resource(method, path, ...)` for custom Chromium/Qt scheme handlers (`QWebEngineUrlSchemeHandler` / WebView2 `WebResourceRequested`) without rewriting HTML at all.

---

## 3. Web Visualization Engine (Zero External JS Libraries)

Bijou does **not** depend on D3, Cytoscape, Sigma, vis.js, or any third-party JavaScript graphing framework. All interactive views are custom Vanilla JS modules bundled in `src/bijou/web/static/`:
- **`view_a_dag.js`**: Topological layer assignment + HTML card layout + SVG cubic Bézier connectors (`BLOCKING` solid vs `NON_BLOCKING_INFORMS` dashed).
- **`view_b_tripartite.js`**: 3-column architectural flow grid + live scale-aware SVG routing and shared-interest hover emphasis.
- **`view_global_neural.js`**: Fruchterman-Reingold force simulation followed by a strict pairwise AABB collision-resolution solver (`resolveOverlaps`) guaranteeing zero card overlap, layered filters, node isolation, and drag pinning persisted in `localStorage`.
- **`graph_editor.js`**: Canvas/node/edge context menus, rubber-band SVG drag-to-connect ports, and plain-English non-technical node/relationship popups.

---

## 4. Packaging & Air-Gapped Compliance

- **Wheel Packaging**: `pyproject.toml` (`name = "bijou-portfolio"`, `package-data`) and `MANIFEST.in` explicitly bundle `bijou/web/static/*` alongside Python modules so `pip install bijou-portfolio` serves the complete UI cleanly with zero network access under the `bijou` import namespace.
- **Path Traversal Guard**: [`validate_safe_path`](../src/bijou/sdk/ingest.py) prevents directory-escape attempts during batch file ingestion.
- **No External CDN Calls**: Verified continuously by `tests/web/test_web_ui_offline_compliance.py`.
