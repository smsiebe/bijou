"""Bijou central orchestration service with materialized view caching."""

import threading
from collections import OrderedDict
from datetime import date, datetime, timezone

import httpx

from bijou.core.contracts.enums import (
    AccumulatorPattern,
    EffectTier,
    TechTreeStratificationMode,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    CausalGateDTO,
    ConcernDTO,
    EffectDTO,
    GraphEdgeDTO,
    OrganizationDTO,
    ThingDTO,
)
from bijou.core.contracts.telemetry import EffectEventDTO
from bijou.core.contracts.views import (
    PerspectiveBriefingDTO,
    SlipSimulationRequestDTO,
    SlipSimulationResponseDTO,
    TechTreeViewDTO,
    ThingFocalDashboardDTO,
    TradeoffProposalComparisonDTO,
)
from bijou.core.ports.federation import IFederationConnector
from bijou.core.ports.graph_engine import IGraphProjectionEngine
from bijou.core.ports.reasoning import IReasoningBroker
from bijou.core.ports.repository import IGraphRepository
from bijou.core.ports.telemetry_store import ITelemetryStore


class BijouOrchestrationService:
    """Core application orchestrator coordinating repository, in-memory graph, telemetry, and reasoning.

    Concurrency Model: Thread-safe; write mutations synchronize graph rebuilds and invalidate
    the bounded LRU materialized perspective cache under an exclusive RLock.
    """

    def __init__(
        self,
        repository: IGraphRepository,
        projection_engine: IGraphProjectionEngine,
        telemetry_store: ITelemetryStore,
        federation_connector: IFederationConnector,
        reasoning_broker: IReasoningBroker,
        enable_reasoning: bool = False,
        max_cache_size: int = 128,
    ) -> None:
        self._repository = repository
        self._projection_engine = projection_engine
        self._telemetry_store = telemetry_store
        self._federation_connector = federation_connector
        self._reasoning_broker = reasoning_broker
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

    # --- Organization Operations ---
    def upsert_organization(self, org: OrganizationDTO) -> OrganizationDTO:
        res = self._repository.upsert_organization(org)
        self._invalidate_and_rebuild()
        return res

    def get_organization(self, org_id: str) -> OrganizationDTO | None:
        return self._repository.get_organization(org_id)

    def list_organizations(self) -> list[OrganizationDTO]:
        return self._repository.list_organizations()

    # --- Concern Operations ---
    def upsert_concern(self, concern: ConcernDTO) -> ConcernDTO:
        res = self._repository.upsert_concern(concern)
        self._invalidate_and_rebuild()
        return res

    def get_concern(self, concern_id: str) -> ConcernDTO | None:
        return self._repository.get_concern(concern_id)

    def list_concerns(self) -> list[ConcernDTO]:
        return self._repository.list_concerns()

    # --- Thing Operations ---
    def upsert_thing(self, thing: ThingDTO) -> ThingDTO:
        res = self._repository.upsert_thing(thing)
        self._invalidate_and_rebuild()
        return res

    def get_thing(self, thing_id: str) -> ThingDTO | None:
        return self._repository.get_thing(thing_id)

    def list_things(self) -> list[ThingDTO]:
        return self._repository.list_things()

    # --- Causal Gate Operations ---
    def upsert_causal_gate(self, gate: CausalGateDTO) -> CausalGateDTO:
        res = self._repository.upsert_causal_gate(gate)
        self._invalidate_and_rebuild()
        return res

    def get_causal_gate(self, gate_id: str) -> CausalGateDTO | None:
        return self._repository.get_causal_gate(gate_id)

    def list_causal_gates(self) -> list[CausalGateDTO]:
        return self._repository.list_causal_gates()

    # --- Effect Operations ---
    def upsert_effect(self, effect: EffectDTO) -> EffectDTO:
        res = self._repository.upsert_effect(effect)
        self._invalidate_and_rebuild()
        return res

    def get_effect(self, effect_id: str) -> EffectDTO | None:
        return self._repository.get_effect(effect_id)

    def list_effects(self) -> list[EffectDTO]:
        return self._repository.list_effects()

    # --- Edge Operations ---
    def upsert_edge(self, edge: GraphEdgeDTO) -> GraphEdgeDTO:
        res = self._repository.upsert_edge(edge)
        self._invalidate_and_rebuild()
        return res

    def get_edge(self, edge_id: str) -> GraphEdgeDTO | None:
        return self._repository.get_edge(edge_id)

    def list_edges(self) -> list[GraphEdgeDTO]:
        return self._repository.list_edges()

    # --- Generic Entity Deletion ---
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

    # --- Telemetry Operations ---
    def ingest_telemetry(self, events: list[EffectEventDTO]) -> int:
        return self._telemetry_store.ingest_events(events)

    def trace_event_provenance(self, event_id: str, max_depth: int = 10) -> list[EffectEventDTO]:
        return self._telemetry_store.trace_event_provenance(event_id, max_depth)

    # --- View & Projection Operations ---
    def get_perspective_briefing(
        self,
        subject_org_id: str,
        perspective_org_id: str | None = None,
        include_descendants: bool = True,
        as_of_date: date | None = None,
    ) -> PerspectiveBriefingDTO:
        """Assemble or retrieve cached Multi-Perspective Briefing."""
        effective_date = as_of_date or date.today()
        cache_key = f"{subject_org_id}:{perspective_org_id}:{include_descendants}:{effective_date}"

        with self._lock:
            if cache_key in self._perspective_cache:
                self._perspective_cache.move_to_end(cache_key)
                return self._perspective_cache[cache_key]

        # Hydrate observed values from telemetry/federation if needed
        self._hydrate_virtual_effects()

        briefing = self._projection_engine.build_perspective_briefing(
            subject_org_id=subject_org_id,
            perspective_org_id=perspective_org_id,
            include_descendants=include_descendants,
            as_of_date=effective_date,
        )

        narrative: str | None = None
        strategic_gaps: list[str] = []

        if self._enable_reasoning:
            subject_org = self.get_organization(subject_org_id)
            mission = subject_org.mission_statement if subject_org else "Support enterprise intentions"
            narrative, strategic_gaps = self._reasoning_broker.synthesize_executive_briefing(
                briefing, mission
            )

        updated_briefing = PerspectiveBriefingDTO(
            subject_org_id=briefing.subject_org_id,
            perspective_org_id=briefing.perspective_org_id,
            include_descendants=briefing.include_descendants,
            as_of_date=briefing.as_of_date,
            owned_things=briefing.owned_things,
            supported_concerns=briefing.supported_concerns,
            cross_org_dependencies=briefing.cross_org_dependencies,
            portfolio_roi_score=briefing.portfolio_roi_score,
            total_committed_cost=briefing.total_committed_cost,
            executive_summary_narrative=narrative,
            strategic_gaps=strategic_gaps,
        )

        with self._lock:
            if len(self._perspective_cache) >= self._max_cache_size:
                self._perspective_cache.popitem(last=False)
            self._perspective_cache[cache_key] = updated_briefing

        return updated_briefing

    def _hydrate_virtual_effects(self) -> None:
        """Query telemetry sidecar or external federation for observable metrics."""
        manifest = self._repository.export_manifest()
        window_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        window_end = datetime.now(timezone.utc)
        updated_any = False

        gates_by_id = {g.id: g for g in manifest.causal_gates}

        for effect in manifest.effects:
            new_observed: float | None = None

            # 1. Federated Virtual Tier
            if effect.tier == EffectTier.FEDERATED_VIRTUAL and effect.federation_spec:
                try:
                    rollup = self._federation_connector.execute_federated_rollup(
                        effect.federation_spec, window_start, window_end
                    )
                    new_observed = rollup.aggregated_value
                except (httpx.HTTPError, OSError, ValueError):
                    pass

            # 2. Tier-2 Operational Telemetry Rollup
            elif effect.tier == EffectTier.TIER_2_OPERATIONAL:
                contributing_thing_ids: list[str] = []
                if effect.causal_gate_id and effect.causal_gate_id in gates_by_id:
                    gate = gates_by_id[effect.causal_gate_id]
                    contributing_thing_ids = [c.thing_id for c in gate.contributors]

                if not contributing_thing_ids:
                    contributing_thing_ids = [t.id for t in manifest.things]

                for t_id in contributing_thing_ids:
                    metrics = self._telemetry_store.list_metrics_for_thing(t_id)
                    target_metrics = [m for m in metrics if m in (effect.id, effect.name)] or metrics
                    for metric in target_metrics:
                        rollup = self._telemetry_store.compute_rollup(
                            thing_id=t_id,
                            metric_name=metric,
                            accumulator=effect.accumulator,
                            window_start=window_start,
                            window_end=window_end,
                            sla_target=effect.target_threshold,
                        )
                        if rollup.event_count > 0:
                            new_observed = rollup.aggregated_value
                            break
                    if new_observed is not None:
                        break

            if new_observed is not None and new_observed != effect.observed_value:
                effect_updated = EffectDTO(
                    id=effect.id,
                    name=effect.name,
                    description=effect.description,
                    tier=effect.tier,
                    causal_gate_id=effect.causal_gate_id,
                    accumulator=effect.accumulator,
                    observed_value=new_observed,
                    target_threshold=effect.target_threshold,
                    satisfies_concerns=effect.satisfies_concerns,
                    federation_spec=effect.federation_spec,
                )
                self._repository.upsert_effect(effect_updated)
                updated_any = True

        if updated_any:
            self._projection_engine.rebuild_projection(self._repository.export_manifest())

    def get_tech_tree_view(
        self,
        as_of_date: date | None = None,
        stratification_mode: TechTreeStratificationMode = TechTreeStratificationMode.TRL_TIERS,
        org_filter: str | None = None,
    ) -> TechTreeViewDTO:
        effective_date = as_of_date or date.today()
        return self._projection_engine.build_tech_tree_view(
            as_of_date=effective_date,
            stratification_mode=stratification_mode,
            org_filter=org_filter,
        )

    def get_thing_focal_dashboard(
        self,
        thing_id: str,
        as_of_date: date | None = None,
    ) -> ThingFocalDashboardDTO:
        effective_date = as_of_date or date.today()
        window_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        window_end = datetime.now(timezone.utc)

        # Query distinct metrics recorded for this thing
        metrics = self._telemetry_store.list_metrics_for_thing(thing_id)
        if not metrics:
            metrics = ["default"]

        rollups = []
        for metric in metrics:
            rollup = self._telemetry_store.compute_rollup(
                thing_id=thing_id,
                metric_name=metric,
                accumulator=AccumulatorPattern.SUM,
                window_start=window_start,
                window_end=window_end,
            )
            if rollup.event_count > 0:
                rollups.append(rollup)

        return self._projection_engine.build_thing_focal_dashboard(
            thing_id=thing_id,
            as_of_date=effective_date,
            telemetry_rollups=rollups,
        )

    def simulate_milestone_slip(
        self,
        request: SlipSimulationRequestDTO,
        as_of_date: date | None = None,
    ) -> SlipSimulationResponseDTO:
        effective_date = as_of_date or date.today()
        return self._projection_engine.simulate_milestone_slip(request, effective_date)

    def evaluate_tradeoff(
        self,
        proposed_thing_ids: list[str],
        as_of_date: date | None = None,
    ) -> TradeoffProposalComparisonDTO:
        effective_date = as_of_date or date.today()
        comparison = self._projection_engine.evaluate_tradeoff_matrix(
            proposed_thing_ids, effective_date
        )
        if self._enable_reasoning:
            try:
                rec = self._reasoning_broker.recommend_portfolio_tradeoff(comparison)
                return TradeoffProposalComparisonDTO(
                    proposed_thing_ids=comparison.proposed_thing_ids,
                    total_cost=comparison.total_cost,
                    aggregate_roi=comparison.aggregate_roi,
                    concern_coverage_deltas=comparison.concern_coverage_deltas,
                    unlocked_effect_ids=comparison.unlocked_effect_ids,
                    reasoning_recommendation=rec,
                )
            except (httpx.HTTPError, OSError, ValueError):
                pass
        return comparison
