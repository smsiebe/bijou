"""Tests for Bijou v2 Python SDK (bijou-pysdk)."""

from pathlib import Path

import pytest

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou_sdk import (
    AccessMode,
    BijouClient,
    BijouValidationError,
    Effort,
    EffortEffortEdge,
    Organization,
)


def test_sdk_client_crud_perspective_and_views(tmp_path: Path) -> None:
    app = create_app(
        BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/sdk.db",
            duckdb_path=str(tmp_path / "sdk.duckdb"),
            enable_reasoning=False,
        )
    )
    with BijouClient(app=app) as client:
        assert client.health()["engine"] == "bijou-v2"

        client.upsert_organization(Organization(id="org-1", name="Org One", is_managed=True))
        client.upsert_effort(Effort(id="eff-1", name="Effort One"))
        client.upsert_effort(Effort(id="eff-2", name="Effort Two"))
        client.upsert_effort_effort_edge(
            EffortEffortEdge(source_effort_id="eff-1", target_effort_id="eff-2")
        )

        # Cycle check raises BijouValidationError (422)
        with pytest.raises(BijouValidationError):
            client.upsert_effort_effort_edge(
                EffortEffortEdge(source_effort_id="eff-2", target_effort_id="eff-1")
            )

        client.set_perspective(AccessMode.MANAGED_ORG_OWNER, "org-1")
        view_a = client.get_capability_tree()
        assert len(view_a.nodes) == 2

        briefing = client.get_perspective_briefing("org-1")
        assert briefing["active_access_mode"] == "MANAGED_ORG_OWNER"
