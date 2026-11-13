"""Canonical manifest interchange schema for Bijou v2."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from bijou.core.contracts.base import BijouBaseModel
from bijou.core.contracts.models import (
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    InterestInterestEdgeDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    ResourcePoolDTO,
)


class BijouManifestDTO(BijouBaseModel):
    """Point-in-time manifest representing the complete Bijou v2 entity and relationship graph."""

    schema_version: Literal["2.0.0"] = Field(default="2.0.0", alias="schema_version", description="Manifest schema version")
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="exported_at",
        description="Manifest export timestamp",
    )
    organizations: list[OrganizationDTO] = Field(default_factory=list, alias="organizations", description="Organizations")
    resource_pools: list[ResourcePoolDTO] = Field(default_factory=list, alias="resource_pools", description="Organization resource pools")
    interests: list[InterestDTO] = Field(default_factory=list, alias="interests", description="Strategic interests & concepts")
    efforts: list[EffortDTO] = Field(default_factory=list, alias="efforts", description="Capability efforts & programs")
    org_org_edges: list[OrgOrgEdgeDTO] = Field(default_factory=list, alias="org_org_edges", description="Org-to-Org relationships")
    org_interest_edges: list[OrgInterestEdgeDTO] = Field(
        default_factory=list, alias="org_interest_edges", description="Org-to-Interest stances & priorities"
    )
    interest_interest_edges: list[InterestInterestEdgeDTO] = Field(
        default_factory=list, alias="interest_interest_edges", description="Interest taxonomy hierarchy DAG"
    )
    org_effort_edges: list[OrgEffortEdgeDTO] = Field(
        default_factory=list, alias="org_effort_edges", description="Org-to-Effort direct resourcing"
    )
    effort_interest_edges: list[EffortInterestEdgeDTO] = Field(
        default_factory=list, alias="effort_interest_edges", description="Effort-to-Interest alignments"
    )
    effort_effort_edges: list[EffortEffortEdgeDTO] = Field(
        default_factory=list, alias="effort_effort_edges", description="Effort-to-Effort causal dependencies"
    )
