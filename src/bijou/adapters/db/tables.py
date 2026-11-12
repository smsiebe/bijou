"""SQLAlchemy 2.0 ORM table models for Bijou v2 relational storage."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM mappings."""


class OrganizationRecord(Base):
    """Table mapping for Organizations (managed or externally modeled)."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    echelon_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ResourcePoolRecord(Base):
    """Table mapping for Organization ResourcePools & earmarked budget pools."""

    __tablename__ = "resource_pools"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(64), default="USD", nullable=False)
    skill_tag: Mapped[str | None] = mapped_column(String(128), nullable=True)
    restricted_interest_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str] = mapped_column(String(2048), default="", nullable=False)


class InterestRecord(Base):
    """Table mapping for Strategic Interests, Priorities, Gaps, and Concepts."""

    __tablename__ = "interests"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    interest_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)


class EffortRecord(Base):
    """Table mapping for Efforts, storing requirements, risks, and mitigators as structured JSON."""

    __tablename__ = "efforts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    estimated_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource_requirements: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    risks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    mitigators: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


# --- Six Typed Relationship Edge Tables ---


class OrgOrgEdgeRecord(Base):
    __tablename__ = "org_org_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class OrgInterestEdgeRecord(Base):
    __tablename__ = "org_interest_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    interest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    stance: Mapped[str] = mapped_column(String(64), nullable=False)
    priority_rank: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    allow_hierarchy_inheritance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class InterestInterestEdgeRecord(Base):
    __tablename__ = "interest_interest_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    parent_interest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    child_interest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class OrgEffortEdgeRecord(Base):
    __tablename__ = "org_effort_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    effort_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resourcing_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_pool_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requirement_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    allocation_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    allocation_unit: Mapped[str] = mapped_column(String(64), default="UNITS", nullable=False)
    assigned_skill: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_generic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class EffortInterestEdgeRecord(Base):
    __tablename__ = "effort_interest_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    effort_id: Mapped[str] = mapped_column(String(128), nullable=False)
    interest_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class EffortEffortEdgeRecord(Base):
    __tablename__ = "effort_effort_edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_effort_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_effort_id: Mapped[str] = mapped_column(String(128), nullable=False)
    blocking_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_degree: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="CONFIRMED", nullable=False)
    provenance_note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)


class DecisionLogRecord(Base):
    """Audit ledger table for decision provenance and rationale."""

    __tablename__ = "decision_logs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    target_effort_id: Mapped[str] = mapped_column(String(128), nullable=False)
    author: Mapped[str] = mapped_column(String(256), nullable=False)
    justification: Mapped[str] = mapped_column(String(2048), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
