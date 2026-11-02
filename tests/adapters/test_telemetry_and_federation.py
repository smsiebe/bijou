"""Unit, provenance cascade, and security fuzzing tests for DuckDbTelemetryStore and HttpFederationConnector."""

from datetime import datetime, timezone

import pytest

from bijou.adapters.federation import HttpFederationConnector
from bijou.adapters.telemetry import DuckDbTelemetryStore
from bijou.core.contracts import (
    AccumulatorPattern,
    EffectEventDTO,
    FederationSpecDTO,
)
from bijou.core.ports.exceptions import ServiceUnavailableError


@pytest.fixture
def telemetry_store() -> DuckDbTelemetryStore:
    """Fixture providing in-memory DuckDbTelemetryStore."""
    store = DuckDbTelemetryStore(":memory:")
    yield store
    store.close()


def test_duckdb_cascade_depth_and_yield_ratio_rollup(telemetry_store: DuckDbTelemetryStore) -> None:
    """Ingests a 3-stage satellite collect -> detection -> intel report DAG and verifies cascade depth and yield ratio."""
    store = telemetry_store
    t0 = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Stage 1: 100 Collect events (root events)
    events: list[EffectEventDTO] = []
    for i in range(100):
        events.append(
            EffectEventDTO(
                event_id=f"ev-collect-{i}",
                thing_id="th-sensor",
                source_org_id="org-space",
                causal_verb="COLLECTED",
                occurred_at=t0,
                metric_name="satellite_imagery_chain",
                metric_value=1.0,
            )
        )

    # 2. Stage 2: 25 Detection events (each links to 4 collects as parents)
    for i in range(25):
        parent_ids = [f"ev-collect-{i * 4 + j}" for j in range(4)]
        events.append(
            EffectEventDTO(
                event_id=f"ev-detect-{i}",
                thing_id="th-sensor",
                source_org_id="org-space",
                causal_parent_ids=parent_ids,
                causal_verb="DETECTED",
                occurred_at=t0,
                metric_name="satellite_imagery_chain",
                metric_value=2.0,
            )
        )

    # 3. Stage 3: 5 Intel Reports (terminal confirmed events; each links to 5 detections)
    for i in range(5):
        parent_ids = [f"ev-detect-{i * 5 + j}" for j in range(5)]
        events.append(
            EffectEventDTO(
                event_id=f"ev-report-{i}",
                thing_id="th-sensor",
                source_org_id="org-space",
                causal_parent_ids=parent_ids,
                causal_verb="CONFIRMED",
                occurred_at=t0,
                metric_name="satellite_imagery_chain",
                metric_value=5.0,
            )
        )

    # Ingest batch
    ingested = store.ingest_events(events)
    assert ingested == 130

    # Test CASCADE_DEPTH: 3 levels (COLLECT -> DETECT -> REPORT)
    rollup_depth = store.compute_rollup(
        thing_id="th-sensor",
        metric_name="satellite_imagery_chain",
        accumulator=AccumulatorPattern.CASCADE_DEPTH,
        window_start=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert rollup_depth.aggregated_value == 3.0
    assert rollup_depth.max_cascade_depth == 3

    # Test YIELD_RATIO: 5 terminal CONFIRMED / 100 root COLLECTED = 0.05
    rollup_yield = store.compute_rollup(
        thing_id="th-sensor",
        metric_name="satellite_imagery_chain",
        accumulator=AccumulatorPattern.YIELD_RATIO,
        window_start=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert rollup_yield.aggregated_value == 0.05


def test_federation_connector_raises_service_unavailable_when_offline() -> None:
    """Verifies that querying an unreachable endpoint with empty cache raises ServiceUnavailableError."""
    connector = HttpFederationConnector()
    spec = FederationSpecDTO(
        connector_id="mock-remote",
        query_template="http://240.0.0.1:9999/api/telemetry/rollup",  # reserved unroutable IP
        params={"cluster": "tactical-node-1"},
        accumulator=AccumulatorPattern.SUM,
        cache_ttl_seconds=300,
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        connector.execute_federated_rollup(
            spec=spec,
            window_start=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
        )

    assert "unreachable and no valid cache found" in str(exc_info.value)
    connector.close()


def test_duckdb_parameterized_queries_reject_sql_injection(telemetry_store: DuckDbTelemetryStore) -> None:
    """Passes malicious SQL string and verifies table integrity remains intact."""
    store = telemetry_store
    malicious_id = "th-1'; DROP TABLE effect_events; --"

    # Should safely query 0 results without executing DROP TABLE
    rollup = store.compute_rollup(
        thing_id=malicious_id,
        metric_name="any_metric",
        accumulator=AccumulatorPattern.SUM,
        window_start=datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 11, 1, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert rollup.event_count == 0

    # Verify table still exists and functions normally
    normal_event = EffectEventDTO(
        event_id="ev-safe-1",
        thing_id="th-safe",
        source_org_id="org-safe",
        causal_verb="COLLECTED",
        occurred_at=datetime.now(timezone.utc),
        metric_name="safe_metric",
        metric_value=42.0,
    )
    count = store.ingest_events([normal_event])
    assert count == 1
