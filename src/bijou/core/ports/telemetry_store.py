"""Abstract port for high-cardinality Tier-2 event telemetry storage."""

from abc import ABC, abstractmethod
from datetime import datetime

from bijou.core.contracts.enums import AccumulatorPattern
from bijou.core.contracts.telemetry import EffectEventDTO, TelemetryRollupDTO


class ITelemetryStore(ABC):
    """Abstract port for high-cardinality Tier-2 operational event telemetry storage.

    Concurrency Model: Thread-safe columnar event storage; concurrent batch ingests and
    analytical window queries guarded by thread-safe cursor locks.
    """

    @abstractmethod
    def ingest_events(self, events: list[EffectEventDTO]) -> int:
        """Batch ingest operational effect events into the telemetry store."""

    @abstractmethod
    def compute_rollup(
        self,
        thing_id: str,
        metric_name: str,
        accumulator: AccumulatorPattern,
        window_start: datetime,
        window_end: datetime,
        sla_target: float | None = None,
    ) -> TelemetryRollupDTO:
        """Execute an analytical aggregation rollup over an event time window."""

    @abstractmethod
    def trace_event_provenance(
        self,
        event_id: str,
        max_depth: int = 10,
    ) -> list[EffectEventDTO]:
        """Walk upstream and downstream causal links to reconstruct event provenance."""
