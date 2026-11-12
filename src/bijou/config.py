"""Configuration settings for Bijou loaded from environment variables."""

import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_dir_writable(directory: Path) -> bool:
    """Return True if the given directory allows creating and removing files."""
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".bijou_write_probe_", delete=True):
            return True
    except OSError:
        return False


def _default_data_dir() -> Path:
    """Use CWD when writable, otherwise fall back to a writable user data directory."""
    cwd = Path.cwd()
    if _is_dir_writable(cwd):
        return cwd
    user_dir = Path.home() / ".bijou"
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def _default_db_uri() -> str:
    data_dir = _default_data_dir()
    if data_dir == Path.cwd():
        return "sqlite:///./bijou_graph.db"
    return f"sqlite:///{(data_dir / 'bijou_graph.db').as_posix()}"


def _default_duckdb_path() -> str:
    data_dir = _default_data_dir()
    if data_dir == Path.cwd():
        return "./bijou_telemetry.duckdb"
    return str(data_dir / "bijou_telemetry.duckdb")


class BijouSettings(BaseSettings):
    """Runtime configuration for Bijou services."""

    model_config = SettingsConfigDict(
        env_prefix="BIJOU_",
        extra="ignore",
    )

    mode: Literal["standalone", "api-only", "worker", "web-only"] = "standalone"
    bind_host: str = Field(default="0.0.0.0", description="Network interface host to bind")
    bind_port: int = Field(default=8000, ge=1, le=65535, description="Port number to listen on")
    db_uri: str = Field(
        default_factory=_default_db_uri,
        description="SQLAlchemy relational database connection URI",
    )
    duckdb_path: str = Field(
        default_factory=_default_duckdb_path,
        description="Path to embedded DuckDB telemetry database",
    )
    aurarouter_url: str | None = Field(
        default=None,
        description="URL for AuraRouter LLM reasoning endpoint",
    )
    aurarouter_model: str = Field(
        default="bijou-strategic-reasoner",
        description="Model identifier to request from AuraRouter",
    )
    max_payload_bytes: int = Field(
        default=10_485_760,
        description="Maximum request payload size in bytes (default 10MB)",
    )
    enable_reasoning: bool = Field(
        default=False,
        description="Whether to execute LLM reasoning calls during briefing generation",
    )
