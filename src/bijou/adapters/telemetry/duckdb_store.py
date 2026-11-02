"""DuckDB embedded analytical sidecar store for Tier-2 operational telemetry."""

import threading
from datetime import datetime, timezone

import duckdb

from bijou.core.contracts.enums import AccumulatorPattern
from bijou.core.contracts.telemetry import EffectEventDTO, TelemetryRollupDTO
from bijou.core.ports.telemetry_store import ITelemetryStore


class DuckDbTelemetryStore(ITelemetryStore):
    """Embedded DuckDB analytical telemetry store.

    Concurrency Model: Thread-safe columnar event storage; concurrent batch ingests and
    analytical window queries guarded by thread-safe cursor locks.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = duckdb.connect(database=db_path, read_only=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS effect_events (
                    event_id VARCHAR PRIMARY KEY,
                    thing_id VARCHAR NOT NULL,
                    milestone_id VARCHAR,
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
                CREATE TABLE IF NOT EXISTS event_causal_links (
                    parent_event_id VARCHAR NOT NULL,
                    child_event_id VARCHAR NOT NULL,
                    PRIMARY KEY (parent_event_id, child_event_id)
                );
            """)

    def close(self) -> None:
        """Close connection to DuckDB."""
        with self._lock:
            self._conn.close()

    def ingest_events(self, events: list[EffectEventDTO]) -> int:
        """Batch ingest operational effect events using parameterized queries."""
        if not events:
            return 0

        event_rows = [
            (
                e.event_id,
                e.thing_id,
                e.milestone_id,
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
                INSERT OR REPLACE INTO effect_events (
                    event_id, thing_id, milestone_id, source_org_id,
                    causal_verb, occurred_at, metric_name, metric_value,
                    confidence, raw_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                event_rows,
            )
            if link_rows:
                self._conn.executemany(
                    """
                    INSERT OR IGNORE INTO event_causal_links (
                        parent_event_id, child_event_id
                    ) VALUES (?, ?);
                    """,
                    link_rows,
                )

        return len(events)

    def compute_rollup(
        self,
        thing_id: str,
        metric_name: str,
        accumulator: AccumulatorPattern,
        window_start: datetime,
        window_end: datetime,
        sla_target: float | None = None,
    ) -> TelemetryRollupDTO:
        """Execute analytical aggregation rollup over an event time window using parameterized bindings."""
        with self._lock:
            # 1. Base counts and filter
            row = self._conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(metric_value), 0.0)
                FROM effect_events
                WHERE thing_id = ?
                  AND metric_name = ?
                  AND occurred_at >= ?
                  AND occurred_at <= ?;
                """,
                [thing_id, metric_name, window_start, window_end],
            ).fetchone()

            event_count = row[0] if row else 0
            agg_sum = row[1] if row else 0.0

            agg_value = 0.0
            max_depth = 1

            if accumulator == AccumulatorPattern.SUM:
                agg_value = float(agg_sum)

            elif accumulator == AccumulatorPattern.SLA_THRESHOLD:
                if event_count > 0 and sla_target is not None:
                    # Quantile calculation
                    p95_row = self._conn.execute(
                        """
                        SELECT quantile_cont(metric_value, 0.95)
                        FROM effect_events
                        WHERE thing_id = ?
                          AND metric_name = ?
                          AND occurred_at >= ?
                          AND occurred_at <= ?;
                        """,
                        [thing_id, metric_name, window_start, window_end],
                    ).fetchone()
                    p95_val = p95_row[0] if p95_row and p95_row[0] is not None else 999999.0
                    agg_value = 1.0 if p95_val <= sla_target else 0.0
                else:
                    agg_value = 0.0

            elif accumulator == AccumulatorPattern.CASCADE_DEPTH:
                # Compute maximum depth via recursive CTE starting from root events
                depth_row = self._conn.execute(
                    """
                    WITH RECURSIVE chain AS (
                        SELECT event_id AS current_id, 1 AS depth
                        FROM effect_events
                        WHERE thing_id = ?
                          AND metric_name = ?
                          AND occurred_at >= ?
                          AND occurred_at <= ?
                          AND event_id NOT IN (SELECT child_event_id FROM event_causal_links)
                        UNION ALL
                        SELECT l.child_event_id, c.depth + 1
                        FROM event_causal_links l
                        JOIN chain c ON l.parent_event_id = c.current_id
                        WHERE c.depth < 20
                    )
                    SELECT COALESCE(MAX(depth), 1) FROM chain;
                    """,
                    [thing_id, metric_name, window_start, window_end],
                ).fetchone()
                max_depth = int(depth_row[0]) if depth_row and depth_row[0] is not None else 1
                agg_value = float(max_depth)

            elif accumulator == AccumulatorPattern.YIELD_RATIO:
                ratio_row = self._conn.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE causal_verb IN ('CONFIRMED', 'SYNTHESIZED')) AS terminal_count,
                        COUNT(*) FILTER (WHERE causal_verb = 'COLLECTED') AS root_count
                    FROM effect_events
                    WHERE thing_id = ?
                      AND metric_name = ?
                      AND occurred_at >= ?
                      AND occurred_at <= ?;
                    """,
                    [thing_id, metric_name, window_start, window_end],
                ).fetchone()
                terminal_count = ratio_row[0] if ratio_row else 0
                root_count = ratio_row[1] if ratio_row else 0
                agg_value = float(terminal_count) / float(root_count) if root_count > 0 else 0.0

            return TelemetryRollupDTO(
                thing_id=thing_id,
                metric_name=metric_name,
                accumulator=accumulator,
                aggregated_value=round(agg_value, 4),
                event_count=event_count,
                max_cascade_depth=max_depth,
                window_start=window_start,
                window_end=window_end,
            )

    def trace_event_provenance(
        self,
        event_id: str,
        max_depth: int = 10,
    ) -> list[EffectEventDTO]:
        """Walk both upstream parents and downstream children using recursive CTE."""
        with self._lock:
            rows = self._conn.execute(
                """
                WITH RECURSIVE
                upstream AS (
                    SELECT parent_event_id AS id, 1 AS depth
                    FROM event_causal_links
                    WHERE child_event_id = ?
                    UNION ALL
                    SELECT l.parent_event_id, u.depth + 1
                    FROM event_causal_links l
                    JOIN upstream u ON l.child_event_id = u.id
                    WHERE u.depth < ?
                ),
                downstream AS (
                    SELECT child_event_id AS id, 1 AS depth
                    FROM event_causal_links
                    WHERE parent_event_id = ?
                    UNION ALL
                    SELECT l.child_event_id, d.depth + 1
                    FROM event_causal_links l
                    JOIN downstream d ON l.parent_event_id = d.id
                    WHERE d.depth < ?
                ),
                all_ids AS (
                    SELECT ? AS id
                    UNION
                    SELECT id FROM upstream
                    UNION
                    SELECT id FROM downstream
                )
                SELECT
                    e.event_id, e.thing_id, e.milestone_id, e.source_org_id,
                    e.causal_verb, e.occurred_at, e.metric_name, e.metric_value,
                    e.confidence, e.raw_ref
                FROM effect_events e
                JOIN all_ids a ON e.event_id = a.id
                ORDER BY e.occurred_at;
                """,
                [event_id, max_depth, event_id, max_depth, event_id],
            ).fetchall()

            # For each event, retrieve its parent IDs
            results: list[EffectEventDTO] = []
            for r in rows:
                ev_id = r[0]
                parents = [
                    p[0]
                    for p in self._conn.execute(
                        "SELECT parent_event_id FROM event_causal_links WHERE child_event_id = ?;",
                        [ev_id],
                    ).fetchall()
                ]
                # Ensure occurred_at has timezone
                occ_at = r[5]
                if occ_at.tzinfo is None:
                    occ_at = occ_at.replace(tzinfo=timezone.utc)

                results.append(
                    EffectEventDTO(
                        event_id=ev_id,
                        thing_id=r[1],
                        milestone_id=r[2],
                        source_org_id=r[3],
                        causal_verb=r[4],
                        occurred_at=occ_at,
                        metric_name=r[6],
                        metric_value=float(r[7]),
                        confidence=float(r[8]),
                        raw_ref=r[9],
                        causal_parent_ids=parents,
                    )
                )

            return results
