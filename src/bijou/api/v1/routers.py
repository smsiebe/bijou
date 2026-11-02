"""FastAPI v1 API route definitions."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from bijou.api.deps import get_orchestrator
from bijou.core.contracts.enums import TechTreeStratificationMode
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    CausalGateDTO,
    ConcernDTO,
    DecisionLogEntryDTO,
    EffectDTO,
    GraphEdgeDTO,
    OrganizationDTO,
    ThingDTO,
)
from bijou.core.contracts.telemetry import EffectEventDTO
from bijou.core.contracts.views import (
    DiagnosticReportDTO,
    ParetoFrontierDTO,
    PerspectiveBriefingDTO,
    SlipSimulationRequestDTO,
    SlipSimulationResponseDTO,
    TechTreeViewDTO,
    ThingFocalDashboardDTO,
    TradeoffProposalComparisonDTO,
    ClusteredSpheresViewDTO,
)
from bijou.core.contracts.tools import ToolDescriptorDTO

v1_router = APIRouter(prefix="/api/v1")

OrchestratorDep = Annotated[Any, Depends(get_orchestrator)]


# --- Organization Routes ---
@v1_router.post(
    "/organizations",
    response_model=OrganizationDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an organization",
    operation_id="create_or_update_organization",
)
def create_organization(
    org: OrganizationDTO,
    orchestrator: OrchestratorDep,
) -> OrganizationDTO:
    return orchestrator.upsert_organization(org)


@v1_router.get(
    "/organizations",
    response_model=list[OrganizationDTO],
    status_code=status.HTTP_200_OK,
    summary="List all organizations",
    operation_id="list_organizations",
)
def list_organizations(
    orchestrator: OrchestratorDep,
) -> list[OrganizationDTO]:
    return orchestrator.list_organizations()


@v1_router.get(
    "/organizations/{org_id}",
    response_model=OrganizationDTO,
    status_code=status.HTTP_200_OK,
    summary="Get organization by ID",
    operation_id="get_organization",
)
def get_organization(
    org_id: str,
    orchestrator: OrchestratorDep,
) -> OrganizationDTO:
    org = orchestrator.get_organization(org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Organization '{org_id}' not found")
    return org


@v1_router.delete(
    "/organizations/{org_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete organization by ID",
    operation_id="delete_organization",
)
def delete_organization(
    org_id: str,
    orchestrator: OrchestratorDep,
) -> dict[str, bool]:
    success = orchestrator.delete_entity("organization", org_id)
    return {"deleted": success}


# --- Concern Routes ---
@v1_router.post(
    "/concerns",
    response_model=ConcernDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a strategic concern",
    operation_id="create_or_update_concern",
)
def create_concern(
    concern: ConcernDTO,
    orchestrator: OrchestratorDep,
) -> ConcernDTO:
    return orchestrator.upsert_concern(concern)


@v1_router.get(
    "/concerns",
    response_model=list[ConcernDTO],
    status_code=status.HTTP_200_OK,
    summary="List all strategic concerns",
    operation_id="list_concerns",
)
def list_concerns(
    orchestrator: OrchestratorDep,
) -> list[ConcernDTO]:
    return orchestrator.list_concerns()


@v1_router.get(
    "/concerns/{concern_id}",
    response_model=ConcernDTO,
    status_code=status.HTTP_200_OK,
    summary="Get concern by ID",
    operation_id="get_concern",
)
def get_concern(
    concern_id: str,
    orchestrator: OrchestratorDep,
) -> ConcernDTO:
    concern = orchestrator.get_concern(concern_id)
    if concern is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Concern '{concern_id}' not found")
    return concern


# --- Thing Routes ---
@v1_router.post(
    "/things",
    response_model=ThingDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a thing",
    operation_id="create_or_update_thing",
)
def create_thing(
    thing: ThingDTO,
    orchestrator: OrchestratorDep,
) -> ThingDTO:
    return orchestrator.upsert_thing(thing)


@v1_router.get(
    "/things",
    response_model=list[ThingDTO],
    status_code=status.HTTP_200_OK,
    summary="List all things",
    operation_id="list_things",
)
def list_things(
    orchestrator: OrchestratorDep,
) -> list[ThingDTO]:
    return orchestrator.list_things()


@v1_router.get(
    "/things/{thing_id}",
    response_model=ThingDTO,
    status_code=status.HTTP_200_OK,
    summary="Get thing by ID",
    operation_id="get_thing",
)
def get_thing(
    thing_id: str,
    orchestrator: OrchestratorDep,
) -> ThingDTO:
    thing = orchestrator.get_thing(thing_id)
    if thing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Thing '{thing_id}' not found")
    return thing


@v1_router.delete(
    "/things/{thing_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete thing by ID",
    operation_id="delete_thing",
)
def delete_thing(
    thing_id: str,
    orchestrator: OrchestratorDep,
) -> dict[str, bool]:
    success = orchestrator.delete_entity("thing", thing_id)
    return {"deleted": success}


# --- Causal Gate Routes ---
@v1_router.post(
    "/causal-gates",
    response_model=CausalGateDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a causal gate",
    operation_id="create_or_update_causal_gate",
)
def create_causal_gate(
    gate: CausalGateDTO,
    orchestrator: OrchestratorDep,
) -> CausalGateDTO:
    return orchestrator.upsert_causal_gate(gate)


@v1_router.get(
    "/causal-gates/{gate_id}",
    response_model=CausalGateDTO,
    status_code=status.HTTP_200_OK,
    summary="Get causal gate by ID",
    operation_id="get_causal_gate",
)
def get_causal_gate(
    gate_id: str,
    orchestrator: OrchestratorDep,
) -> CausalGateDTO:
    gate = orchestrator.get_causal_gate(gate_id)
    if gate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Causal gate '{gate_id}' not found")
    return gate


# --- Effect Routes ---
@v1_router.post(
    "/effects",
    response_model=EffectDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update an observable effect",
    operation_id="create_or_update_effect",
)
def create_effect(
    effect: EffectDTO,
    orchestrator: OrchestratorDep,
) -> EffectDTO:
    return orchestrator.upsert_effect(effect)


@v1_router.get(
    "/effects",
    response_model=list[EffectDTO],
    status_code=status.HTTP_200_OK,
    summary="List all observable effects",
    operation_id="list_effects",
)
def list_effects(
    orchestrator: OrchestratorDep,
) -> list[EffectDTO]:
    return orchestrator.list_effects()


@v1_router.get(
    "/effects/{effect_id}",
    response_model=EffectDTO,
    status_code=status.HTTP_200_OK,
    summary="Get observable effect by ID",
    operation_id="get_effect",
)
def get_effect(
    effect_id: str,
    orchestrator: OrchestratorDep,
) -> EffectDTO:
    eff = orchestrator.get_effect(effect_id)
    if eff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Effect '{effect_id}' not found")
    return eff


# --- Edge Routes ---
@v1_router.post(
    "/edges",
    response_model=GraphEdgeDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a graph edge",
    operation_id="create_or_update_edge",
)
def create_edge(
    edge: GraphEdgeDTO,
    orchestrator: OrchestratorDep,
) -> GraphEdgeDTO:
    return orchestrator.upsert_edge(edge)


@v1_router.get(
    "/edges",
    response_model=list[GraphEdgeDTO],
    status_code=status.HTTP_200_OK,
    summary="List all graph edges",
    operation_id="list_edges",
)
def list_edges(
    orchestrator: OrchestratorDep,
) -> list[GraphEdgeDTO]:
    return orchestrator.list_edges()


@v1_router.delete(
    "/edges/{edge_id}",
    response_model=dict[str, bool],
    status_code=status.HTTP_200_OK,
    summary="Delete graph edge by ID",
    operation_id="delete_edge",
)
def delete_edge(
    edge_id: str,
    orchestrator: OrchestratorDep,
) -> dict[str, bool]:
    success = orchestrator.delete_entity("edge", edge_id)
    return {"deleted": success}


# --- Telemetry & Manifest Routes ---
@v1_router.post(
    "/telemetry/events",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Ingest batch of Tier-2 operational events",
    operation_id="ingest_telemetry_events",
)
def ingest_telemetry_events(
    events: list[EffectEventDTO],
    orchestrator: OrchestratorDep,
) -> dict[str, int]:
    count = orchestrator.ingest_telemetry(events)
    return {"ingested_count": count}


@v1_router.get(
    "/telemetry/provenance/{event_id}",
    response_model=list[EffectEventDTO],
    status_code=status.HTTP_200_OK,
    summary="Trace event causal provenance chain",
    operation_id="trace_event_provenance",
)
def trace_event_provenance(
    event_id: str,
    orchestrator: OrchestratorDep,
    max_depth: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[EffectEventDTO]:
    return orchestrator.trace_event_provenance(event_id, max_depth)


@v1_router.post(
    "/manifest/import",
    response_model=dict[str, int],
    status_code=status.HTTP_200_OK,
    summary="Import manifest interchange document",
    operation_id="import_manifest",
)
def import_manifest(
    manifest: BijouManifestDTO,
    orchestrator: OrchestratorDep,
    replace_all: Annotated[bool, Query()] = False,
) -> dict[str, int]:
    return orchestrator.import_manifest(manifest, replace_all)


@v1_router.get(
    "/manifest/export",
    response_model=BijouManifestDTO,
    status_code=status.HTTP_200_OK,
    summary="Export graph database snapshot as manifest",
    operation_id="export_manifest",
)
def export_manifest(
    orchestrator: OrchestratorDep,
) -> BijouManifestDTO:
    return orchestrator.export_manifest()


@v1_router.post(
    "/manifest/validate",
    response_model=DiagnosticReportDTO,
    status_code=status.HTTP_200_OK,
    summary="Validate manifest topology and diagnostic linting",
    operation_id="validate_manifest_diagnostics",
)
def validate_manifest_diagnostics(
    manifest: BijouManifestDTO,
    orchestrator: OrchestratorDep,
) -> DiagnosticReportDTO:
    return orchestrator.validate_manifest_diagnostics(manifest)


# --- View & Analytical Projection Routes ---
@v1_router.get(
    "/views/perspectives/{org_id}",
    response_model=PerspectiveBriefingDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate 1-slide multi-perspective briefing",
    operation_id="get_perspective_briefing",
)
def get_perspective_briefing(
    org_id: str,
    orchestrator: OrchestratorDep,
    perspective_org_id: Annotated[str | None, Query()] = None,
    include_descendants: Annotated[bool, Query()] = True,
    as_of_date: Annotated[date | None, Query()] = None,
) -> PerspectiveBriefingDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.get_perspective_briefing(
        subject_org_id=org_id,
        perspective_org_id=perspective_org_id,
        include_descendants=include_descendants,
        as_of_date=effective_date,
    )


@v1_router.get(
    "/views/tech-tree",
    response_model=TechTreeViewDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate 4X game-style tech tree layout",
    operation_id="get_tech_tree_view",
)
def get_tech_tree_view(
    orchestrator: OrchestratorDep,
    as_of_date: Annotated[date | None, Query()] = None,
    stratification_mode: Annotated[
        TechTreeStratificationMode, Query()
    ] = TechTreeStratificationMode.TRL_TIERS,
    org_filter: Annotated[str | None, Query()] = None,
) -> TechTreeViewDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.get_tech_tree_view(
        as_of_date=effective_date,
        stratification_mode=stratification_mode,
        org_filter=org_filter,
    )


@v1_router.get(
    "/views/things/{thing_id}/focal",
    response_model=ThingFocalDashboardDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate 2-hop focal ego-network dashboard for a thing",
    operation_id="get_thing_focal_dashboard",
)
def get_thing_focal_dashboard(
    thing_id: str,
    orchestrator: OrchestratorDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> ThingFocalDashboardDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.get_thing_focal_dashboard(thing_id, effective_date)


@v1_router.post(
    "/analysis/simulate-slip",
    response_model=SlipSimulationResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Simulate milestone slip and propagate impact",
    operation_id="simulate_milestone_slip",
)
def simulate_milestone_slip(
    request: SlipSimulationRequestDTO,
    orchestrator: OrchestratorDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> SlipSimulationResponseDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.simulate_milestone_slip(request, effective_date)


@v1_router.post(
    "/analysis/tradeoff",
    response_model=TradeoffProposalComparisonDTO,
    status_code=status.HTTP_200_OK,
    summary="Evaluate portfolio tradeoff between proposed things",
    operation_id="evaluate_portfolio_tradeoff",
)
def evaluate_tradeoff(
    proposed_thing_ids: list[str],
    orchestrator: OrchestratorDep,
    as_of_date: Annotated[date | None, Query()] = None,
) -> TradeoffProposalComparisonDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.evaluate_tradeoff(proposed_thing_ids, effective_date)


@v1_router.get(
    "/analysis/pareto-frontier",
    response_model=ParetoFrontierDTO,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Pareto-optimal funding frontier under a budget ceiling",
    operation_id="evaluate_pareto_frontier",
)
def evaluate_pareto_frontier(
    orchestrator: OrchestratorDep,
    budget_ceiling: Annotated[float, Query(ge=0.0)] = 100000000.0,
    as_of_date: Annotated[date | None, Query()] = None,
) -> ParetoFrontierDTO:
    return orchestrator.evaluate_pareto_frontier(budget_ceiling, as_of_date)


# --- Decision Provenance Ledger Routes ---
@v1_router.post(
    "/decision-logs",
    response_model=DecisionLogEntryDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Append a decision audit record to the ledger",
    operation_id="create_decision_log_entry",
)
def create_decision_log(
    entry: DecisionLogEntryDTO,
    orchestrator: OrchestratorDep,
) -> DecisionLogEntryDTO:
    return orchestrator.upsert_decision_log(entry)


@v1_router.get(
    "/decision-logs",
    response_model=list[DecisionLogEntryDTO],
    status_code=status.HTTP_200_OK,
    summary="List decision ledger records",
    operation_id="list_decision_logs",
)
def list_decision_logs(
    orchestrator: OrchestratorDep,
    target_milestone_id: Annotated[str | None, Query()] = None,
) -> list[DecisionLogEntryDTO]:
    return orchestrator.list_decision_logs(target_milestone_id)



# --- Tool Registry & Clustered Spheres Routes ---
@v1_router.get(
    "/tools",
    response_model=list[ToolDescriptorDTO],
    status_code=status.HTTP_200_OK,
    summary="List available analytical tools",
    operation_id="list_analytical_tools",
)
def list_analytical_tools(
    orchestrator: OrchestratorDep,
) -> list[ToolDescriptorDTO]:
    return orchestrator.list_tools()


@v1_router.get(
    "/views/clustered-spheres",
    response_model=ClusteredSpheresViewDTO,
    status_code=status.HTTP_200_OK,
    summary="Get compound clustered graph layout partitioned by Organization spheres",
    operation_id="get_clustered_spheres_view",
)
def get_clustered_spheres_view(
    orchestrator: OrchestratorDep,
    as_of_date: Annotated[date | None, Query()] = None,
    org_filter: Annotated[str | None, Query()] = None,
) -> ClusteredSpheresViewDTO:
    effective_date = as_of_date or date.today()
    return orchestrator.get_clustered_spheres_view(
        as_of_date=effective_date,
        org_filter=org_filter,
    )
