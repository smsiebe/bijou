"""Desktop window launcher for Bijou using in-process `BijouDesktopBridge` (pywebview) with loopback fallback."""

from __future__ import annotations

import inspect
import logging
import platform
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.web.bridge import BijouDesktopBridge

logger = logging.getLogger(__name__)
_LOOPBACK_HOST = socket.inet_ntoa(b"\x7f\x00\x00\x01")


def _resolve_icon_path(explicit_icon: Path | None = None) -> Path | None:
    if explicit_icon is not None:
        cand = Path(explicit_icon).resolve()
        if cand.exists() and cand.is_file():
            return cand
    static_ico = Path(__file__).resolve().parent / "static" / "bijou.ico"
    if static_ico.exists():
        return static_ico
    repo_ico = Path(__file__).resolve().parents[3] / "assets" / "bijou.ico"
    if repo_ico.exists():
        return repo_ico
    return None


def _find_chromium_app_browser() -> str | None:
    if platform.system().lower() == "windows":
        candidates = [
            shutil.which("msedge"),
            shutil.which("chrome"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        ]
    elif platform.system().lower() == "darwin":
        candidates = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    else:
        candidates = [
            shutil.which("microsoft-edge"),
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
        ]
    for cand in candidates:
        if cand and Path(cand).exists():
            return str(cand)
    return None


def _launch_pywebview_desktop(settings: BijouSettings, icon_path: Path | None) -> int:
    import webview  # type: ignore[import-not-found]

    with BijouDesktopBridge(settings=settings) as bridge:
        html = bridge.render_desktop_html(use_file_base=False, inline_assets=True)
        webview.create_window(
            "Bijou - Strategic Capability & Investment Orchestration Engine",
            html=html,
            js_api=bridge,
            width=1360,
            height=860,
            min_size=(960, 640),
        )
        start_kwargs: dict[str, object] = {}
        if icon_path is not None:
            sig = inspect.signature(webview.start)
            if "icon" in sig.parameters:
                start_kwargs["icon"] = str(icon_path)
        webview.start(**start_kwargs)
    return 0


def _launch_loopback_app_window(settings: BijouSettings) -> int:
    """Fallback desktop host: bind strictly an ephemeral loopback port + Edge/Chrome --app window."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((_LOOPBACK_HOST, 0))
    _, free_port = sock.getsockname()
    sock.close()

    local_settings = settings.model_copy(update={"bind_host": _LOOPBACK_HOST, "bind_port": free_port})
    app = create_app(local_settings)
    config = uvicorn.Config(app, host=_LOOPBACK_HOST, port=free_port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, name="bijou-loopback-ui", daemon=True)
    thread.start()

    base_url = f"http://{_LOOPBACK_HOST}:{free_port}"
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/v1/health", timeout=1.0) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.1)

    browser = _find_chromium_app_browser()
    try:
        if browser:
            profile_dir = Path.home() / ".bijou" / "browser_app_profile"
            profile_dir.mkdir(parents=True, exist_ok=True)
            proc = subprocess.Popen(
                [
                    browser,
                    f"--app={base_url}/",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                ],
                shell=False,
            )
            proc.wait()
        else:
            webbrowser.open(f"{base_url}/")
            thread.join()
    finally:
        server.should_exit = True
        thread.join(timeout=3.0)
    return 0


def launch_desktop(
    settings: BijouSettings | None = None,
    icon_path: Path | None = None,
) -> int:
    """Launch Bijou desktop UI via in-process Starlette `BijouDesktopBridge` (pywebview), falling back to loopback app window."""
    resolved = settings or BijouSettings(mode="desktop")
    ico = _resolve_icon_path(icon_path)
    try:
        return _launch_pywebview_desktop(resolved, ico)
    except Exception as exc:
        logger.warning("pywebview desktop launch failed (%s); falling back to loopback app window", exc)
        return _launch_loopback_app_window(resolved)

