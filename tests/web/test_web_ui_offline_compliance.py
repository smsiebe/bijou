"""Static web UI offline-first compliance and Bijou v2 structural tests."""

import re
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from setuptools import build_meta as _build_meta

from bijou.api.app import app


def test_zero_external_cdn_links_in_static_bundle() -> None:
    """Asserts that all HTML, CSS, and JS static assets contain ZERO external HTTP/HTTPS CDN links."""
    static_dir = Path(__file__).parent.parent.parent / "src" / "bijou" / "web" / "static"
    assert static_dir.exists(), f"Static directory does not exist: {static_dir}"

    static_files = list(static_dir.glob("*.html")) + list(static_dir.glob("*.css")) + list(static_dir.glob("*.js"))
    assert len(static_files) >= 10, f"Expected at least 10 modular static asset files, found {len(static_files)}"

    url_pattern = re.compile(r"https?://(?!www\.w3\.org/)[^\s\"'>]+")

    violations = []
    for file_path in static_files:
        content = file_path.read_text(encoding="utf-8")
        matches = url_pattern.findall(content)
        if matches:
            violations.append((file_path.name, matches))

    assert not violations, f"Detected external URL dependencies in static bundle: {violations}"


def test_web_root_serves_v2_shell_and_assets() -> None:
    """Verifies web root serves Bijou v2 shell with Tree/Tri-Partite/Global Neural modes, Cart Dock & Graph Editor."""
    client = TestClient(app)

    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")
    body = resp_root.text

    assert 'id="lens-canvas"' in body
    assert 'id="btn-mode-a"' in body
    assert 'id="btn-mode-b"' in body
    assert 'id="btn-mode-neural"' in body
    assert 'id="btn-mode-c"' not in body
    assert 'id="bill-of-efforts-dock"' in body
    assert 'id="btn-toggle-dock"' in body
    assert 'id="briefing-one-pager"' in body
    assert 'id="lens-studio"' in body
    assert 'id="puck-backdrop"' in body
    assert 'id="perspective-select"' in body
    assert 'id="pedigree-select"' in body

    resp_asset = client.get("/static/app.js")
    assert resp_asset.status_code == 200
    assert "switchCanvasMode" in resp_asset.text

    resp_neural = client.get("/static/view_global_neural.js")
    assert resp_neural.status_code == 200
    assert "renderGlobalNeuralGraph" in resp_neural.text

    resp_editor = client.get("/static/graph_editor.js")
    assert resp_editor.status_code == 200
    assert "BijouGraphEditor" in resp_editor.text


def test_print_stylesheet_present_for_one_slide_briefing() -> None:
    """Verifies @media print and @page CSS rules are defined for single-landscape print output."""
    static_dir = Path(__file__).parent.parent.parent / "src" / "bijou" / "web" / "static"
    css_file = static_dir / "styles.css"
    assert css_file.exists()

    css_content = css_file.read_text(encoding="utf-8")
    assert "@page" in css_content
    assert "size: landscape" in css_content
    assert "@media print" in css_content
    assert "#briefing-one-pager" in css_content


def test_wheel_bundle_includes_web_ui_and_sdk(tmp_path: Path, monkeypatch) -> None:
    """Verifies built wheel includes Web UI static bundle and integrated bijou.sdk package."""
    root_dir = Path(__file__).parent.parent.parent
    monkeypatch.chdir(root_dir)
    whl_name = _build_meta.build_wheel(str(tmp_path))
    whl_path = tmp_path / whl_name
    assert whl_path.exists()

    with zipfile.ZipFile(whl_path) as zf:
        names = set(zf.namelist())

    expected_assets = {
        "bijou/web/static/index.html",
        "bijou/web/static/app.js",
        "bijou/web/static/styles.css",
        "bijou/web/static/api.js",
        "bijou/web/static/graph_editor.js",
        "bijou/web/static/view_a_dag.js",
        "bijou/web/static/view_b_tripartite.js",
        "bijou/web/static/view_global_neural.js",
        "bijou/web/static/view_c_dock.js",
        "bijou/web/static/entity_puck.js",
        "bijou/web/static/briefing.js",
        "bijou/web/static/studio.js",
        "bijou/sdk/__init__.py",
        "bijou/sdk/client.py",
        "bijou/sdk/ingest.py",
    }
    missing = sorted(expected_assets - names)
    assert not missing, f"Built wheel missing Web UI / SDK files: {missing}"
