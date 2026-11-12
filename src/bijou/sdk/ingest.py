"""Batch manifest and operational telemetry ingestion utilities for Bijou v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from bijou.sdk.client import BijouClient
from bijou.sdk.exceptions import BijouValidationError
from bijou.sdk.models import BijouManifestDTO


def validate_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """Resolve and validate that target_path resides strictly within base_dir.

    Raises:
        ValueError: If path traversal or escaping base_dir is detected.
        FileNotFoundError: If the target file does not exist.
    """
    base_resolved = Path(base_dir).resolve()
    target = Path(target_path)

    if target.is_absolute():
        resolved_target = target.resolve()
    else:
        resolved_target = (base_resolved / target).resolve()

    try:
        resolved_target.relative_to(base_resolved)
    except ValueError as err:
        raise ValueError(
            f"Path traversal detected: target '{target_path}' resolves to '{resolved_target}', "
            f"which is outside base directory '{base_resolved}'"
        ) from err

    if not resolved_target.exists():
        raise FileNotFoundError(f"File not found: {resolved_target}")

    return resolved_target


class ManifestIngestor:
    """Batch document manifest and telemetry stream ingestor backed by BijouClient."""

    def __init__(self, client: BijouClient) -> None:
        self.client = client

    def ingest_manifest_payload(
        self,
        manifest: BijouManifestDTO | dict[str, Any],
        replace_all: bool = False,
        validate_first: bool = False,
    ) -> dict[str, int]:
        """Validate and atomically import an in-memory manifest payload or DTO."""
        dto = manifest if isinstance(manifest, BijouManifestDTO) else BijouManifestDTO.model_validate(manifest)
        if validate_first:
            report = self.client.validate_manifest(dto)
            if report.blockers:
                raise BijouValidationError(
                    f"Manifest validation failed with blockers: {'; '.join(report.blockers)}",
                    status_code=422,
                    detail=report.model_dump(mode="json"),
                )
        return self.client.import_manifest(dto, replace_all=replace_all)

    def ingest_manifest_file(
        self,
        file_path: str | Path,
        base_dir: str | Path | None = None,
        replace_all: bool = False,
        validate_first: bool = False,
    ) -> dict[str, int]:
        """Ingest a YAML or JSON Bijou v2 manifest file."""
        if base_dir is not None:
            safe_path = validate_safe_path(base_dir, file_path)
        else:
            safe_path = Path(file_path).resolve()
            if not safe_path.exists():
                raise FileNotFoundError(f"File not found: {safe_path}")

        raw_text = safe_path.read_text(encoding="utf-8")
        if safe_path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(raw_text)
        else:
            data = json.loads(raw_text)

        return self.ingest_manifest_payload(data, replace_all=replace_all, validate_first=validate_first)

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

        return self.client.ingest_telemetry_events(events)
