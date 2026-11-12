"""Core domain enumerations for Bijou v2."""

from enum import StrEnum


class EffortState(StrEnum):
    """Execution lifecycle state for an Effort."""

    COMPLETED = "COMPLETED"
    IN_WORK = "IN_WORK"
    BACKLOGGED = "BACKLOGGED"
    PLANNED = "PLANNED"
    DISCOVERY_PENDING = "DISCOVERY_PENDING"
    CANCELLED = "CANCELLED"


class EffortTimingMode(StrEnum):
    """Resolved or declared timing certainty mode for an Effort."""

    EXPLICIT_DATES = "EXPLICIT_DATES"
    DURATION_ONLY = "DURATION_ONLY"
    UNKNOWN = "UNKNOWN"


class ForecastHorizonStatus(StrEnum):
    """Solver-resolved schedule horizon state for capability forecasting."""

    COMPLETED_HISTORICAL = "COMPLETED_HISTORICAL"
    EXPLICIT_SCHEDULE = "EXPLICIT_SCHEDULE"
    OPEN_ENDED_ACTIVE = "OPEN_ENDED_ACTIVE"
    RELATIVE_TO_DEPENDENCY = "RELATIVE_TO_DEPENDENCY"
    UNSCHEDULED_PLAN = "UNSCHEDULED_PLAN"
    CANCELLED = "CANCELLED"


class InterestKind(StrEnum):
    """Categorical nature of an Interest node."""

    STRATEGIC_CONCEPT = "STRATEGIC_CONCEPT"
    MISSION_GOAL = "MISSION_GOAL"
    NIPF_PRIORITY = "NIPF_PRIORITY"
    THREAT_VECTOR = "THREAT_VECTOR"
    INTELLIGENCE_GAP = "INTELLIGENCE_GAP"
    CUSTOMER = "CUSTOMER"
    INVESTMENT = "INVESTMENT"
    COUNTRY = "COUNTRY"
    CAPABILITY_AREA = "CAPABILITY_AREA"
    OTHER = "OTHER"


class ConfidenceLevel(StrEnum):
    """Intelligence pedigree / confidence tier for graph relationships."""

    CONFIRMED = "CONFIRMED"
    ASSESSED = "ASSESSED"
    UNCONFIRMED = "UNCONFIRMED"


class ResourceCategory(StrEnum):
    """Category of resource required or provided for an Effort."""

    MONEY = "MONEY"
    STAFF = "STAFF"
    COMPUTE = "COMPUTE"
    MATERIAL = "MATERIAL"
    GENERIC_SUPPORT = "GENERIC_SUPPORT"


class OrgOrgRelationType(StrEnum):
    """Typed inter-organization relationship."""

    HIERARCHICAL_PARENT = "HIERARCHICAL_PARENT"
    FORMAL_SUPPORTING = "FORMAL_SUPPORTING"
    COLLABORATIVE_ADJACENT = "COLLABORATIVE_ADJACENT"
    CO_SPONSOR = "CO_SPONSOR"


class OrgInterestStance(StrEnum):
    """Nature of an Organization's relationship to an Interest."""

    RESPONSIBLE_OWNER = "RESPONSIBLE_OWNER"
    DIRECT_INVESTOR = "DIRECT_INVESTOR"
    BENEFICIARY = "BENEFICIARY"
    PERCEIVED_GAP = "PERCEIVED_GAP"
    MISSION_ALIGNED = "MISSION_ALIGNED"


class InterestInterestRelationType(StrEnum):
    """Directed edge type inside the Interest taxonomy DAG."""

    SPECIALIZES = "SPECIALIZES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    RELATED_TO = "RELATED_TO"


class EffortInterestRelationType(StrEnum):
    """Typed alignment between an Effort and an Interest."""

    DIRECT_SOLUTION = "DIRECT_SOLUTION"
    INDIRECT_ENABLER = "INDIRECT_ENABLER"
    FUNDED_FOR = "FUNDED_FOR"
    PARTIAL_ALIGNMENT = "PARTIAL_ALIGNMENT"


class BlockingMode(StrEnum):
    """Dependency blocking behavior between upstream and downstream Efforts."""

    BLOCKING = "BLOCKING"
    NON_BLOCKING_INFORMS = "NON_BLOCKING_INFORMS"


class RiskSeverity(StrEnum):
    """Severity tier of an Effort Risk."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskStatus(StrEnum):
    """Active resolution status of a Risk."""

    ACTIVE = "ACTIVE"
    MITIGATED = "MITIGATED"
    REALIZED = "REALIZED"


class AccessMode(StrEnum):
    """Workspace perspective / authorization mode."""

    GLOBAL_ANALYST = "GLOBAL_ANALYST"
    MANAGED_ORG_OWNER = "MANAGED_ORG_OWNER"


class WorkspaceViewMode(StrEnum):
    """A/B/C Canvas Visualization Modes."""

    VIEW_A_DAG = "VIEW_A_DAG"
    VIEW_B_TRIPARTITE = "VIEW_B_TRIPARTITE"
    VIEW_C_WORKBENCH = "VIEW_C_WORKBENCH"


class AccumulatorPattern(StrEnum):
    """Aggregation pattern for rolling up telemetry events."""

    SUM = "SUM"
    SLA_THRESHOLD = "SLA_THRESHOLD"
    CASCADE_DEPTH = "CASCADE_DEPTH"
    YIELD_RATIO = "YIELD_RATIO"
