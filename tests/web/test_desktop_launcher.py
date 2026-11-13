"""Tests for desktop window launcher (`bijou --mode desktop`) and icon resolution."""

import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from bijou import cli
from bijou.config import BijouSettings
from bijou.web import desktop


def test_resolve_icon_path_prefers_explicit_and_falls_back_to_static(tmp_path: Path) -> None:
    custom_ico = tmp_path / "custom.ico"
    custom_ico.write_bytes(b"\x00\x00\x01\x00")
    assert desktop._resolve_icon_path(custom_ico) == custom_ico.resolve()

    missing_ico = tmp_path / "missing.ico"
    resolved_default = desktop._resolve_icon_path(missing_ico)
    assert resolved_default is not None
    assert resolved_default.name == "bijou.ico"
    assert resolved_default.is_file()


def test_launch_desktop_uses_pywebview_and_inlined_bridge_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_create_window(title: str, **kwargs: object) -> None:
        captured["title"] = title
        captured.update(kwargs)

    def fake_start(icon: str | None = None) -> None:
        captured["started_icon"] = icon

    fake_webview = SimpleNamespace(create_window=fake_create_window, start=fake_start)
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    settings = BijouSettings(
        mode="desktop",
        db_uri=f"sqlite:///{tmp_path}/desktop.db",
        duckdb_path=str(tmp_path / "desktop.duckdb"),
    )
    rc = desktop.launch_desktop(settings=settings)
    assert rc == 0
    assert "Bijou" in str(captured["title"])
    assert "<style>" in str(captured["html"])
    assert "window.__BIJOU_DESKTOP_MODE__ = true;" in str(captured["html"])
    assert captured["js_api"] is not None
    assert str(captured["started_icon"]).endswith("bijou.ico")


def test_launch_desktop_logs_warning_and_falls_back_on_pywebview_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def boom(*args: object, **kwargs: object) -> int:
        raise RuntimeError("no webview backend")

    fallback_calls: list[BijouSettings] = []

    def fake_fallback(settings: BijouSettings) -> int:
        fallback_calls.append(settings)
        return 0

    monkeypatch.setattr(desktop, "_launch_pywebview_desktop", boom)
    monkeypatch.setattr(desktop, "_launch_loopback_app_window", fake_fallback)

    settings = BijouSettings(
        mode="desktop",
        db_uri=f"sqlite:///{tmp_path}/fallback.db",
        duckdb_path=str(tmp_path / "fallback.duckdb"),
    )
    with caplog.at_level(logging.WARNING, logger=desktop.logger.name):
        rc = desktop.launch_desktop(settings=settings)

    assert rc == 0
    assert len(fallback_calls) == 1
    assert "falling back to loopback app window" in caplog.text


def test_cli_desktop_mode_invokes_launch_desktop(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[BijouSettings] = []

    def fake_launch_desktop(settings: BijouSettings) -> int:
        seen.append(settings)
        return 0

    monkeypatch.setattr(cli, "launch_desktop", fake_launch_desktop)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--mode", "desktop"])
    assert result.exit_code == 0
    assert len(seen) == 1
    assert seen[0].mode == "desktop"
