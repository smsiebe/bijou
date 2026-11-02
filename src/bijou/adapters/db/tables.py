"""SQLAlchemy 2.0 ORM table models for Bijou relational storage."""

from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM mappings."""


class OrganizationRecord(Base):
    """Table mapping for Organization entities."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    echelon_level: Mapped[int] = mapped_column(Integer, nullable=False)
    mission_statement: Mapped[str] = mapped_column(String(2048), nullable=False)
    parent_org_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    peer_org_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ConcernRecord(Base):
    """Table mapping for Concern entities."""

    __tablename__ = "concerns"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    owner_org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_concern_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority: Mapped[float] = mapped_column(Float, nullable=False)
    target_metric_sla: Mapped[float | None] = mapped_column(Float, nullable=True)


class ThingRecord(Base):
    """Table mapping for Thing deliverables/programs."""

    __tablename__ = "things"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    lifecycle: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_org_id: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False)
    risk_factor: Mapped[float] = mapped_column(Float, nullable=False)

    milestones: Mapped[list["MilestoneRecord"]] = relationship(
        "MilestoneRecord",
        back_populates="thing",
        cascade="all, delete-orphan",
        order_by="MilestoneRecord.sequence_index",
    )


class MilestoneRecord(Base):
    """Table mapping for Thing phased Milestones."""

    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    thing_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("things.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_date: Mapped[date] = mapped_column(nullable=False)
    actual_date: Mapped[date | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_delta: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    lane: Mapped[str] = mapped_column(String(128), nullable=False)
    trl: Mapped[int] = mapped_column(Integer, nullable=False)

    thing: Mapped[ThingRecord] = relationship("ThingRecord", back_populates="milestones")


class CausalGateRecord(Base):
    """Table mapping for Causal Gate nodes."""

    __tablename__ = "causal_gates"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    mechanism: Mapped[str] = mapped_column(String(64), nullable=False)
    threshold_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contributors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)


class EffectRecord(Base):
    """Table mapping for Effect observable outcomes."""

    __tablename__ = "effects"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    tier: Mapped[str] = mapped_column(String(64), nullable=False)
    causal_gate_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accumulator: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    satisfies_concerns: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    federation_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class EdgeRecord(Base):
    """Table mapping for typed graph edges."""

    __tablename__ = "edges"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_milestone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_milestone_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effective_start: Mapped[date | None] = mapped_column(nullable=True)
    effective_end: Mapped[date | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("idx_edge_source_rel", "source_id", "relationship"),
        Index("idx_edge_target_rel", "target_id", "relationship"),
    )
