"""Static web UI offline-first compliance and Bijou v2 structural tests."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from bijou.api.app import app


def test_zero_external_cdn_links_in_static_bundle() -> None:
    """Asserts that all HTML, CSS, and JS static assets contain ZERO external HTTP/HTTPS CDN links."""
    static_dir = Path(__file__).parent.parent.parent / "src" / "bijou" / "web" / "static"
    assert static_dir.exists(), f"Static directory does not exist: {static_dir}"

    static_files = list(static_dir.glob("*.html")) + list(static_dir.glob("*.css")) + list(static_dir.glob("*.js"))
    assert len(static_files) >= 8, f"Expected at least 8 modular static asset files, found {len(static_files)}"

    url_pattern = re.compile(r"https?://(?!www\.w3\.org/)[^\s\"'>]+")

    violations = []
    for file_path in static_files:
        content = file_path.read_text(encoding="utf-8")
        matches = url_pattern.findall(content)
        if matches:
            violations.append((file_path.name, matches))

    assert not violations, f"Detected external URL dependencies in static bundle: {violations}"


def test_web_root_serves_v2_shell_and_assets() -> None:
    """Verifies web root serves Bijou v2 index.html with A/B/C canvas, BoE dock, Puck, Briefing & Studio."""
    client = TestClient(app)

    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "text/html" in resp_root.headers.get("content-type", "")
    body = resp_root.text

    assert 'id="lens-canvas"' in body
    assert 'id="btn-mode-a"' in body
    assert 'id="btn-mode-b"' in body
    assert 'id="btn-mode-c"' in body
    assert 'id="bill-of-efforts-dock"' in body
    assert 'id="briefing-one-pager"' in body
    assert 'id="lens-studio"' in body
    assert 'id="puck-backdrop"' in body
    assert 'id="perspective-select"' in body
    assert 'id="pedigree-select"' in body

    resp_asset = client.get("/static/app.js")
    assert resp_asset.status_code == 200
    assert "switchCanvasMode" in resp_asset.text


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
