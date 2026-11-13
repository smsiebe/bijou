"""FastAPI v1 REST API route definitions for Bijou v2 ontology & A/B/C workspace views."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bijou.api.deps import get_access_context, get_orchestrator
from bijou.core.contracts.enums import ConfidenceLevel
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    DecisionLogEntryDTO,
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
from bijou.core.contracts.telemetry import EffortTelemetryEventDTO
from bijou.core.contracts.tools import ToolDescriptorDTO
from bijou.core.contracts.views import (
    AccessPerspectiveStateDTO,
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    DiagnosticReportDTO,
    EffortFocalDashboardDTO,
    InterestFocalDashboardDTO,
    OrgFocalDashboardDTO,
    PerspectiveBriefingDTO,
    TriPartiteFlowViewDTO,
)
from bijou.core.ports.access_control import AccessContext

v1_router = APIRouter(prefix="/api/v1")

OrchestratorDep = Annotated[Any, Depends(get_orchestrator)]
AccessContextDep = Annotated[AccessContext, Depends(get_access_context)]


# --- Perspective / Access Context ---
@v1_router.get(
    "/perspective",
    response_model=AccessPerspectiveStateDTO,
    status_code=status.HTTP_200_OK,
    summary="Get active access perspective state & managed organizations",
    operation_id="get_access_perspective_state",
)
def get_perspective_state(
    orchestrator: OrchestratorDep,
    access_ctx: AccessContextDep,
) -> AccessPerspectiveStateDTO:
    return orchestrator.get_perspective_state(access_ctx)


# --- Organization Routes ---
@v1_router.post(
    "/organizations",
    response_model=OrganizationDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an Organization",
    operation_id="upsert_organization",
)
def upsert_organization(org: OrganizationDTO, orchestrator: OrchestratorDep) -> OrganizationDTO:
    return orchestrator.upsert_organization(org)


@v1_router.get(
    "/organizations",
    response_model=list[OrganizationDTO],
    status_code=status.HTTP_200_OK,
    summary="List all Organizations",
    operation_id="list_organizations",
)
def list_organizations(orchestrator: OrchestratorDep) -> list[OrganizationDTO]:
    return orchestrator.list_organizations()


@v1_router.get(
    "/organizations/{org_id}",
    response_model=OrganizationDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Organization by ID",
    operation_id="get_organization",
)
def get_organization(org_id: str, orchestrator: OrchestratorDep) -> OrganizationDTO:
    org = orchestrator.get_organization(org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organization '{org_id}' not found")
    return org


@v1_router.delete(
    "/organizations/{org_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete Organization by ID",
    operation_id="delete_organization",
)
def delete_organization(org_id: str, orchestrator: OrchestratorDep) -> dict[str, bool]:
    return {"deleted": orchestrator.delete_entity("organization", org_id)}


# --- Resource Pool Routes ---
@v1_router.post(
    "/resource-pools",
    response_model=ResourcePoolDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a Resource Pool",
    operation_id="upsert_resource_pool",
)
def upsert_resource_pool(
    pool: ResourcePoolDTO,
    orchestrator: OrchestratorDep,
    access_ctx: AccessContextDep,
) -> ResourcePoolDTO:
    return orchestrator.upsert_resource_pool(pool, context=access_ctx)


@v1_router.get(
    "/resource-pools",
    response_model=list[ResourcePoolDTO],
    status_code=status.HTTP_200_OK,
    summary="List Resource Pools",
    operation_id="list_resource_pools",
)
def list_resource_pools(
    orchestrator: OrchestratorDep,
    org_id: str | None = Query(default=None),
) -> list[ResourcePoolDTO]:
    return orchestrator.list_resource_pools(org_id=org_id)


@v1_router.delete(
    "/resource-pools/{pool_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete Resource Pool by ID",
    operation_id="delete_resource_pool",
)
def delete_resource_pool(pool_id: str, orchestrator: OrchestratorDep) -> dict[str, bool]:
    return {"deleted": orchestrator.delete_entity("resource_pool", pool_id)}


# --- Interest Routes ---
@v1_router.post(
    "/interests",
    response_model=InterestDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an Interest",
    operation_id="upsert_interest",
)
def upsert_interest(interest: InterestDTO, orchestrator: OrchestratorDep) -> InterestDTO:
    return orchestrator.upsert_interest(interest)


@v1_router.get(
    "/interests",
    response_model=list[InterestDTO],
    status_code=status.HTTP_200_OK,
    summary="List all Interests",
    operation_id="list_interests",
)
def list_interests(orchestrator: OrchestratorDep) -> list[InterestDTO]:
    return orchestrator.list_interests()


@v1_router.get(
    "/interests/{interest_id}",
    response_model=InterestDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Interest by ID",
    operation_id="get_interest",
)
def get_interest(interest_id: str, orchestrator: OrchestratorDep) -> InterestDTO:
    interest = orchestrator.get_interest(interest_id)
    if interest is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interest '{interest_id}' not found")
    return interest


@v1_router.delete(
    "/interests/{interest_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete Interest by ID",
    operation_id="delete_interest",
)
def delete_interest(interest_id: str, orchestrator: OrchestratorDep) -> dict[str, bool]:
    return {"deleted": orchestrator.delete_entity("interest", interest_id)}


# --- Effort Routes ---
@v1_router.post(
    "/efforts",
    response_model=EffortDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an Effort (with requirements, risks, mitigators)",
    operation_id="upsert_effort",
)
def upsert_effort(effort: EffortDTO, orchestrator: OrchestratorDep) -> EffortDTO:
    return orchestrator.upsert_effort(effort)


@v1_router.get(
    "/efforts",
    response_model=list[EffortDTO],
    status_code=status.HTTP_200_OK,
    summary="List all Efforts",
    operation_id="list_efforts",
)
def list_efforts(orchestrator: OrchestratorDep) -> list[EffortDTO]:
    return orchestrator.list_efforts()


@v1_router.get(
    "/efforts/{effort_id}",
    response_model=EffortDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Effort by ID",
    operation_id="get_effort",
)
def get_effort(effort_id: str, orchestrator: OrchestratorDep) -> EffortDTO:
    effort = orchestrator.get_effort(effort_id)
    if effort is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Effort '{effort_id}' not found")
    return effort


@v1_router.delete(
    "/efforts/{effort_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete Effort by ID",
    operation_id="delete_effort",
)
def delete_effort(effort_id: str, orchestrator: OrchestratorDep) -> dict[str, bool]:
    return {"deleted": orchestrator.delete_entity("effort", effort_id)}


# --- Six Typed Edge Routes ---
@v1_router.post(
    "/edges/org-org",
    response_model=OrgOrgEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Org-to-Org relationship",
    operation_id="upsert_org_org_edge",
)
def upsert_org_org_edge(edge: OrgOrgEdgeDTO, orchestrator: OrchestratorDep) -> OrgOrgEdgeDTO:
    return orchestrator.upsert_org_org_edge(edge)


@v1_router.post(
    "/edges/org-interest",
    response_model=OrgInterestEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Org-to-Interest stance & priority",
    operation_id="upsert_org_interest_edge",
)
def upsert_org_interest_edge(edge: OrgInterestEdgeDTO, orchestrator: OrchestratorDep) -> OrgInterestEdgeDTO:
    return orchestrator.upsert_org_interest_edge(edge)


@v1_router.post(
    "/edges/interest-interest",
    response_model=InterestInterestEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Interest-to-Interest taxonomy edge",
    operation_id="upsert_interest_interest_edge",
)
def upsert_interest_interest_edge(
    edge: InterestInterestEdgeDTO, orchestrator: OrchestratorDep
) -> InterestInterestEdgeDTO:
    return orchestrator.upsert_interest_interest_edge(edge)


@v1_router.post(
    "/edges/org-effort",
    response_model=OrgEffortEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Org-to-Effort direct resourcing link",
    operation_id="upsert_org_effort_edge",
)
def upsert_org_effort_edge(
    edge: OrgEffortEdgeDTO,
    orchestrator: OrchestratorDep,
    access_ctx: AccessContextDep,
    human_slip_penalty_days: int | None = Query(default=None),
) -> OrgEffortEdgeDTO:
    return orchestrator.upsert_org_effort_edge(
        edge, context=access_ctx, human_slip_penalty_days=human_slip_penalty_days
    )


@v1_router.post(
    "/edges/effort-interest",
    response_model=EffortInterestEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Effort-to-Interest alignment link",
    operation_id="upsert_effort_interest_edge",
)
def upsert_effort_interest_edge(
    edge: EffortInterestEdgeDTO, orchestrator: OrchestratorDep
) -> EffortInterestEdgeDTO:
    return orchestrator.upsert_effort_interest_edge(edge)


@v1_router.post(
    "/edges/effort-effort",
    response_model=EffortEffortEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upsert Effort-to-Effort causal dependency link",
    operation_id="upsert_effort_effort_edge",
)
def upsert_effort_effort_edge(edge: EffortEffortEdgeDTO, orchestrator: OrchestratorDep) -> EffortEffortEdgeDTO:
    return orchestrator.upsert_effort_effort_edge(edge)


@v1_router.delete(
    "/edges/{edge_category}/{edge_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete a typed edge by category and ID",
    operation_id="delete_typed_edge",
)
def delete_typed_edge(edge_category: str, edge_id: str, orchestrator: OrchestratorDep) -> dict[str, bool]:
    valid_categories = {
        "org_org_edge",
        "org_interest_edge",
        "interest_interest_edge",
        "org_effort_edge",
        "effort_interest_edge",
        "effort_effort_edge",
    }
    if edge_category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid edge_category '{edge_category}'",
        )
    return {"deleted": orchestrator.delete_entity(edge_category, edge_id)}


# --- Primary Workspace Views (A / B / C) ---
@v1_router.get(
    "/views/capability-tree",
    response_model=CapabilityTreeViewDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Stateful Capability Progression Tree projection (View A)",
    operation_id="get_capability_tree_view",
)
def get_capability_tree_view(
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
    include_hierarchy_priorities: bool = Query(default=True),
    min_confidence: ConfidenceLevel | None = Query(default=None),
    org_filter: str | None = Query(default=None),
) -> CapabilityTreeViewDTO:
    return orchestrator.get_capability_tree_view(
        as_of_date=as_of_date,
        include_hierarchy_priorities=include_hierarchy_priorities,
        min_confidence=min_confidence,
        org_filter=org_filter,
    )


@v1_router.get(
    "/views/tripartite-flow",
    response_model=TriPartiteFlowViewDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Tri-Partite Architectural Flow projection (View B)",
    operation_id="get_tripartite_flow_view",
)
def get_tripartite_flow_view(
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
    include_hierarchy_priorities: bool = Query(default=True),
    min_confidence: ConfidenceLevel | None = Query(default=None),
) -> TriPartiteFlowViewDTO:
    return orchestrator.get_tripartite_flow_view(
        as_of_date=as_of_date,
        include_hierarchy_priorities=include_hierarchy_priorities,
        min_confidence=min_confidence,
    )


@v1_router.post(
    "/simulation/bill-of-efforts",
    response_model=BillOfEffortsSimulationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Simulate transient Bill of Efforts changes (View C)",
    operation_id="simulate_bill_of_efforts",
)
def simulate_bill_of_efforts(
    request: BillOfEffortsSimulationRequestDTO,
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
) -> BillOfEffortsSimulationResponseDTO:
    return orchestrator.simulate_bill_of_efforts(request=request, as_of_date=as_of_date)


@v1_router.post(
    "/simulation/bill-of-efforts/commit",
    response_model=BillOfEffortsSimulationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Commit simulated Bill of Efforts decisions into persistent graph",
    operation_id="commit_bill_of_efforts",
)
def commit_bill_of_efforts(
    request: BillOfEffortsSimulationRequestDTO,
    orchestrator: OrchestratorDep,
    access_ctx: AccessContextDep,
    as_of_date: date | None = Query(default=None),
) -> BillOfEffortsSimulationResponseDTO:
    return orchestrator.commit_bill_of_efforts(
        request=request, context=access_ctx, as_of_date=as_of_date
    )


# --- Focal Dashboards ---
@v1_router.get(
    "/views/efforts/{effort_id}/focal",
    response_model=EffortFocalDashboardDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Effort focal inspector dashboard",
    operation_id="get_effort_focal_dashboard",
)
def get_effort_focal_dashboard(
    effort_id: str,
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
) -> EffortFocalDashboardDTO:
    return orchestrator.get_effort_focal_dashboard(effort_id=effort_id, as_of_date=as_of_date)


@v1_router.get(
    "/views/organizations/{org_id}/focal",
    response_model=OrgFocalDashboardDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Organization focal inspector dashboard",
    operation_id="get_org_focal_dashboard",
)
def get_org_focal_dashboard(
    org_id: str,
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
    include_hierarchy_priorities: bool = Query(default=True),
) -> OrgFocalDashboardDTO:
    return orchestrator.get_org_focal_dashboard(
        org_id=org_id,
        as_of_date=as_of_date,
        include_hierarchy_priorities=include_hierarchy_priorities,
    )


@v1_router.get(
    "/views/interests/{interest_id}/focal",
    response_model=InterestFocalDashboardDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate Interest lineage focal inspector dashboard",
    operation_id="get_interest_focal_dashboard",
)
def get_interest_focal_dashboard(
    interest_id: str,
    orchestrator: OrchestratorDep,
    as_of_date: date | None = Query(default=None),
) -> InterestFocalDashboardDTO:
    return orchestrator.get_interest_focal_dashboard(interest_id=interest_id, as_of_date=as_of_date)


# --- Executive Briefing ---
@v1_router.get(
    "/views/briefing",
    response_model=PerspectiveBriefingDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate 1-Slide Executive Organization Briefing",
    operation_id="get_perspective_briefing",
)
def get_perspective_briefing(
    orchestrator: OrchestratorDep,
    access_ctx: AccessContextDep,
    subject_org_id: str = Query(...),
    include_hierarchy_inheritance: bool = Query(default=True),
    as_of_date: date | None = Query(default=None),
) -> PerspectiveBriefingDTO:
    return orchestrator.get_perspective_briefing(
        subject_org_id=subject_org_id,
        active_access_mode=access_ctx.mode,
        include_hierarchy_inheritance=include_hierarchy_inheritance,
        as_of_date=as_of_date,
    )


# --- Manifest Interchange & Diagnostics ---
@v1_router.get(
    "/manifest/export",
    response_model=BijouManifestDTO,
    status_code=status.HTTP_200_OK,
    summary="Export complete Bijou v2 graph manifest",
    operation_id="export_manifest",
)
def export_manifest(orchestrator: OrchestratorDep) -> BijouManifestDTO:
    return orchestrator.export_manifest()


@v1_router.post(
    "/manifest/import",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Import complete Bijou v2 graph manifest atomically",
    operation_id="import_manifest",
)
def import_manifest(
    manifest: BijouManifestDTO,
    orchestrator: OrchestratorDep,
    replace_all: bool = Query(default=False),
) -> dict[str, int]:
    try:
        return orchestrator.import_manifest(manifest, replace_all=replace_all)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err)) from err


@v1_router.post(
    "/manifest/validate",
    response_model=DiagnosticReportDTO,
    status_code=status.HTTP_200_OK,
    summary="Run graph acyclicity, Color-of-Money, pool capacity, and skill risk diagnostics",
    operation_id="validate_manifest",
)
def validate_manifest(
    orchestrator: OrchestratorDep,
    manifest: BijouManifestDTO | None = None,
) -> DiagnosticReportDTO:
    return orchestrator.validate_manifest_diagnostics(manifest=manifest)


# --- Telemetry, Provenance Ledger & Tools ---
@v1_router.post(
    "/telemetry/events",
    response_model=dict[str, int],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch ingest Effort operational telemetry events",
    operation_id="ingest_telemetry_events",
)
def ingest_telemetry_events(
    events: list[EffortTelemetryEventDTO],
    orchestrator: OrchestratorDep,
) -> dict[str, int]:
    return {"ingested": orchestrator.ingest_telemetry(events)}


@v1_router.get(
    "/telemetry/provenance/{event_id}",
    response_model=list[EffortTelemetryEventDTO],
    status_code=status.HTTP_200_OK,
    summary="Trace telemetry event causal provenance",
    operation_id="trace_event_provenance",
)
def trace_event_provenance(
    event_id: str,
    orchestrator: OrchestratorDep,
    max_depth: int = Query(default=10, ge=1, le=20),
) -> list[EffortTelemetryEventDTO]:
    return orchestrator.trace_event_provenance(event_id=event_id, max_depth=max_depth)


@v1_router.post(
    "/decisions",
    response_model=DecisionLogEntryDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Record decision provenance log entry",
    operation_id="log_decision",
)
def log_decision(entry: DecisionLogEntryDTO, orchestrator: OrchestratorDep) -> DecisionLogEntryDTO:
    return orchestrator.log_decision(entry)


@v1_router.get(
    "/decisions",
    response_model=list[DecisionLogEntryDTO],
    status_code=status.HTTP_200_OK,
    summary="List decision provenance logs",
    operation_id="list_decision_logs",
)
def list_decision_logs(
    orchestrator: OrchestratorDep,
    target_effort_id: str | None = Query(default=None),
) -> list[DecisionLogEntryDTO]:
    return orchestrator.list_decision_logs(target_effort_id=target_effort_id)


@v1_router.get(
    "/tools",
    response_model=list[ToolDescriptorDTO],
    status_code=status.HTTP_200_OK,
    summary="List analytical decision tools",
    operation_id="list_tools",
)
def list_tools(orchestrator: OrchestratorDep) -> list[ToolDescriptorDTO]:
    return orchestrator.list_tools()


@v1_router.get(
    "/health",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="System health check",
    operation_id="health_check",
)
def health_check() -> dict[str, str]:
    return {"status": "healthy", "engine": "bijou-v2"}
