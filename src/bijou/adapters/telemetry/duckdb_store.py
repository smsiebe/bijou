"""DuckDB embedded analytical sidecar store for Tier-2 Effort telemetry."""

import threading
from datetime import datetime, timezone

import duckdb

from bijou.core.contracts.enums import AccumulatorPattern
from bijou.core.contracts.telemetry import EffortTelemetryEventDTO, TelemetryRollupDTO
from bijou.core.ports.telemetry_store import ITelemetryStore


class DuckDbTelemetryStore(ITelemetryStore):
    """Thread-safe columnar telemetry store keyed by effort_id and source_org_id."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = duckdb.connect(database=db_path, read_only=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS effort_telemetry_events (
                    event_id VARCHAR PRIMARY KEY,
                    effort_id VARCHAR NOT NULL,
                    source_org_id VARCHAR NOT NULL,
                    causal_verb VARCHAR NOT NULL,
                    occurred_at TIMESTAMP NOT NULL,
                    metric_name VARCHAR NOT NULL,
                    metric_value DOUBLE NOT NULL,
                    confidence DOUBLE NOT NULL,
                    raw_ref VARCHAR
                );
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS effort_event_causal_links (
                    parent_event_id VARCHAR NOT NULL,
                    child_event_id VARCHAR NOT NULL,
                    PRIMARY KEY (parent_event_id, child_event_id)
                );
            """)

    def close(self) -> None:
        """Close connection to DuckDB."""
        with self._lock:
            self._conn.close()

    def ingest_events(self, events: list[EffortTelemetryEventDTO]) -> int:
        """Batch ingest operational Effort telemetry events using parameterized queries."""
        if not events:
            return 0

        event_rows = [
            (
                e.event_id,
                e.effort_id,
                e.source_org_id,
                e.causal_verb,
                e.occurred_at,
                e.metric_name,
                e.metric_value,
                e.confidence,
                e.raw_ref,
            )
            for e in events
        ]

        link_rows: list[tuple[str, str]] = []
        for e in events:
            for parent_id in e.causal_parent_ids:
                link_rows.append((parent_id, e.event_id))

        with self._lock:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO effort_telemetry_events (
                    event_id, effort_id, source_org_id,
                    causal_verb, occurred_at, metric_name, metric_value,
                    confidence, raw_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                event_rows,
            )
            if link_rows:
                self._conn.executemany(
                    """
                    INSERT OR IGNORE INTO effort_event_causal_links (
                        parent_event_id, child_event_id
                    ) VALUES (?, ?);
                    """,
                    link_rows,
                )

        return len(events)

    def compute_rollup(
        self,
        effort_id: str,
        metric_name: str,
        accumulator: AccumulatorPattern,
        window_start: datetime,
        window_end: datetime,
        sla_target: float | None = None,
    ) -> TelemetryRollupDTO:
        """Execute analytical aggregation rollup over an event window using parameterized bindings."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(metric_value), 0.0)
                FROM effort_telemetry_events
                WHERE effort_id = ?
                  AND metric_name = ?
                  AND occurred_at >= ?
                  AND occurred_at <= ?;
                """,
                [effort_id, metric_name, window_start, window_end],
            ).fetchone()

            event_count = row[0] if row else 0
            agg_sum = row[1] if row else 0.0

            agg_value = 0.0
            max_depth = 1

            if accumulator == AccumulatorPattern.SUM:
                agg_value = float(agg_sum)
            elif accumulator == AccumulatorPattern.SLA_THRESHOLD:
                if event_count > 0 and sla_target is not None:
                    p95_row = self._conn.execute(
                        """
                        SELECT quantile_cont(metric_value, 0.95)
                        FROM effort_telemetry_events
                        WHERE effort_id = ?
                          AND metric_name = ?
                          AND occurred_at >= ?
                          AND occurred_at <= ?;
                        """,
                        [effort_id, metric_name, window_start, window_end],
                    ).fetchone()
                    p95_val = p95_row[0] if p95_row and p95_row[0] is not None else 999999.0
                    agg_value = 1.0 if p95_val <= sla_target else 0.0
            elif accumulator == AccumulatorPattern.CASCADE_DEPTH:
                depth_row = self._conn.execute(
                    """
                    WITH RECURSIVE chain AS (
                        SELECT event_id AS current_id, 1 AS depth
                        FROM effort_telemetry_events
                        WHERE effort_id = ?
                          AND metric_name = ?
                          AND occurred_at >= ?
                          AND occurred_at <= ?
                          AND event_id NOT IN (SELECT child_event_id FROM effort_event_causal_links)
                        UNION ALL
                        SELECT l.child_event_id, c.depth + 1
                        FROM effort_event_causal_links l
                        JOIN chain c ON l.parent_event_id = c.current_id
                        WHERE c.depth < 20
                    )
                    SELECT COALESCE(MAX(depth), 1) FROM chain;
                    """,
                    [effort_id, metric_name, window_start, window_end],
                ).fetchone()
                max_depth = int(depth_row[0]) if depth_row and depth_row[0] is not None else 1
                agg_value = float(max_depth)
            elif accumulator == AccumulatorPattern.YIELD_RATIO:
                ratio_row = self._conn.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE causal_verb IN ('CONFIRMED', 'SYNTHESIZED')) AS terminal_count,
                        COUNT(*) FILTER (WHERE causal_verb = 'COLLECTED') AS root_count
                    FROM effort_telemetry_events
                    WHERE effort_id = ?
                      AND metric_name = ?
                      AND occurred_at >= ?
                      AND occurred_at <= ?;
                    """,
                    [effort_id, metric_name, window_start, window_end],
                ).fetchone()
                terminal_count = ratio_row[0] if ratio_row else 0
                root_count = ratio_row[1] if ratio_row else 0
                agg_value = float(terminal_count) / float(root_count) if root_count > 0 else 0.0

            return TelemetryRollupDTO(
                effort_id=effort_id,
                metric_name=metric_name,
                accumulator=accumulator,
                aggregated_value=agg_value,
                event_count=event_count,
                max_cascade_depth=max_depth,
                window_start=window_start,
                window_end=window_end,
            )

    def list_metrics_for_effort(self, effort_id: str) -> list[str]:
        """List distinct metric names recorded for a specific Effort."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT DISTINCT metric_name
                FROM effort_telemetry_events
                WHERE effort_id = ?
                ORDER BY metric_name;
                """,
                [effort_id],
            ).fetchall()
            return [r[0] for r in rows]

    def trace_event_provenance(
        self,
        event_id: str,
        max_depth: int = 10,
    ) -> list[EffortTelemetryEventDTO]:
        """Walk causal lineage using parameterized recursive CTE."""
        with self._lock:
            rows = self._conn.execute(
                """
                WITH RECURSIVE anc AS (
                    SELECT parent_event_id AS eid, 1 AS depth
                    FROM effort_event_causal_links
                    WHERE child_event_id = ?
                    UNION
                    SELECT l.parent_event_id, anc.depth + 1
                    FROM effort_event_causal_links l
                    JOIN anc ON l.child_event_id = anc.eid
                    WHERE anc.depth < ?
                ),
                desc_chain AS (
                    SELECT child_event_id AS eid, 1 AS depth
                    FROM effort_event_causal_links
                    WHERE parent_event_id = ?
                    UNION
                    SELECT l.child_event_id, desc_chain.depth + 1
                    FROM effort_event_causal_links l
                    JOIN desc_chain ON l.parent_event_id = desc_chain.eid
                    WHERE desc_chain.depth < ?
                ),
                all_ids AS (
                    SELECT ? AS eid
                    UNION
                    SELECT eid FROM anc
                    UNION
                    SELECT eid FROM desc_chain
                )
                SELECT
                    e.event_id, e.effort_id, e.source_org_id,
                    e.causal_verb, e.occurred_at, e.metric_name, e.metric_value,
                    e.confidence, e.raw_ref
                FROM effort_telemetry_events e
                JOIN all_ids a ON e.event_id = a.eid
                ORDER BY e.occurred_at ASC;
                """,
                [event_id, max_depth, event_id, max_depth, event_id],
            ).fetchall()

            results: list[EffortTelemetryEventDTO] = []
            for r in rows:
                eid = r[0]
                parent_rows = self._conn.execute(
                    "SELECT parent_event_id FROM effort_event_causal_links WHERE child_event_id = ?;",
                    [eid],
                ).fetchall()
                parents = [pr[0] for pr in parent_rows]
                occ = r[4]
                if occ.tzinfo is None:
                    occ = occ.replace(tzinfo=timezone.utc)
                results.append(
                    EffortTelemetryEventDTO(
                        event_id=eid,
                        effort_id=r[1],
                        source_org_id=r[2],
                        causal_parent_ids=parents,
                        causal_verb=r[3],
                        occurred_at=occ,
                        metric_name=r[5],
                        metric_value=r[6],
                        confidence=r[7],
                        raw_ref=r[8],
                    )
                )
            return results
