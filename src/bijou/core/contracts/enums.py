"""Core domain enumerations for Bijou."""

from enum import StrEnum


class LifecycleStatus(StrEnum):
    """Lifecycle status for a Thing."""

    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    DELIVERED = "DELIVERED"
    DEPRECATED = "DEPRECATED"
    CANCELLED = "CANCELLED"
    RETIRED = "RETIRED"


class MilestoneStatus(StrEnum):
    """Execution status for a Milestone."""

    ESTIMATED = "ESTIMATED"
    COMMITTED = "COMMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    ACHIEVED = "ACHIEVED"
    SLIPPED = "SLIPPED"
    BLOCKED = "BLOCKED"


class TechTreeNodeState(StrEnum):
    """Resolved state of a node in the 4X tech tree."""

    ACHIEVED = "ACHIEVED"
    ACTIVE = "ACTIVE"
    UNLOCKED_READY = "UNLOCKED_READY"
    LOCKED = "LOCKED"
    BLOCKED = "BLOCKED"


class CausalMechanismType(StrEnum):
    """Evaluation mechanism for a Causal Gate."""

    ADDITIVE = "ADDITIVE"
    COMBINATORIAL_AND = "COMBINATORIAL_AND"
    THRESHOLD_K_OF_N = "THRESHOLD_K_OF_N"


class RelationshipType(StrEnum):
    """Typed relationship for edges in the Bijou graph."""

    PARENT_OF = "PARENT_OF"
    COLLABORATES_WITH = "COLLABORATES_WITH"
    PEER_OF = "PEER_OF"
    SUB_CONCERN_OF = "SUB_CONCERN_OF"
    OWNS = "OWNS"
    SUPPORTS = "SUPPORTS"
    IMPACTS = "IMPACTS"
    SATISFIES = "SATISFIES"
    DEPENDS_ON = "DEPENDS_ON"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    REPLACES = "REPLACES"


class EffectTier(StrEnum):
    """Tier categorization for observable Effects."""

    TIER_1_STRATEGIC = "TIER_1_STRATEGIC"
    TIER_2_OPERATIONAL = "TIER_2_OPERATIONAL"
    FEDERATED_VIRTUAL = "FEDERATED_VIRTUAL"


class AccumulatorPattern(StrEnum):
    """Aggregation pattern for rolling up events into effects."""

    SUM = "SUM"
    SLA_THRESHOLD = "SLA_THRESHOLD"
    CASCADE_DEPTH = "CASCADE_DEPTH"
    YIELD_RATIO = "YIELD_RATIO"


class TechTreeStratificationMode(StrEnum):
    """Horizontal stratification mode for 4X Tech Tree layout."""

    TRL_TIERS = "TRL_TIERS"
    FISCAL_ERA = "FISCAL_ERA"
    TOPOLOGICAL_DEPTH = "TOPOLOGICAL_DEPTH"
