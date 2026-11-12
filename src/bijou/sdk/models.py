"""Canonical wire & domain models exposed by the Bijou v2 Python SDK."""

from bijou.core.contracts.enums import (
    AccessMode,
    AccumulatorPattern,
    BlockingMode,
    ConfidenceLevel,
    EffortInterestRelationType,
    EffortState,
    EffortTimingMode,
    ForecastHorizonStatus,
    InterestInterestRelationType,
    InterestKind,
    OrgInterestStance,
    OrgOrgRelationType,
    ResourceCategory,
    RiskSeverity,
    RiskStatus,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    DecisionLogEntryDTO,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    InterestInterestEdgeDTO,
    MitigatorDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrganizationDTO,
    OrgOrgEdgeDTO,
    PedigreeEdgeBase,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
)
from bijou.core.contracts.telemetry import EffortTelemetryEventDTO, TelemetryRollupDTO
from bijou.core.contracts.tools import ToolDescriptorDTO
from bijou.core.contracts.views import (
    AccessPerspectiveStateDTO,
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    DiagnosticReportDTO,
    DynamicOrgInterestPriorityDTO,
    EffortFocalDashboardDTO,
    ForecastedEffortNodeDTO,
    IndirectBenefitPathDTO,
    InterestFocalDashboardDTO,
    OrgFocalDashboardDTO,
    PerspectiveBriefingDTO,
    ResourcePoolBalanceDTO,
    SharedInterestPartnershipDTO,
    SimulatedPoolAllocationDTO,
    SkillMismatchWarningDTO,
    TriPartiteFlowViewDTO,
)

# Ergonomic SDK aliases alongside full *DTO names
Organization = OrganizationDTO
ResourcePool = ResourcePoolDTO
Interest = InterestDTO
ResourceRequirement = ResourceRequirementDTO
Risk = RiskDTO
Mitigator = MitigatorDTO
Effort = EffortDTO
PedigreeEdge = PedigreeEdgeBase
OrgOrgEdge = OrgOrgEdgeDTO
OrgInterestEdge = OrgInterestEdgeDTO
InterestInterestEdge = InterestInterestEdgeDTO
OrgEffortEdge = OrgEffortEdgeDTO
EffortInterestEdge = EffortInterestEdgeDTO
EffortEffortEdge = EffortEffortEdgeDTO
DecisionLogEntry = DecisionLogEntryDTO
EffortTelemetryEvent = EffortTelemetryEventDTO
TelemetryRollup = TelemetryRollupDTO
ToolDescriptor = ToolDescriptorDTO
ManifestPayload = BijouManifestDTO
ForecastedEffortNode = ForecastedEffortNodeDTO
CapabilityTreeView = CapabilityTreeViewDTO
TriPartiteFlowView = TriPartiteFlowViewDTO
BillOfEffortsSimulationRequest = BillOfEffortsSimulationRequestDTO
BillOfEffortsSimulationResult = BillOfEffortsSimulationResponseDTO
SimulatedPoolAllocation = SimulatedPoolAllocationDTO
EffortFocalDashboard = EffortFocalDashboardDTO
OrgFocalDashboard = OrgFocalDashboardDTO
InterestFocalDashboard = InterestFocalDashboardDTO
PerspectiveBriefing = PerspectiveBriefingDTO
DiagnosticReport = DiagnosticReportDTO
AccessPerspectiveState = AccessPerspectiveStateDTO

__all__ = [
    "AccessMode",
    "AccessPerspectiveState",
    "AccessPerspectiveStateDTO",
    "AccumulatorPattern",
    "BijouManifestDTO",
    "BillOfEffortsSimulationRequest",
    "BillOfEffortsSimulationRequestDTO",
    "BillOfEffortsSimulationResponseDTO",
    "BillOfEffortsSimulationResult",
    "BlockingMode",
    "CapabilityTreeView",
    "CapabilityTreeViewDTO",
    "ConfidenceLevel",
    "DecisionLogEntry",
    "DecisionLogEntryDTO",
    "DiagnosticReport",
    "DiagnosticReportDTO",
    "DynamicOrgInterestPriorityDTO",
    "Effort",
    "EffortDTO",
    "EffortEffortEdge",
    "EffortEffortEdgeDTO",
    "EffortFocalDashboard",
    "EffortFocalDashboardDTO",
    "EffortInterestEdge",
    "EffortInterestEdgeDTO",
    "EffortInterestRelationType",
    "EffortState",
    "EffortTelemetryEvent",
    "EffortTelemetryEventDTO",
    "EffortTimingMode",
    "ForecastHorizonStatus",
    "ForecastedEffortNode",
    "ForecastedEffortNodeDTO",
    "IndirectBenefitPathDTO",
    "Interest",
    "InterestDTO",
    "InterestFocalDashboard",
    "InterestFocalDashboardDTO",
    "InterestInterestEdge",
    "InterestInterestEdgeDTO",
    "InterestInterestRelationType",
    "InterestKind",
    "ManifestPayload",
    "Mitigator",
    "MitigatorDTO",
    "OrgEffortEdge",
    "OrgEffortEdgeDTO",
    "OrgFocalDashboard",
    "OrgFocalDashboardDTO",
    "OrgInterestEdge",
    "OrgInterestEdgeDTO",
    "OrgInterestStance",
    "OrgOrgEdge",
    "OrgOrgEdgeDTO",
    "OrgOrgRelationType",
    "Organization",
    "OrganizationDTO",
    "PedigreeEdge",
    "PedigreeEdgeBase",
    "PerspectiveBriefing",
    "PerspectiveBriefingDTO",
    "ResourceCategory",
    "ResourcePool",
    "ResourcePoolBalanceDTO",
    "ResourcePoolDTO",
    "ResourceRequirement",
    "ResourceRequirementDTO",
    "Risk",
    "RiskDTO",
    "RiskSeverity",
    "RiskStatus",
    "SharedInterestPartnershipDTO",
    "SimulatedPoolAllocation",
    "SimulatedPoolAllocationDTO",
    "SkillMismatchWarningDTO",
    "TelemetryRollup",
    "TelemetryRollupDTO",
    "ToolDescriptor",
    "ToolDescriptorDTO",
    "TriPartiteFlowView",
    "TriPartiteFlowViewDTO",
]
