"""CLI utility for batch ingesting manifests and telemetry into a running Bijou server."""

import os
import sys
from pathlib import Path

import click

from bijou.sdk.client import DEFAULT_BASE_URL, BijouClient
from bijou.sdk.ingest import ManifestIngestor


@click.command()
@click.option("--manifest", type=click.Path(dir_okay=False), default=None, help="Path to manifest YAML or JSON file.")
@click.option("--telemetry", type=click.Path(dir_okay=False), default=None, help="Path to telemetry JSONL event stream.")
@click.option(
    "--server-url",
    default=lambda: os.environ.get("BIJOU_SERVER_URL", DEFAULT_BASE_URL),
    help="Target Bijou server base URL.",
)
@click.option("--replace-all", is_flag=True, default=False, help="Replace existing graph instead of merging.")
@click.option("--validate-first", is_flag=True, default=False, help="Run pre-flight cycle/pool diagnostics first.")
def main(
    manifest: str | None,
    telemetry: str | None,
    server_url: str,
    replace_all: bool,
    validate_first: bool,
) -> None:
    """Batch document manifest and telemetry stream ingestor for Bijou v2."""
    if not manifest and not telemetry:
        click.echo("[bijou-ingest] Error: Specify at least one of --manifest or --telemetry.", err=True)
        sys.exit(1)

    try:
        with BijouClient(base_url=server_url) as client:
            ingestor = ManifestIngestor(client)

            if manifest:
                manifest_path = Path(manifest).resolve()
                click.echo(f"[bijou-ingest] Ingesting manifest: {manifest_path}...")
                counts = ingestor.ingest_manifest_file(
                    manifest_path,
                    replace_all=replace_all,
                    validate_first=validate_first,
                )
                click.echo(f"[bijou-ingest] Manifest imported: {counts}")

            if telemetry:
                telemetry_path = Path(telemetry).resolve()
                click.echo(f"[bijou-ingest] Ingesting telemetry: {telemetry_path}...")
                count = ingestor.ingest_telemetry_file(telemetry_path)
                click.echo(f"[bijou-ingest] Ingested {count} telemetry events.")
    except Exception as exc:
        click.echo(f"[bijou-ingest] Ingestion failed: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
