"""Export canonical OpenAPI 3.1 schema to docs/openapi.json."""

import json
from pathlib import Path

from bijou.api.app import create_app


def export_openapi() -> None:
    """Generate and write the deterministic OpenAPI 3.1 specification."""
    app_instance = create_app()
    openapi_schema = app_instance.openapi()
    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    out_path = docs_dir / "openapi.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, sort_keys=True)

    print(f"OpenAPI schema successfully exported to {out_path}")


if __name__ == "__main__":
    export_openapi()
