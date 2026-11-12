"""Integration tests for DuckDbTelemetryStore (v2 effort telemetry) and AuraRouterAdapter."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bijou.adapters.llm import AuraRouterAdapter
from bijou.adapters.telemetry import DuckDbTelemetryStore
from bijou.core.contracts import (
    AccessMode,
    AccumulatorPattern,
    EffortTelemetryEventDTO,
    PerspectiveBriefingDTO,
)
from bijou.core.ports import ServiceUnavailableError


def test_duckdb_effort_telemetry_ingestion_and_causal_trace(tmp_path: Path) -> None:
    db_path = str(tmp_path / "tel_v2.duckdb")
    store = DuckDbTelemetryStore(db_path=db_path)
    try:
        t0 = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
        ev1 = EffortTelemetryEventDTO(
            event_id="ev-root",
            effort_id="eff-optical",
            source_org_id="org-strat-space",
            causal_verb="DETECTED",
            occurred_at=t0,
            metric_name="link_margin_db",
            metric_value=8.2,
        )
        ev2 = EffortTelemetryEventDTO(
            event_id="ev-child",
            effort_id="eff-ai-fusion",
            source_org_id="org-joint-c2",
            causal_verb="TRIGGERED",
            occurred_at=t0 + timedelta(minutes=5),
            metric_name="frame_latency_ms",
            metric_value=195.0,
            causal_parent_ids=["ev-root"],
        )
        assert store.ingest_events([ev1, ev2]) == 2

        chain = store.trace_event_provenance("ev-child")
        ids = [c.event_id for c in chain]
        assert "ev-child" in ids and "ev-root" in ids

        rollup = store.compute_rollup(
            effort_id="eff-ai-fusion",
            metric_name="frame_latency_ms",
            accumulator=AccumulatorPattern.SUM,
            window_start=t0 - timedelta(minutes=1),
            window_end=t0 + timedelta(minutes=10),
        )
        assert rollup.aggregated_value == 195.0
    finally:
        store.close()


def test_aurarouter_adapter_raises_service_unavailable_when_offline() -> None:
    adapter = AuraRouterAdapter(aurarouter_url="http://nonexistent.invalid:9999", timeout=0.1)
    try:
        briefing = PerspectiveBriefingDTO(
            subject_org_id="org-joint-c2",
            active_access_mode=AccessMode.GLOBAL_ANALYST,
            as_of_date=datetime(2026, 11, 1, tzinfo=timezone.utc).date(),
            total_allocated_usd=250000.0,
        )
        with pytest.raises(ServiceUnavailableError):
            adapter.synthesize_executive_briefing(briefing, "Test mission")
    finally:
        adapter.close()
