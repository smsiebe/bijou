"""Configuration settings for Bijou loaded from environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BijouSettings(BaseSettings):
    """Runtime configuration for Bijou services."""

    model_config = SettingsConfigDict(
        env_prefix="BIJOU_",
        extra="ignore",
    )

    mode: Literal["standalone", "api-only", "worker", "web-only"] = "standalone"
    bind_host: str = Field(default="0.0.0.0", description="Network interface host to bind")
    bind_port: int = Field(default=8080, ge=1, le=65535, description="Port number to listen on")
    db_uri: str = Field(
        default="sqlite:///./bijou_graph.db",
        description="SQLAlchemy relational database connection URI",
    )
    duckdb_path: str = Field(
        default="./bijou_telemetry.duckdb",
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
