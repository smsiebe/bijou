"""Bijou command-line interface entrypoint."""

import click
import uvicorn

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.web.desktop import launch_desktop


@click.command()
@click.option(
    "--mode",
    type=click.Choice(["desktop", "standalone", "api-only", "worker", "web-only", "export-snapshot"], case_sensitive=False),
    default="standalone",
    help="Deployment runtime mode.",
)
@click.option("--host", default=None, help="Host network interface to bind.")
@click.option("--port", type=int, default=None, help="Port to listen on.")
@click.option("--db-uri", default=None, help="Relational database connection URI.")
@click.option("--duckdb-path", default=None, help="Path to DuckDB telemetry database.")
@click.option("--aurarouter-url", default=None, help="URL for AuraRouter LLM endpoint.")
@click.option("--enable-reasoning/--no-reasoning", default=False, help="Enable AI reasoning.")
@click.option(
    "--export-snapshot",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Export an offline read-only Bijou snapshot ZIP archive and exit.",
)
def main(
    mode: str,
    host: str | None,
    port: int | None,
    db_uri: str | None,
    duckdb_path: str | None,
    aurarouter_url: str | None,
    enable_reasoning: bool,
    export_snapshot: str | None,
) -> None:
    """Bijou Multi-Echelon Causal Graph Engine CLI."""
    settings = BijouSettings()
    if mode:
        settings.mode = mode.lower()  # type: ignore[assignment]
    if host:
        settings.bind_host = host
    if port:
        settings.bind_port = port
    if db_uri:
        settings.db_uri = db_uri
    if duckdb_path:
        settings.duckdb_path = duckdb_path
    if aurarouter_url:
        settings.aurarouter_url = aurarouter_url
    if enable_reasoning:
        settings.enable_reasoning = enable_reasoning

    if export_snapshot or settings.mode == "export-snapshot":
        from bijou.adapters.db import SqlAlchemyGraphRepository
        from bijou.adapters.telemetry import DuckDbTelemetryStore
        from bijou.core.engine import InMemoryGraphProjectionEngine
        from bijou.services import BijouOrchestrationService, export_snapshot_to_file

        repo = SqlAlchemyGraphRepository(db_uri=settings.db_uri)
        telemetry_store = DuckDbTelemetryStore(db_path=settings.duckdb_path)
        projection_engine = InMemoryGraphProjectionEngine()
        orchestrator = BijouOrchestrationService(
            repository=repo,
            projection_engine=projection_engine,
            telemetry_store=telemetry_store,
            reasoning_broker=None,
        )
        orchestrator.initialize()

        target_file = export_snapshot or "bijou_snapshot.zip"
        out_path = export_snapshot_to_file(orchestrator, target_file)
        click.echo(f"Exported offline Bijou snapshot to: {out_path} ({out_path.stat().st_size:,} bytes)")
        return

    if settings.mode == "desktop":
        raise SystemExit(launch_desktop(settings))
    elif settings.mode in ("standalone", "api-only", "web-only"):
        app = create_app(settings)
        uvicorn.run(app, host=settings.bind_host, port=settings.bind_port)
    elif settings.mode == "worker":
        click.echo("Starting Bijou background projection worker...")
        # In worker mode, could poll or listen for projection update events
        click.echo("Worker initialized successfully.")


if __name__ == "__main__":
    main()
