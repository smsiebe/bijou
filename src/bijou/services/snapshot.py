"""Bijou v2 Offline Snapshot Export Service.

Generates self-contained, air-gapped, read-only HTML/CSS/JS + Data ZIP archives
that require zero Python runtime, zero local webservers, and zero external CDNs.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bijou.services.orchestrator import BijouOrchestrationService


def build_snapshot_data(
    orchestrator: BijouOrchestrationService,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Assemble complete pre-computed portfolio views, focal dashboards, and briefings."""
    eff_date = as_of_date or date.today()

    manifest = orchestrator.export_manifest().model_dump(mode="json")
    perspective_ctx = orchestrator.resolve_access_context()
    perspective = orchestrator.get_perspective_state(perspective_ctx).model_dump(mode="json")

    orgs = [o.model_dump(mode="json") for o in orchestrator.list_organizations()]
    pools = [p.model_dump(mode="json") for p in orchestrator.list_resource_pools()]
    interests = [i.model_dump(mode="json") for i in orchestrator.list_interests()]
    efforts = [e.model_dump(mode="json") for e in orchestrator.list_efforts()]
    decisions = [d.model_dump(mode="json") for d in orchestrator.list_decision_logs()]
    diagnostics = orchestrator.validate_manifest_diagnostics().model_dump(mode="json")
    tools = [t.model_dump(mode="json") for t in orchestrator.list_tools()]

    cap_tree = orchestrator.get_capability_tree_view(as_of_date=eff_date).model_dump(mode="json")
    tri_flow = orchestrator.get_tripartite_flow_view(as_of_date=eff_date).model_dump(mode="json")

    efforts_focal: dict[str, Any] = {}
    for eff in orchestrator.list_efforts():
        try:
            efforts_focal[eff.id] = orchestrator.get_effort_focal_dashboard(
                eff.id, as_of_date=eff_date
            ).model_dump(mode="json")
        except Exception:
            pass

    orgs_focal: dict[str, Any] = {}
    for org in orchestrator.list_organizations():
        try:
            orgs_focal[org.id] = orchestrator.get_org_focal_dashboard(
                org.id, as_of_date=eff_date
            ).model_dump(mode="json")
        except Exception:
            pass

    interests_focal: dict[str, Any] = {}
    for intr in orchestrator.list_interests():
        try:
            interests_focal[intr.id] = orchestrator.get_interest_focal_dashboard(
                intr.id, as_of_date=eff_date
            ).model_dump(mode="json")
        except Exception:
            pass

    orgs_briefing: dict[str, Any] = {}
    for org in orchestrator.list_organizations():
        try:
            orgs_briefing[org.id] = orchestrator.get_perspective_briefing(
                org.id, as_of_date=eff_date
            ).model_dump(mode="json")
        except Exception:
            pass

    efforts_briefing: dict[str, Any] = {}
    for eff in orchestrator.list_efforts():
        try:
            efforts_briefing[eff.id] = orchestrator.get_effort_briefing(
                eff.id, as_of_date=eff_date
            ).model_dump(mode="json")
        except Exception:
            pass

    meta = {
        "version": "2.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": eff_date.isoformat(),
        "read_only": True,
        "title": "Bijou Strategic Portfolio Offline Snapshot",
    }

    return {
        "meta": meta,
        "health": {
            "status": "healthy",
            "engine": "bijou-v2-snapshot",
            "mode": "read_only",
            "as_of_date": eff_date.isoformat(),
        },
        "perspective": perspective,
        "manifest": manifest,
        "organizations": orgs,
        "resource_pools": pools,
        "interests": interests,
        "efforts": efforts,
        "decisions": decisions,
        "diagnostics": diagnostics,
        "tools": tools,
        "views": {
            "capability_tree": cap_tree,
            "tripartite_flow": tri_flow,
        },
        "focal": {
            "efforts": efforts_focal,
            "organizations": orgs_focal,
            "interests": interests_focal,
        },
        "briefings": {
            "organizations": orgs_briefing,
            "efforts": efforts_briefing,
        },
    }


def build_snapshot_zip_bytes(
    orchestrator: BijouOrchestrationService,
    static_dir: Path | None = None,
    as_of_date: date | None = None,
) -> bytes:
    """Build in-memory self-contained ZIP archive bytes for the offline snapshot."""
    dir_path = static_dir or (Path(__file__).parent.parent / "web" / "static")
    snapshot_data = build_snapshot_data(orchestrator, as_of_date=as_of_date)

    # Escape '</' sequences so inline <script> injection cannot be broken by entity text
    data_json = json.dumps(snapshot_data, indent=2, ensure_ascii=False).replace("</", "<\\/")
    snapshot_data_js = (
        "/* ==========================================================================\n"
        "   Bijou v2 Precomputed Portfolio Snapshot Store\n"
        "   Generated at: " + snapshot_data["meta"]["exported_at"] + "\n"
        "   ========================================================================== */\n\n"
        "(function (global) {\n"
        "  'use strict';\n"
        f"  global.__BIJOU_SNAPSHOT__ = {data_json};\n"
        "})(window);\n"
    )

    index_path = dir_path / "index.html"
    index_html = index_path.read_text(encoding="utf-8")

    # Ensure relative paths for file:// protocol compatibility
    index_html = index_html.replace('href="/static/', 'href="./static/')
    index_html = index_html.replace('src="/static/', 'src="./static/')

    # Ensure snapshot_data.js and offline_adapter.js are included
    if "snapshot_data.js" not in index_html:
        index_html = index_html.replace(
            '<script src="./static/api.js"></script>',
            '<script src="./static/snapshot_data.js"></script>\n  '
            '<script src="./static/offline_adapter.js"></script>\n  '
            '<script src="./static/api.js"></script>',
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write root index.html
        zf.writestr("index.html", index_html.encode("utf-8"))

        # Write generated snapshot_data.js into static/
        zf.writestr("static/snapshot_data.js", snapshot_data_js.encode("utf-8"))

        # Write all static assets into static/
        for asset in dir_path.glob("*"):
            if not asset.is_file():
                continue
            if asset.name in ("index.html", "snapshot_data.js"):
                continue
            zf.write(asset, arcname=f"static/{asset.name}")

    return buf.getvalue()


def export_snapshot_to_file(
    orchestrator: BijouOrchestrationService,
    output_path: Path | str,
    static_dir: Path | None = None,
    as_of_date: date | None = None,
) -> Path:
    """Export snapshot ZIP directly to a disk path."""
    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    zip_bytes = build_snapshot_zip_bytes(orchestrator, static_dir=static_dir, as_of_date=as_of_date)
    out.write_bytes(zip_bytes)
    return out

