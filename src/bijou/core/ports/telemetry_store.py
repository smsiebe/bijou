"""Abstract port for high-cardinality Tier-2 Effort event telemetry storage."""

from abc import ABC, abstractmethod
from datetime import datetime

from bijou.core.contracts.enums import AccumulatorPattern
from bijou.core.contracts.telemetry import EffortTelemetryEventDTO, TelemetryRollupDTO


class ITelemetryStore(ABC):
    """Abstract port for high-cardinality Tier-2 operational telemetry storage.

    Concurrency Model: Thread-safe columnar event storage; concurrent batch ingests and
    analytical window queries guarded by thread-safe cursor locks.
    """

    @abstractmethod
    def ingest_events(self, events: list[EffortTelemetryEventDTO]) -> int:
        """Batch ingest operational telemetry events into DuckDB."""

    @abstractmethod
    def compute_rollup(
        self,
        effort_id: str,
        metric_name: str,
        accumulator: AccumulatorPattern,
        window_start: datetime,
        window_end: datetime,
        sla_target: float | None = None,
    ) -> TelemetryRollupDTO:
        """Execute an analytical aggregation rollup over an event time window."""

    @abstractmethod
    def list_metrics_for_effort(self, effort_id: str) -> list[str]:
        """List distinct metric names recorded for a specific Effort."""

    @abstractmethod
    def trace_event_provenance(
        self,
        event_id: str,
        max_depth: int = 10,
    ) -> list[EffortTelemetryEventDTO]:
        """Walk upstream and downstream causal links to reconstruct event provenance."""
