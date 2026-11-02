"""Tier-2 high-volume operational event telemetry DTOs."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.enums import AccumulatorPattern


class EffectEventDTO(BijouBaseModel):
    """High-volume operational event record in the provenance DAG."""

    event_id: str = Field(..., alias="event_id", description="Unique event ID")
    thing_id: str = Field(..., alias="thing_id", description="Producing Thing ID")
    milestone_id: str | None = Field(default=None, alias="milestone_id", description="Associated Milestone ID")
    source_org_id: str = Field(..., alias="source_org_id", description="Source Organization ID")
    causal_parent_ids: list[str] = Field(default_factory=list, alias="causal_parent_ids", description="Causal parent event IDs")
    causal_verb: Literal["COLLECTED", "DETECTED", "SYNTHESIZED", "TRIGGERED", "CONFIRMED"] = Field(
        ..., alias="causal_verb", description="Causal action verb"
    )
    occurred_at: datetime = Field(..., alias="occurred_at", description="Timestamp of event occurrence")
    metric_name: str = Field(..., alias="metric_name", description="Metric name")
    metric_value: float = Field(..., alias="metric_value", description="Metric value")
    confidence: float = Field(default=1.0, alias="confidence", ge=0.0, le=1.0, description="Confidence score")
    raw_ref: str | None = Field(default=None, alias="raw_ref", description="Raw payload reference pointer")


class TelemetryRollupDTO(BijouBaseModel):
    """Analytical rollup of Tier-2 events over a time window."""

    thing_id: str = Field(..., alias="thing_id", description="Target Thing ID")
    metric_name: str = Field(..., alias="metric_name", description="Aggregated metric name")
    accumulator: AccumulatorPattern = Field(..., alias="accumulator", description="Accumulator pattern applied")
    aggregated_value: float = Field(..., alias="aggregated_value", description="Computed aggregate value")
    event_count: int = Field(..., alias="event_count", ge=0, description="Total events in rollup window")
    max_cascade_depth: int = Field(..., alias="max_cascade_depth", ge=0, description="Maximum causal cascade depth")
    window_start: datetime = Field(..., alias="window_start", description="Aggregation window start timestamp")
    window_end: datetime = Field(..., alias="window_end", description="Aggregation window end timestamp")
