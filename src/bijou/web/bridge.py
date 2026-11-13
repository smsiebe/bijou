"""In-process Desktop WebView Bridge for Bijou v2 (Zero TCP Ports / Zero Webserver).

Routes both static assets (/, /static/*) and REST calls (/api/v1/*) directly through
the FastAPI ASGI application via Starlette's in-memory TestClient so desktop hosts
(Tkinter + WebView2, pywebview, Qt QWebEngineView) run the full Bijou Web UI
without binding any network socket or duplicating backend logic.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from starlette.testclient import TestClient

from bijou.api.app import create_app
from bijou.config import BijouSettings


class BijouDesktopBridge:
    """In-process ASGI bridge connecting desktop WebViews directly to Bijou FastAPI."""

    def __init__(
        self,
        app: FastAPI | None = None,
        settings: BijouSettings | None = None,
        static_dir: Path | None = None,
    ) -> None:
        self.app: FastAPI = app or create_app(settings=settings)
        self.static_dir: Path = static_dir or (Path(__file__).resolve().parent / "static")
        self._client: TestClient | None = None
        self._lock = threading.RLock()

    def open(self) -> BijouDesktopBridge:
        """Initialize the in-process ASGI lifespan and client."""
        with self._lock:
            if self._client is None:
                client = TestClient(self.app, raise_server_exceptions=False)
                client.__enter__()
                self._client = client
        return self

    def close(self) -> None:
        """Tear down the in-process ASGI lifespan and database connections."""
        with self._lock:
            if self._client is not None:
                self._client.__exit__(None, None, None)
                self._client = None

    def __enter__(self) -> BijouDesktopBridge:
        return self.open()

    def __exit__(self, *args: object) -> None:
        self.close()

    def _ensure_client(self) -> TestClient:
        if self._client is None:
            self.open()
        assert self._client is not None
        return self._client

    def dispatch(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: Any = None,
    ) -> dict[str, Any]:
        """Execute a REST call in-process and return {ok, status, data}."""
        if not path.startswith("/"):
            raise ValueError(f"Bridge dispatch path must start with '/': {path!r}")

        client = self._ensure_client()
        req_headers = dict(headers or {})
        kwargs: dict[str, Any] = {"headers": req_headers}

        if body is not None:
            if isinstance(body, str):
                try:
                    kwargs["json"] = json.loads(body)
                except ValueError:
                    kwargs["content"] = body.encode("utf-8")
            else:
                kwargs["json"] = body

        with self._lock:
            client = self._ensure_client()
            resp = client.request(method.upper(), path, **kwargs)
        text = resp.text
        parsed: Any = None
        if text:
            try:
                parsed = resp.json()
            except ValueError:
                parsed = {"detail": text}

        return {
            "ok": bool(resp.is_success),
            "status": int(resp.status_code),
            "data": parsed,
        }

    def dispatch_json(self, request_json: str) -> str:
        """JSON-string RPC entrypoint for single-string WebView bridges."""
        req = json.loads(request_json)
        res = self.dispatch(
            method=req.get("method", "GET"),
            path=req["path"],
            headers=req.get("headers"),
            body=req.get("body"),
        )
        return json.dumps(res)

    def serve_resource(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        body: bytes | str | None = None,
    ) -> tuple[int, str, bytes]:
        """Serve /, /static/*, or /api/v1/* bytes for custom WebView URL scheme handlers."""
        if not path.startswith("/"):
            path = "/" + path
        with self._lock:
            client = self._ensure_client()
            kwargs: dict[str, Any] = {"headers": dict(headers or {})}
            if body is not None:
                kwargs["content"] = body.encode("utf-8") if isinstance(body, str) else body

            resp = client.request(method.upper(), path, **kwargs)
        content_type = resp.headers.get("content-type", "application/octet-stream")
        return int(resp.status_code), content_type, resp.content

    def render_desktop_html(
        self,
        use_file_base: bool = True,
        inline_assets: bool = False,
    ) -> str:
        """Return index.html prepared for direct HTML or file:// desktop WebView loading."""
        index_path = self.static_dir / "index.html"
        html = index_path.read_text(encoding="utf-8")

        if inline_assets:
            def _replace_css(match: re.Match[str]) -> str:
                rel = match.group(1).lstrip("/")
                css_file = self.static_dir / rel
                if css_file.is_file():
                    css_text = css_file.read_text(encoding="utf-8").replace("</style>", "<\\/style>")
                    return f"<style>\n{css_text}\n</style>"
                return match.group(0)

            def _replace_js(match: re.Match[str]) -> str:
                rel = match.group(1).lstrip("/")
                js_file = self.static_dir / rel
                if js_file.is_file():
                    js_text = js_file.read_text(encoding="utf-8").replace("</script>", "<\\/script>")
                    return f"<script>\n{js_text}\n</script>"
                return match.group(0)

            html = re.sub(
                r'<link\s+rel=["\']stylesheet["\']\s+href=["\']/static/([^"\']+)["\']\s*/?>',
                _replace_css,
                html,
            )
            html = re.sub(
                r'<script\s+src=["\']/static/([^"\']+)["\']\s*>\s*</script>',
                _replace_js,
                html,
            )

        desktop_marker = "<script>window.__BIJOU_DESKTOP_MODE__ = true;</script>"
        if use_file_base and not inline_assets:
            base_uri = self.static_dir.resolve().as_uri().rstrip("/") + "/"
            head_inject = f'  <base href="{base_uri}" />\n  {desktop_marker}\n</head>'
            html = html.replace('href="/static/', 'href="./').replace('src="/static/', 'src="./')
        else:
            head_inject = f"  {desktop_marker}\n</head>"

        return html.replace("</head>", head_inject, 1)
