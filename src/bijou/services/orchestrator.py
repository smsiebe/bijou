"""Bijou v2 central orchestration service coordinating repository, projection engine, telemetry, and access perspective."""

import threading
from collections import OrderedDict
from datetime import date, datetime, timezone

from bijou.core.contracts.enums import (
    AccessMode,
    AccumulatorPattern,
    ConfidenceLevel,
)
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
from bijou.core.contracts.telemetry import EffortTelemetryEventDTO, TelemetryRollupDTO
from bijou.core.contracts.tools import ToolDescriptorDTO
from bijou.core.contracts.views import (
    AccessPerspectiveStateDTO,
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    DiagnosticReportDTO,
    EffortBriefingDTO,
    EffortFocalDashboardDTO,
    InterestFocalDashboardDTO,
    OrgFocalDashboardDTO,
    PerspectiveBriefingDTO,
    TriPartiteFlowViewDTO,
)
from bijou.core.engine.forecasting import detect_cycles_in_graph
from bijou.core.engine.traversal import evaluate_skill_mismatch
from bijou.core.ports.access_control import (
    AccessContext,
    DemoAccessControlProvider,
    IAccessControlProvider,
)
from bijou.core.ports.exceptions import GraphCycleError, PermissionDeniedError
from bijou.core.ports.graph_engine import IGraphProjectionEngine
from bijou.core.ports.reasoning import IReasoningBroker
from bijou.core.ports.repository import IGraphRepository
from bijou.core.ports.telemetry_store import ITelemetryStore


