"""Tests for BijouDesktopBridge enabling zero-webserver in-process WebView hosting."""

import json
from pathlib import Path

import pytest

from bijou.config import BijouSettings
from bijou.web import BijouDesktopBridge


def _make_bridge(tmp_path: Path, name: str = "bridge") -> BijouDesktopBridge:
    return BijouDesktopBridge(
        settings=BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/{name}.db",
            duckdb_path=str(tmp_path / f"{name}.duckdb"),
            enable_reasoning=False,
        )
    )


def test_desktop_bridge_dispatch_and_rpc_roundtrip(tmp_path: Path) -> None:
    with _make_bridge(tmp_path, "rpc") as bridge:
        health = bridge.dispatch("GET", "/api/v1/health")
        assert health == {"ok": True, "status": 200, "data": {"status": "healthy", "engine": "bijou-v2"}}

        org_res = bridge.dispatch(
            "POST",
            "/api/v1/organizations",
            body={"id": "org-desk", "name": "Desktop Org", "is_managed": True},
        )
        assert org_res["ok"] is True
        assert org_res["status"] == 201
        assert org_res["data"]["id"] == "org-desk"

        # JSON-string single-call RPC mode (for PostWebMessage / QWebChannel)
        raw_resp = bridge.dispatch_json(
            json.dumps(
                {
                    "method": "POST",
                    "path": "/api/v1/efforts",
                    "body": {"id": "eff-desk", "name": "Desktop Effort"},
                }
            )
        )
        eff_res = json.loads(raw_resp)
        assert eff_res["ok"] is True
        assert eff_res["data"]["id"] == "eff-desk"

        bridge.dispatch(
            "POST",
            "/api/v1/organizations",
            body={"id": "org-other", "name": "Other Managed Org", "is_managed": True},
        )

        # Perspective boundary enforcement works identically to HTTP server
        denied = bridge.dispatch(
            "POST",
            "/api/v1/edges/org-effort",
            headers={
                "X-Bijou-Access-Mode": "MANAGED_ORG_OWNER",
                "X-Bijou-Active-Org": "org-desk",
            },
            body={"org_id": "org-other", "effort_id": "eff-desk", "allocation_amount": 5.0},
        )
        assert denied["ok"] is False
        assert denied["status"] == 403

        # Clean 404 propagation
        missing = bridge.dispatch("GET", "/api/v1/efforts/no-such-id")
        assert missing["ok"] is False
        assert missing["status"] == 404

        with pytest.raises(ValueError):
            bridge.dispatch("GET", "api/v1/health")


def test_desktop_bridge_serve_resource_and_html_rewriting(tmp_path: Path) -> None:
    with _make_bridge(tmp_path, "assets") as bridge:
        status, ctype, raw_index = bridge.serve_resource("GET", "/")
        assert status == 200
        assert "text/html" in ctype
        assert b"id=\"lens-canvas\"" in raw_index

        status_js, _, raw_js = bridge.serve_resource("GET", "/static/api.js")
        assert status_js == 200
        assert b"__BIJOU_BRIDGE__" in raw_js

        status_api, _, raw_api = bridge.serve_resource("GET", "/api/v1/health")
        assert status_api == 200
        assert b"bijou-v2" in raw_api

        desktop_html = bridge.render_desktop_html(use_file_base=True)
        assert "<base href=\"file:///" in desktop_html
        assert "window.__BIJOU_DESKTOP_MODE__ = true;" in desktop_html
        assert 'src="./app.js"' in desktop_html
        assert 'href="./styles.css"' in desktop_html
        assert 'src="/static/' not in desktop_html

        inlined_html = bridge.render_desktop_html(use_file_base=False, inline_assets=True)
        assert "<base href=" not in inlined_html
        assert "window.__BIJOU_DESKTOP_MODE__ = true;" in inlined_html
        assert "<style>" in inlined_html
        assert 'src="/static/' not in inlined_html
        assert 'href="/static/' not in inlined_html
