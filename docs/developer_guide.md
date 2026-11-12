# Bijou v2 Developer & Contributing Guide

---

## 1. Environment Setup

Bijou ships as a single Python package (`bijou`) containing the server, CLI (`bijou`, `bijou-ingest`), offline Web UI (`bijou/web/static/`), and Python SDK (`bijou.sdk`).

```bash
git clone https://github.com/smsiebe/bijou.git
cd bijou

python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS:        source .venv/bin/activate

pip install -e ".[dev]"
```

Run the standalone dev server:

```bash
bijou --mode standalone --port 8000
```

Or on Windows using the helper script (auto-seeds `%TEMP%\bijou_test` on first launch):

```bat
run_dev.bat
```

---

## 2. Repository Structure

```
bijou/
├── datasets/                  # Sample Joint ISR JSON/YAML manifests & JSONL telemetry
├── docs/                      # Architecture, User Guide, Developer Guide, API Ref & openapi.json
├── hooks/                     # AuraSeed post-install lifecycle hook
├── scripts/
│   ├── audit_banned_tokens.py # Offline/stub compliance scanner
│   ├── black_preflight_audit.py
│   ├── capture_gui_snapshots.py
│   ├── dev_seed.py            # Uses bijou.sdk.ManifestIngestor
│   └── export_openapi.py      # Regenerates docs/openapi.json
├── src/bijou/
│   ├── adapters/              # SQLAlchemy, DuckDB, AuraRouter implementations
│   ├── api/                   # FastAPI app factory, lifespan, middleware & v1 routers
│   ├── core/                  # Contracts (DTOs/Enums), Ports, NetworkX Engine
│   ├── sdk/                   # BijouClient, AsyncBijouClient, ManifestIngestor & CLI
│   ├── services/              # Orchestration & perspective enforcement
│   └── web/static/            # Pure Vanilla JS/CSS/SVG offline frontend bundle
└── tests/
    ├── adapters/
    ├── adversarial/
    ├── api/
    ├── contracts/
    ├── e2e/
    ├── engine/
    ├── ingest/
    ├── sdk/
    ├── services/
    └── web/
```

---

## 3. Compliance, Audits & Wheel Verification

Bijou enforces strict offline-first & packaging checks:
- **Offline Static Asset Audit**: Zero `http(s)://` CDN references in `src/bijou/web/static/`.
- **Banned Token Audit**: `python scripts/audit_banned_tokens.py` scans `src/` for hardcoded `localhost`, `127.0.0.1`, `TODO`, `FIXME`, or stubs.
- **Wheel Packaging Check**: `tests/web/test_web_ui_offline_compliance.py::test_wheel_bundle_includes_web_ui_and_sdk` builds a wheel via `setuptools.build_meta` and verifies that `bijou/web/static/*` and `bijou/sdk/*` are present in the `.whl`.

Run all checks:

```bash
pytest tests -v
python scripts/audit_banned_tokens.py
python scripts/black_preflight_audit.py --root .
ruff check src tests
```

---

## 4. Building & Publishing to PyPI

Because `pyproject.toml` includes `[tool.setuptools.package-data]` (`bijou = ["web/static/*"]`) and `MANIFEST.in`, a single `python -m build` produces a self-contained wheel and source distribution with the server, Web UI, CLI entrypoints (`bijou`, `bijou-ingest`), and `bijou.sdk`:

```bash
python -m build
twine check dist/*
# twine upload dist/*
```
