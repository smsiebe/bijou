"""Canonical manifest interchange schema for Bijou."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.models import (
    CausalGateDTO,
    ConcernDTO,
    EffectDTO,
    GraphEdgeDTO,
    OrganizationDTO,
    ThingDTO,
)


class BijouManifestDTO(BijouBaseModel):
    """Point-in-time manifest representing the complete entity and edge graph."""

    schema_version: Literal["1.0.0"] = Field(default="1.0.0", alias="schema_version", description="Schema version")
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="exported_at",
        description="Manifest export timestamp",
    )
    organizations: list[OrganizationDTO] = Field(default_factory=list, alias="organizations", description="Organizations")
    concerns: list[ConcernDTO] = Field(default_factory=list, alias="concerns", description="Concerns")
    things: list[ThingDTO] = Field(default_factory=list, alias="things", description="Things")
    causal_gates: list[CausalGateDTO] = Field(default_factory=list, alias="causal_gates", description="Causal gates")
    effects: list[EffectDTO] = Field(default_factory=list, alias="effects", description="Effects")
    edges: list[GraphEdgeDTO] = Field(default_factory=list, alias="edges", description="Graph edges")
