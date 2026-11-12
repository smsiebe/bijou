"""Batch document manifest and operational telemetry stream ingestor."""

import json
from pathlib import Path
from typing import Any

import yaml
from bijou_sdk import BijouClient, ManifestPayload

from .path_utils import validate_safe_path


class ManifestIngestor:
    """Ingestor consuming BijouClient to load YAML/JSON manifests and telemetry streams."""

    def __init__(self, client: BijouClient) -> None:
        self.client = client

    def ingest_manifest_file(
        self,
        file_path: str | Path,
        base_dir: str | Path | None = None,
        replace_all: bool = False,
    ) -> dict[str, Any]:
        """Ingest a manifest YAML or JSON document."""
        if base_dir is not None:
            safe_path = validate_safe_path(base_dir, file_path)
        else:
            safe_path = Path(file_path).resolve()
            if not safe_path.exists():
                raise FileNotFoundError(f"File not found: {safe_path}")

        raw_text = safe_path.read_text(encoding="utf-8")
        if safe_path.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(raw_text)
        else:
            data = json.loads(raw_text)

        # Validate against SDK ManifestPayload model
        manifest = ManifestPayload.model_validate(data)

        # Import via BijouClient
        return self.client.import_manifest(manifest, replace_all=replace_all)

    def ingest_telemetry_file(
        self,
        file_path: str | Path,
        base_dir: str | Path | None = None,
    ) -> int:
        """Ingest streaming telemetry events from a JSONL document."""
        if base_dir is not None:
            safe_path = validate_safe_path(base_dir, file_path)
        else:
            safe_path = Path(file_path).resolve()
            if not safe_path.exists():
                raise FileNotFoundError(f"File not found: {safe_path}")

        events: list[dict[str, Any]] = []
        with safe_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    events.append(json.loads(stripped))

        if not events:
            return 0

        resp = self.client._request("POST", "/api/v1/telemetry/events", json=events)
        res_data = resp.json()
        return res_data.get("ingested", res_data.get("ingested_count", len(events)))