class BijouOrchestrationService:
    """Thread-safe application orchestrator for Bijou v2."""

    def __init__(
        self,
        repository: IGraphRepository,
        projection_engine: IGraphProjectionEngine,
        telemetry_store: ITelemetryStore,
        reasoning_broker: IReasoningBroker,
        access_provider: IAccessControlProvider | None = None,
        enable_reasoning: bool = False,
        max_cache_size: int = 128,
    ) -> None:
        self._repository = repository
        self._projection_engine = projection_engine
        self._telemetry_store = telemetry_store
        self._reasoning_broker = reasoning_broker
        self._access_provider = access_provider or DemoAccessControlProvider()
        self._enable_reasoning = enable_reasoning
        self._max_cache_size = max_cache_size

        self._lock = threading.RLock()
        self._perspective_cache: OrderedDict[str, PerspectiveBriefingDTO] = OrderedDict()

    def initialize(self) -> None:
        """Hydrate graph projection engine from repository on startup."""
        with self._lock:
            manifest = self._repository.export_manifest()
            self._projection_engine.rebuild_projection(manifest)
            self._perspective_cache.clear()

    def _invalidate_and_rebuild(self) -> None:
        with self._lock:
            self._perspective_cache.clear()
            manifest = self._repository.export_manifest()
            self._projection_engine.rebuild_projection(manifest)

    # --- Access Perspective Resolution ---
    def resolve_access_context(
        self,
        requested_mode: AccessMode | None = None,
        requested_org_id: str | None = None,
        auth_token: str | None = None,
    ) -> AccessContext:
        return self._access_provider.resolve_context(
            requested_mode=requested_mode,
            requested_org_id=requested_org_id,
            auth_token=auth_token,
        )

    def get_perspective_state(self, context: AccessContext) -> AccessPerspectiveStateDTO:
        managed_orgs = [o for o in self._repository.list_organizations() if o.is_managed]
        return AccessPerspectiveStateDTO(
            mode=context.mode,
            active_org_id=context.active_org_id,
            managed_organizations=managed_orgs,
        )

    def _assert_can_manage_org(self, context: AccessContext, org_id: str) -> None:
        org = self._repository.get_organization(org_id)
        if org and not self._access_provider.can_manage_org(context, org):
            raise PermissionDeniedError(
                f"Active perspective ({context.mode}:{context.active_org_id}) cannot mutate inventories for '{org_id}'"
            )

    # --- Organization & Resource Pool CRUD ---
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        res = self._repository.upsert_organization(org)
        self._invalidate_and_rebuild()
        return res

    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        return self._repository.get_organization(org_id)

    def list_organizations(self) -> list[OrganizationDTO]:
        return self._repository.list_organizations()

    def upsert_resource_pool(
        self,
        pool: ResourcePoolDTO,
        context: AccessContext | None = None,
    ) -> ResourcePoolDTO:
        if context is not None:
            self._assert_can_manage_org(context, pool.org_id)
        res = self._repository.upsert_resource_pool(pool)
        self._invalidate_and_rebuild()
        return res

    def get_resource_pool(self, pool_id: str) -> ResourcePoolDTO | None:
        return self._repository.get_resource_pool(pool_id)

    def list_resource_pools(self, org_id: str | None = None) -> list[ResourcePoolDTO]:
        return self._repository.list_resource_pools(org_id=org_id)

    # --- Interest CRUD ---
    def upsert_interest(self, interest: InterestDTO) -> InterestDTO:
        res = self._repository.upsert_interest(interest)
        self._invalidate_and_rebuild()
        return res

    def get_interest(self, interest_id: str) -> InterestDTO | None:
        return self._repository.get_interest(interest_id)

    def list_interests(self) -> list[InterestDTO]:
        return self._repository.list_interests()

    # --- Effort CRUD ---
    def upsert_effort(self, effort: EffortDTO) -> EffortDTO:
        res = self._repository.upsert_effort(effort)
        self._invalidate_and_rebuild()
        return res

    def get_effort(self, effort_id: str) -> EffortDTO | None:
        return self._repository.get_effort(effort_id)

    def list_efforts(self) -> list[EffortDTO]:
        return self._repository.list_efforts()

    # --- Six Typed Edges CRUD ---
    def upsert_org_org_edge(self, edge: OrgOrgEdgeDTO) -> OrgOrgEdgeDTO:
        res = self._repository.upsert_org_org_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def upsert_org_interest_edge(self, edge: OrgInterestEdgeDTO) -> OrgInterestEdgeDTO:
        res = self._repository.upsert_org_interest_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def upsert_interest_interest_edge(self, edge: InterestInterestEdgeDTO) -> InterestInterestEdgeDTO:
        manifest = self._repository.export_manifest()
        nodes = [i.id for i in manifest.interests]
        edges = [
            (e.parent_interest_id, e.child_interest_id)
            for e in manifest.interest_interest_edges
            if e.id != edge.id
        ]
        edges.append((edge.parent_interest_id, edge.child_interest_id))
        cycles = detect_cycles_in_graph(nodes, edges)
        if cycles:
            raise GraphCycleError(cycles[0])

        res = self._repository.upsert_interest_interest_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def upsert_org_effort_edge(
        self,
        edge: OrgEffortEdgeDTO,
        context: AccessContext | None = None,
        human_slip_penalty_days: int | None = None,
    ) -> OrgEffortEdgeDTO:
        if context is not None:
            self._assert_can_manage_org(context, edge.org_id)

        # Check for non-transferable skill mismatch and automatically register Risk on target Effort
        target_effort = self._repository.get_effort(edge.effort_id)
        if target_effort and edge.requirement_id:
            all_reqs = list(target_effort.resource_requirements)
            for m in target_effort.mitigators:
                all_reqs.extend(m.additional_requirements)
            matched_req = next((r for r in all_reqs if r.id == edge.requirement_id), None)

            assigned_skill = edge.assigned_skill
            if assigned_skill is None and edge.resource_pool_id:
                pool = self._repository.get_resource_pool(edge.resource_pool_id)
                if pool:
                    assigned_skill = pool.skill_tag

            warning = evaluate_skill_mismatch(
                effort_id=edge.effort_id,
                assigned_skill=assigned_skill,
                requirement=matched_req,
                is_generic=edge.is_generic,
                human_slip_penalty_days=human_slip_penalty_days,
            )
            if warning:
                updated_risks = list(target_effort.risks) + [warning.generated_risk]
                self._repository.upsert_effort(target_effort.model_copy(update={"risks": updated_risks}))

        res = self._repository.upsert_org_effort_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def upsert_effort_interest_edge(self, edge: EffortInterestEdgeDTO) -> EffortInterestEdgeDTO:
        res = self._repository.upsert_effort_interest_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def upsert_effort_effort_edge(self, edge: EffortEffortEdgeDTO) -> EffortEffortEdgeDTO:
        manifest = self._repository.export_manifest()
        nodes = [e.id for e in manifest.efforts]
        edges = [
            (e.source_effort_id, e.target_effort_id)
            for e in manifest.effort_effort_edges
            if e.id != edge.id
        ]
        edges.append((edge.source_effort_id, edge.target_effort_id))
        cycles = detect_cycles_in_graph(nodes, edges)
        if cycles:
            raise GraphCycleError(cycles[0])

        res = self._repository.upsert_effort_effort_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        res = self._repository.delete_entity(entity_type, entity_id)
        if res:
            self._invalidate_and_rebuild()
        return res

    # --- Manifest Operations ---
    def export_manifest(self) -> BijouManifestDTO:
        return self._repository.export_manifest()

    def import_manifest(self, manifest: BijouManifestDTO, replace_all: bool = False) -> dict[str, int]:
        counts = self._repository.import_manifest(manifest, replace_all)
        self._invalidate_and_rebuild()
        return counts

    # --- Views & Simulation ---
    def get_capability_tree_view(
        self,
        as_of_date: date | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
        org_filter: str | None = None,
    ) -> CapabilityTreeViewDTO:
        return self._projection_engine.build_capability_tree_view(
            as_of_date=as_of_date or date.today(),
            include_hierarchy_priorities=include_hierarchy_priorities,
            min_confidence=min_confidence,
            org_filter=org_filter,
        )

    def get_tripartite_flow_view(
        self,
        as_of_date: date | None = None,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
    ) -> TriPartiteFlowViewDTO:
        return self._projection_engine.build_tripartite_flow_view(
            as_of_date=as_of_date or date.today(),
            include_hierarchy_priorities=include_hierarchy_priorities,
            min_confidence=min_confidence,
        )

    def simulate_bill_of_efforts(
        self,
        request: BillOfEffortsSimulationRequestDTO,
        as_of_date: date | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        return self._projection_engine.simulate_bill_of_efforts(
            request=request,
            as_of_date=as_of_date or date.today(),
        )

    def commit_bill_of_efforts(
        self,
        request: BillOfEffortsSimulationRequestDTO,
        context: AccessContext | None = None,
        as_of_date: date | None = None,
    ) -> BillOfEffortsSimulationResponseDTO:
        """Persist Bill of Efforts adjustments (toggled mitigators and allocations) into repository."""
        eff_date = as_of_date or date.today()
        sim_preview = self.simulate_bill_of_efforts(request=request, as_of_date=eff_date)

        # 1. Remove specified resourcing edges
        for edge_id in request.remove_edge_ids:
            try:
                self._repository.delete_entity("org_effort_edge", edge_id)
            except Exception:
                pass

        # 2. Apply toggled mitigators on Efforts
        if request.toggle_mitigators:
            for effort in self._repository.list_efforts():
                changed = False
                new_mits = []
                for m in effort.mitigators:
                    if m.id in request.toggle_mitigators:
                        new_mits.append(m.model_copy(update={"is_exercised": request.toggle_mitigators[m.id]}))
                        changed = True
                    else:
                        new_mits.append(m)
                if changed:
                    self._repository.upsert_effort(effort.model_copy(update={"mitigators": new_mits}))

        # 3. Apply new resource allocations (with auto-risk generation for skill mismatch)
        for alloc in request.add_allocations:
            self.upsert_org_effort_edge(
                OrgEffortEdgeDTO(
                    org_id=alloc.org_id,
                    effort_id=alloc.effort_id,
                    resourcing_type=alloc.resourcing_type,
                    resource_pool_id=alloc.pool_id,
                    requirement_id=alloc.requirement_id,
                    allocation_amount=alloc.amount,
                    allocation_unit=alloc.unit,
                    assigned_skill=alloc.assigned_skill,
                    is_generic=alloc.is_generic,
                    confidence=ConfidenceLevel.CONFIRMED,
                    provenance_note="Committed from Bill of Efforts workbench",
                ),
                context=context,
                human_slip_penalty_days=alloc.human_slip_penalty_days,
            )

        self._invalidate_and_rebuild()
        return sim_preview

    # --- Focal Dashboards ---
    def get_effort_focal_dashboard(
        self,
        effort_id: str,
        as_of_date: date | None = None,
    ) -> EffortFocalDashboardDTO:
        metric_names = self._telemetry_store.list_metrics_for_effort(effort_id)
        window_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        window_end = datetime.now(timezone.utc)
        rollups: list[TelemetryRollupDTO] = [
            self._telemetry_store.compute_rollup(
                effort_id=effort_id,
                metric_name=mname,
                accumulator=AccumulatorPattern.SUM,
                window_start=window_start,
                window_end=window_end,
            )
            for mname in metric_names
        ]
        return self._projection_engine.build_effort_focal_dashboard(
            effort_id=effort_id,
            as_of_date=as_of_date or date.today(),
            telemetry_rollups=rollups,
        )

    def get_org_focal_dashboard(
        self,
        org_id: str,
        as_of_date: date | None = None,
        include_hierarchy_priorities: bool = True,
    ) -> OrgFocalDashboardDTO:
        return self._projection_engine.build_org_focal_dashboard(
            org_id=org_id,
            as_of_date=as_of_date or date.today(),
            include_hierarchy_priorities=include_hierarchy_priorities,
        )

    def get_interest_focal_dashboard(
        self,
        interest_id: str,
        as_of_date: date | None = None,
    ) -> InterestFocalDashboardDTO:
        return self._projection_engine.build_interest_focal_dashboard(
            interest_id=interest_id,
            as_of_date=as_of_date or date.today(),
        )

    # --- Executive Briefing ---
    def get_perspective_briefing(
        self,
        subject_org_id: str,
        active_access_mode: AccessMode = AccessMode.GLOBAL_ANALYST,
        include_hierarchy_inheritance: bool = True,
        as_of_date: date | None = None,
    ) -> PerspectiveBriefingDTO:
        effective_date = as_of_date or date.today()
        cache_key = f"{subject_org_id}:{active_access_mode}:{include_hierarchy_inheritance}:{effective_date}"

        with self._lock:
            if cache_key in self._perspective_cache:
                self._perspective_cache.move_to_end(cache_key)
                return self._perspective_cache[cache_key]

        briefing = self._projection_engine.build_perspective_briefing(
            subject_org_id=subject_org_id,
            active_access_mode=active_access_mode,
            include_hierarchy_inheritance=include_hierarchy_inheritance,
            as_of_date=effective_date,
        )

        narrative: str | None = None
        strategic_gaps: list[str] = []
        if self._enable_reasoning:
            subject_org = self.get_organization(subject_org_id)
            mission = subject_org.description if subject_org else "Strategic domain mission"
            narrative, strategic_gaps = self._reasoning_broker.synthesize_executive_briefing(briefing, mission)

        result = briefing.model_copy(
            update={
                "executive_summary_narrative": narrative,
                "strategic_gaps": strategic_gaps,
            }
        )

        with self._lock:
            if len(self._perspective_cache) >= self._max_cache_size:
                self._perspective_cache.popitem(last=False)
            self._perspective_cache[cache_key] = result

        return result

    def get_effort_briefing(
        self,
        effort_id: str,
        active_access_mode: AccessMode = AccessMode.GLOBAL_ANALYST,
        include_hierarchy_inheritance: bool = True,
        as_of_date: date | None = None,
        max_hops: int = 6,
    ) -> EffortBriefingDTO:
        effective_date = as_of_date or date.today()
        cache_key = (
            f"effort:{effort_id}:{active_access_mode}:{include_hierarchy_inheritance}:{effective_date}:{max_hops}"
        )

        with self._lock:
            if cache_key in self._perspective_cache:
                self._perspective_cache.move_to_end(cache_key)
                return self._perspective_cache[cache_key]  # type: ignore[return-value]

        result = self._projection_engine.build_effort_briefing(
            effort_id=effort_id,
            active_access_mode=active_access_mode,
            as_of_date=effective_date,
            include_hierarchy_inheritance=include_hierarchy_inheritance,
            max_hops=max_hops,
        )

        with self._lock:
            if len(self._perspective_cache) >= self._max_cache_size:
                self._perspective_cache.popitem(last=False)
            self._perspective_cache[cache_key] = result  # type: ignore[assignment]

        return result

    # --- Diagnostics, Telemetry, Ledger & Tools ---
    def validate_manifest_diagnostics(self, manifest: BijouManifestDTO | None = None) -> DiagnosticReportDTO:
        return self._projection_engine.validate_manifest_diagnostics(manifest=manifest)

    def ingest_telemetry(self, events: list[EffortTelemetryEventDTO]) -> int:
        return self._telemetry_store.ingest_events(events)

    def trace_event_provenance(self, event_id: str, max_depth: int = 10) -> list[EffortTelemetryEventDTO]:
        return self._telemetry_store.trace_event_provenance(event_id, max_depth)

    def log_decision(self, entry: DecisionLogEntryDTO) -> DecisionLogEntryDTO:
        return self._repository.upsert_decision_log(entry)

    def list_decision_logs(self, target_effort_id: str | None = None) -> list[DecisionLogEntryDTO]:
        return self._repository.list_decision_logs(target_effort_id=target_effort_id)

    def list_tools(self) -> list[ToolDescriptorDTO]:
        return [
            ToolDescriptorDTO(
                tool_id="bill-of-efforts",
                title="Bill of Efforts Workbench",
                icon="zap",
                category="workbench",
                target_entity="effort",
                description="Simulate Mitigator options, allocate Color-of-Money pools, and reassign staff.",
                endpoint="/api/v1/simulation/bill-of-efforts",
                ui_component="BillOfEffortsDock",
            ),
            ToolDescriptorDTO(
                tool_id="tripartite-flow",
                title="Tri-Partite Flow Explorer",
                icon="globe",
                category="graph_projection",
                target_entity="global",
                description="Trace direct resourcing and indirect shared-interest partnerships across Orgs, Efforts, and Interests.",
                endpoint="/api/v1/views/tripartite-flow",
                ui_component="TriPartiteFlowCanvas",
            ),
            ToolDescriptorDTO(
                tool_id="effort-focal",
                title="Effort Deep Inspector",
                icon="target",
                category="graph_projection",
                target_entity="effort",
                description="Inspect upstream/downstream blocking vs informing edges, resource coverage, risks, and telemetry.",
                endpoint="/api/v1/views/efforts/{effort_id}/focal",
                ui_component="EntityPuckHUD",
            ),
            ToolDescriptorDTO(
                tool_id="diagnostics",
                title="Color-of-Money & Graph Diagnostics",
                icon="history",
                category="audit",
                target_entity="global",
                description="Verify DAG acyclicity, earmarked pool eligibility, and skill-mismatch risk registers.",
                endpoint="/api/v1/manifest/validate",
                ui_component="DiagnosticPanel",
            ),
        ]
