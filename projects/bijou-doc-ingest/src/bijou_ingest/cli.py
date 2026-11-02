"""CLI entrypoint for bijou-ingest."""

import argparse
import sys
from pathlib import Path

from bijou_sdk import BijouClient
from bijou_ingest.ingestor import ManifestIngestor


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bijou-ingest",
        description="Batch document manifest and operational telemetry stream ingestor for Bijou."
    )
    parser.add_argument(
        "--manifest",
        type=str,
        help="Path to manifest YAML or JSON file."
    )
    parser.add_argument(
        "--telemetry",
        type=str,
        help="Path to telemetry JSONL event stream file."
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://localhost:8000",
        help="Bijou server endpoint URL (default: http://localhost:8000)."
    )
    parser.add_argument(
        "--replace-all",
        action="store_true",
        help="Replace existing entities in graph instead of merging."
    )

    args = parser.parse_args()

    if not args.manifest and not args.telemetry:
        print("[bijou-ingest] Error: At least one of --manifest or --telemetry must be specified.", file=sys.stderr)
        sys.exit(1)

    try:
        with BijouClient(base_url=args.server_url) as client:
            ingestor = ManifestIngestor(client)

            if args.manifest:
                manifest_path = Path(args.manifest).resolve()
                print(f"[bijou-ingest] Ingesting manifest from: {manifest_path}...")
                res = ingestor.ingest_manifest_file(manifest_path, replace_all=args.replace_all)
                print(f"[bijou-ingest] Manifest imported successfully: {res}")

            if args.telemetry:
                telemetry_path = Path(args.telemetry).resolve()
                print(f"[bijou-ingest] Ingesting telemetry events from: {telemetry_path}...")
                count = ingestor.ingest_telemetry_file(telemetry_path)
                print(f"[bijou-ingest] Successfully ingested {count} telemetry events.")

    except Exception as e:
        print(f"[bijou-ingest] Error: Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
