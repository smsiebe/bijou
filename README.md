# Bijou

**Organizational Interests, Stateful Capability Progression & Resource Portfolio Engine (v2)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Zero External CDN](https://img.shields.io/badge/offline--first-airgapped%20compliant-brightgreen)]()

---

## Overview

**Bijou** is an offline-first strategic portfolio, capability dependency, and resource orchestration engine designed for modeling the complex interactions between:
- **Organizations** (and managed Color-of-Money resource pools)
- **Interests** (hierarchical DAGs spanning mission goals, threats, intelligence gaps, customers, and strategic categories)
- **Efforts** (stateful capability programs with optional resource requirements, delivery risks, mitigators, and explicit or dependency-relative timing)
- **6 Typed Relationships with Pedigree** (`OrgOrgEdge`, `OrgInterestEdge`, `InterestInterestEdge`, `OrgEffortEdge`, `EffortInterestEdge`, `EffortEffortEdge`)

Bijou ships as a single PyPI distribution (`bijou-portfolio`, import namespace `bijou`) bundling the FastAPI engine, SQLite + DuckDB stores, offline Vanilla JS/SVG Web UI, CLI entrypoints (`bijou`, `bijou-ingest`), and the integrated Python client SDK (`bijou.sdk`).

---

## Key Capabilities

1. **Three Primary Graph Modes (`A` / `B` / `G`)**:
   - **View A — Capability Progression Tree**: Stateful Effort DAG (`COMPLETED` → `IN_WORK` → `PLANNED` / `DISCOVERY_PENDING`) with SPOF detection, slack calculation, and hover neighborhood emphasis.
   - **View B — Tri-Partite Architectural Flow**: Maps **Organizations & Pools ↔ Efforts ↔ Interest Taxonomy**, illuminating indirect shared-interest benefits and potential organizational partnerships.
   - **View G — Global Neural Graph**: Free-floating force-directed topology with pairwise AABB zero-overlap resolution, node-type toggles, Org/Interest multi-filters, node isolation (`Right-Click → Isolate & Connections`), breadcrumb filter history, drag pinning, and cursor-anchored scroll-wheel zoom.
2. **Graph-Native Non-Technical Editing**:
   - Right-click anywhere to spawn Organizations, Efforts, or Interests; drag `●` connect handles between nodes to create relationships using plain-English statements instead of raw enum/direction jargon.
3. **Bill of Efforts Scenario Dock**:
   - Persistent slide-out cart for exercising mitigators, staging resource pool allocations (with Color-of-Money Interest DAG inheritance & skill-mismatch slip warnings), testing schedule slip/cancellation shocks, and committing approved decisions.
4. **Executive Briefing & Entity Studio**:
   - 1-slide landscape printable briefing tailored per Organization (`X-Bijou-Access-Mode` / `X-Bijou-Active-Org` perspective seam) plus a full Entity & Graph Studio with pre-flight manifest diagnostics.
5. **Air-Gapped & Self-Contained**:
   - Zero external JS libraries or CDNs in the Web UI; custom pure Vanilla JS + native browser SVG/DOM rendering bundled directly into the Python wheel.

---

## Quickstart

### 1. Installation

Install from PyPI (`pip install bijou-portfolio`) or from source:

```bash
pip install bijou-portfolio
# or from local source checkout:
pip install -e ".[dev]"
```

The single `bijou-portfolio` wheel includes the backend API, CLI, Web UI static assets (plus offline OpenAPI explorer), and `bijou.sdk` (keeping the `bijou` import namespace).

#### Air-Gapped / Corporate Firewall Transfer

When moving across a firewall into an internet-isolated network, gather platform-matched wheels (including compiled wheels such as `duckdb` and `pydantic-core`) on the connected side first:

```bash
# Example for Windows x64 + Python 3.12
pip download bijou-portfolio -d ./wheelhouse --only-binary=:all: --platform win_amd64 --python-version 3.12

# On the air-gapped target machine:
pip install --no-index --find-links=./wheelhouse bijou-portfolio
```

Note for locked-down corporate hosts: if the current directory is read-only, Bijou automatically stores its SQLite and DuckDB files in `~/.bijou/`, or you can use `bijou --host 127.0.0.1` / `BijouDesktopBridge` to avoid Windows Firewall prompts.

### 2. Launch the Application

```bash
bijou --mode standalone --port 8000
```

- **Web UI**: `http://0.0.0.0:8000/` (or `http://localhost:8000/` in a local browser)
- **Offline Interactive API Explorer**: `http://localhost:8000/docs` (also `/redoc`, zero external CDNs)
- **OpenAPI 3.1 Schema**: `http://localhost:8000/openapi.json`

### 3. Ingest Reference Data

```bash
bijou-ingest --server-url http://0.0.0.0:8000 \
  --manifest datasets/joint_isr_architecture.yaml \
  --telemetry datasets/satellite_cascade_telemetry.jsonl \
  --replace-all
```

---

## Integrated Python SDK (`bijou.sdk`)

Use [`BijouClient`](src/bijou/sdk/client.py) (sync), [`AsyncBijouClient`](src/bijou/sdk/client.py) (async), and [`ManifestIngestor`](src/bijou/sdk/ingest.py) directly from `bijou.sdk` for document-extraction pipelines and analytical automation:

```python
from bijou.sdk import (
    AccessMode,
    BijouClient,
    ManifestIngestor,
    Organization,
)

with BijouClient(base_url="http://0.0.0.0:8000") as client:
    # Upsert entities (idempotent by string ID)
    client.upsert_organization(
        Organization(id="org-demo", name="Joint Demo Org", is_managed=True)
    )

    # Or import an atomic multi-entity manifest bundle from an extractor
    ingestor = ManifestIngestor(client)
    ingestor.ingest_manifest_file(
        "datasets/joint_isr_architecture.json",
        validate_first=True,
    )

    # Query projections and run Bill of Efforts simulation
    tree = client.get_capability_tree()
    sim = client.simulate_bill_of_efforts({"effort_slips": {"eff-edge-correlator": 30}})
    print(f"Nodes: {len(tree.nodes)}, Impacted: {sim.impacted_effort_ids}")
```

---

## Documentation Index

- [**User Guide**](docs/user_guide.md): Domain ontology, forecasting semantics, Color-of-Money rules, and UI walkthrough.
- [**Architecture Specification**](docs/architecture.md): Hexagonal architecture, SQLite/DuckDB persistence, NetworkX projection engine, and custom SVG/DOM rendering.
- [**Developer & Contributing Guide**](docs/developer_guide.md): Setup, test suites, banned-token / offline compliance audits, and wheel packaging.
- [**API & SDK Reference**](docs/api_reference.md): Complete REST endpoint catalog, `bijou.sdk` methods, models, exceptions, and CLI flags.

---

## Testing & Quality Assurance

```bash
# Run full suite (unit, contract, adversarial, SDK, ingest, Selenium E2E, wheel check)
pytest tests -v

# Audit source code for banned tokens
python scripts/audit_banned_tokens.py

# Run pre-flight gate
python scripts/black_preflight_audit.py --root .

# Regenerate static OpenAPI schema snapshot
python scripts/export_openapi.py
```

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE).
