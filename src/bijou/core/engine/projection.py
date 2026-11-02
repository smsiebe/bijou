"""In-memory deterministic graph projection and analytical calculation engine."""

import itertools
import threading
from datetime import date
from typing import Any

import networkx as nx

from bijou.core.contracts.enums import (
    LifecycleStatus,
    RelationshipType,
    TechTreeNodeState,
    TechTreeStratificationMode,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    ConcernDTO,
    EffectDTO,
    GraphEdgeDTO,
    ThingDTO,
)
from bijou.core.contracts.telemetry import TelemetryRollupDTO
from bijou.core.contracts.views import (
    ConcernCoverageItemDTO,
    DiagnosticReportDTO,
    ParetoFrontierDTO,
    PerspectiveBriefingDTO,
    SlipSimulationRequestDTO,
    SlipSimulationResponseDTO,
    TechTreeViewDTO,
    ThingFocalDashboardDTO,
    TradeoffProposalComparisonDTO,
    ClusteredSpheresViewDTO,
    OrganizationClusterDTO,
    ClusteredThingNodeDTO,
    ClusteredDependencyEdgeDTO,
    MacroOrgDependencyEdgeDTO,
)
from bijou.core.engine.causal import evaluate_causal_gate_yield
from bijou.core.engine.tech_tree import build_tech_tree_graph, simulate_slip_propagation
from bijou.core.ports.exceptions import GraphCycleError
from bijou.core.ports.graph_engine import IGraphProjectionEngine


def _is_edge_active(edge: GraphEdgeDTO, as_of_date: date) -> bool:
    """Return False if edge is outside its effective_start or effective_end window relative to as_of_date."""
    if edge.effective_start and as_of_date < edge.effective_start:
        return False
    return not (edge.effective_end and as_of_date > edge.effective_end)


class InMemoryGraphProjectionEngine(IGraphProjectionEngine):
    """In-memory deterministic graph projection engine using NetworkX.

    Concurrency Model: Thread-safe via reentrant read-write lock (RLock); snapshot reads
    execute concurrently; rebuild_projection acquires exclusive write lock.
    """

    def __init__(self, manifest: BijouManifestDTO | None = None) -> None:
        self._lock = threading.RLock()
        self._manifest = manifest or BijouManifestDTO()
        self._graph = nx.DiGraph()
        self._ms_graph = nx.DiGraph()
        if manifest:
            self._rebuild_internal(manifest)

    def rebuild_projection(self, manifest: BijouManifestDTO) -> None:
        """Rebuild the graph projection from a manifest snapshot."""
        with self._lock:
            self._rebuild_internal(manifest)

    def _rebuild_internal(self, manifest: BijouManifestDTO) -> None:
        self._manifest = manifest
        self._graph.clear()
        self._ms_graph.clear()

        # Add node entities
        for org in manifest.organizations:
            self._graph.add_node(org.id, type="organization", entity=org)
        for con in manifest.concerns:
            self._graph.add_node(con.id, type="concern", entity=con)
        for thing in manifest.things:
            self._graph.add_node(thing.id, type="thing", entity=thing)
            sorted_ms = sorted(thing.milestones, key=lambda m: m.sequence_index)
            for i in range(len(sorted_ms) - 1):
                self._ms_graph.add_edge(sorted_ms[i].id, sorted_ms[i + 1].id)
        for gate in manifest.causal_gates:
            self._graph.add_node(gate.id, type="causal_gate", entity=gate)
            for contrib in gate.contributors:
                self._graph.add_edge(contrib.thing_id, gate.id, weight=contrib.contribution_weight)
        for effect in manifest.effects:
            self._graph.add_node(effect.id, type="effect", entity=effect)
            if effect.causal_gate_id:
                self._graph.add_edge(effect.causal_gate_id, effect.id)

        # Add graph edges
        for edge in manifest.edges:
            self._graph.add_edge(
                edge.source_id,
                edge.target_id,
                relationship=edge.relationship,
                weight=edge.weight,
                source_ms=edge.source_milestone_id,
                target_ms=edge.target_milestone_id,
            )
            if edge.relationship == RelationshipType.DEPENDS_ON:
                if edge.source_milestone_id and edge.target_milestone_id:
                    self._ms_graph.add_edge(edge.target_milestone_id, edge.source_milestone_id)
                else:
                    self._ms_graph.add_edge(edge.target_id, edge.source_id)

    def validate_dag_acyclic(self) -> list[list[str]]:
        """Verify the milestone dependency graph is acyclic and return any detected cycles."""
        with self._lock:
            try:
                cycles = list(nx.simple_cycles(self._ms_graph))
            except nx.NetworkXError:
                cycles = []

            if cycles:
                first_cycle = list(cycles[0])
                first_cycle.append(first_cycle[0])
                raise GraphCycleError(first_cycle)

            return []

    def calculate_thing_roi(self, thing_id: str, as_of_date: date) -> float:
        """Calculate direct ROI score for a given Thing according to formula."""
        with self._lock:
            thing = next((t for t in self._manifest.things if t.id == thing_id), None)
            if not thing:
                return 0.0

            _, ms_states = build_tech_tree_graph(
                self._manifest,
                as_of_date,
                TechTreeStratificationMode.TRL_TIERS,
            )
            gate_yields = {
                g.id: evaluate_causal_gate_yield(g, ms_states) for g in self._manifest.causal_gates
            }
            return self._calculate_thing_roi_with_states(thing, gate_yields, as_of_date=as_of_date)

    def _calculate_thing_roi_with_states(
        self,
        thing: ThingDTO,
        gate_yields: dict[str, float],
        as_of_date: date | None = None,
    ) -> float:
        """Helper to compute ROI given pre-evaluated gate yields."""
        effects_numerator = 0.0
        concerns_by_id = {c.id: c for c in self._manifest.concerns}

        # 1. Effects produced via causal gates
        for gate in self._manifest.causal_gates:
            if any(c.thing_id == thing.id for c in gate.contributors):
                g_yield = gate_yields.get(gate.id, 0.0)
                for effect in self._manifest.effects:
                    if effect.causal_gate_id == gate.id:
                        eff_yield = g_yield if effect.observed_value is None else min(1.0, effect.observed_value / max(effect.target_threshold or 1.0, 1.0))
                        concern_sum = sum(
                            link.weight * concerns_by_id[link.concern_id].priority
                            for link in effect.satisfies_concerns
                            if link.concern_id in concerns_by_id
                        )
                        effects_numerator += eff_yield * concern_sum

        # 2. Direct impacts from Thing to Concerns via edges (filtered by temporal validity)
        for edge in self._manifest.edges:
            if as_of_date and not _is_edge_active(edge, as_of_date):
                continue
            if (
                edge.source_id == thing.id
                and edge.relationship in (RelationshipType.IMPACTS, RelationshipType.SUPPORTS)
                and edge.target_id in concerns_by_id
            ):
                c = concerns_by_id[edge.target_id]
                effects_numerator += edge.weight * c.priority

        # Cost & Risk floor
        cost_floor = max(thing.estimated_cost, 1.0)
        risk = max(thing.risk_factor, 1.0)
        return round(effects_numerator / (cost_floor * risk), 10)

    def build_perspective_briefing(
        self,
        subject_org_id: str,
        perspective_org_id: str | None,
        include_descendants: bool,
        as_of_date: date,
    ) -> PerspectiveBriefingDTO:
        """Assemble an executive Multi-Perspective 1-Slide Briefing projection."""
        with self._lock:
            # 1. Resolve subject organizations (including descendants if requested)
            subject_org_ids = {subject_org_id}
            if include_descendants:
                org_dag = nx.DiGraph()
                for org in self._manifest.organizations:
                    if org.parent_org_id:
                        org_dag.add_edge(org.parent_org_id, org.id)
                for edge in self._manifest.edges:
                    if _is_edge_active(edge, as_of_date) and edge.relationship == RelationshipType.PARENT_OF:
                        org_dag.add_edge(edge.source_id, edge.target_id)
                if subject_org_id in org_dag:
                    subject_org_ids.update(nx.descendants(org_dag, subject_org_id))

            # 2. Owned Things
            owned_things = [t for t in self._manifest.things if t.owner_org_id in subject_org_ids]
            total_cost = sum(t.estimated_cost for t in owned_things)

            # 3. Evaluate tech tree & gate yields
            _, ms_states = build_tech_tree_graph(
                self._manifest,
                as_of_date,
                TechTreeStratificationMode.TRL_TIERS,
            )
            gate_yields = {
                g.id: evaluate_causal_gate_yield(g, ms_states) for g in self._manifest.causal_gates
            }

            # 4. Resolve perspective concerns
            perspective_concerns: list[ConcernDTO] = []
            for c in self._manifest.concerns:
                if perspective_org_id is None or c.owner_org_id == perspective_org_id:
                    perspective_concerns.append(c)

            # 5. Calculate Concern coverage
            supported_concerns: list[ConcernCoverageItemDTO] = []

            for con in perspective_concerns:
                contributing_things: set[str] = set()
                satisfied_effects: set[str] = set()
                total_coverage = 0.0

                # Check effects satisfying this concern
                for effect in self._manifest.effects:
                    for link in effect.satisfies_concerns:
                        if link.concern_id == con.id and effect.causal_gate_id:
                            gate = next((g for g in self._manifest.causal_gates if g.id == effect.causal_gate_id), None)
                            if gate:
                                subject_contribs = [c for c in gate.contributors if c.thing_id in {t.id for t in owned_things}]
                                if subject_contribs:
                                    satisfied_effects.add(effect.id)
                                    for sc in subject_contribs:
                                        contributing_things.add(sc.thing_id)
                                    y = gate_yields.get(gate.id, 0.0)
                                    total_coverage += link.weight * y

                # Check direct edges from subject things (filtered by temporal validity)
                for t in owned_things:
                    for edge in self._manifest.edges:
                        if not _is_edge_active(edge, as_of_date):
                            continue
                        if edge.source_id == t.id and edge.target_id == con.id:
                            contributing_things.add(t.id)
                            total_coverage += edge.weight

                coverage_score = min(1.0, total_coverage)
                supported_concerns.append(
                    ConcernCoverageItemDTO(
                        concern_id=con.id,
                        concern_name=con.name,
                        owner_org_id=con.owner_org_id,
                        priority=con.priority,
                        coverage_score=round(coverage_score, 4),
                        contributing_thing_ids=sorted(contributing_things),
                        satisfied_by_effect_ids=sorted(satisfied_effects),
                    )
                )

            # 6. Cross-org dependencies (filtered by temporal validity)
            cross_org_edges: list[Any] = []
            owned_thing_ids = {t.id for t in owned_things}
            for edge in self._manifest.edges:
                if not _is_edge_active(edge, as_of_date):
                    continue
                if edge.source_id in owned_thing_ids and edge.target_id not in owned_thing_ids or edge.target_id in owned_thing_ids and edge.source_id not in owned_thing_ids:
                    cross_org_edges.append(edge)

            # 7. Portfolio ROI
            portfolio_roi = sum(
                self._calculate_thing_roi_with_states(t, gate_yields, as_of_date) for t in owned_things
            )

            return PerspectiveBriefingDTO(
                subject_org_id=subject_org_id,
                perspective_org_id=perspective_org_id,
                include_descendants=include_descendants,
                as_of_date=as_of_date,
                owned_things=owned_things,
                supported_concerns=supported_concerns,
                cross_org_dependencies=cross_org_edges,
                portfolio_roi_score=round(portfolio_roi, 6),
                total_committed_cost=total_cost,
                executive_summary_narrative=None,
                strategic_gaps=[],
            )

    def build_tech_tree_view(
        self,
        as_of_date: date,
        stratification_mode: TechTreeStratificationMode,
        org_filter: str | None = None,
    ) -> TechTreeViewDTO:
        """Construct the stratified 4X Game-Style Tech Tree layout."""
        with self._lock:
            tree_view, _ = build_tech_tree_graph(
                self._manifest,
                as_of_date,
                stratification_mode,
                org_filter,
            )
            return tree_view

    def simulate_milestone_slip(
        self,
        request: SlipSimulationRequestDTO,
        as_of_date: date,
    ) -> SlipSimulationResponseDTO:
        """Simulate milestone slip and calculate downstream blast radius."""
        with self._lock:
            _, base_ms_states = build_tech_tree_graph(
                self._manifest,
                as_of_date,
                TechTreeStratificationMode.TRL_TIERS,
            )
            base_gate_yields = {
                g.id: evaluate_causal_gate_yield(g, base_ms_states)
                for g in self._manifest.causal_gates
            }
            base_roi = sum(
                self._calculate_thing_roi_with_states(t, base_gate_yields, as_of_date)
                for t in self._manifest.things
            )

            def calc_roi_helper(ms_states: dict[str, TechTreeNodeState], g_yields: dict[str, float]) -> float:
                return sum(
                    self._calculate_thing_roi_with_states(t, g_yields, as_of_date)
                    for t in self._manifest.things
                )

            return simulate_slip_propagation(
                manifest=self._manifest,
                request=request,
                as_of_date=as_of_date,
                base_roi=base_roi,
                calculate_roi_fn=calc_roi_helper,
            )

    def evaluate_tradeoff_matrix(
        self,
        proposed_thing_ids: list[str],
        as_of_date: date,
    ) -> TradeoffProposalComparisonDTO:
        """Evaluate portfolio tradeoff between competing subsets of Things."""
        with self._lock:
            selected_things = [t for t in self._manifest.things if t.id in proposed_thing_ids]
            total_cost = sum(t.estimated_cost for t in selected_things)

            _, ms_states = build_tech_tree_graph(
                self._manifest,
                as_of_date,
                TechTreeStratificationMode.TRL_TIERS,
            )
            gate_yields = {
                g.id: evaluate_causal_gate_yield(g, ms_states) for g in self._manifest.causal_gates
            }

            agg_roi = sum(
                self._calculate_thing_roi_with_states(t, gate_yields, as_of_date) for t in selected_things
            )

            coverage_deltas: dict[str, float] = {}
            for c in self._manifest.concerns:
                delta = 0.0
                for t in selected_things:
                    for edge in self._manifest.edges:
                        if not _is_edge_active(edge, as_of_date):
                            continue
                        if edge.source_id == t.id and edge.target_id == c.id:
                            delta += edge.weight
                coverage_deltas[c.id] = round(min(1.0, delta), 4)

            unlocked_effects: list[str] = []
            for g in self._manifest.causal_gates:
                if any(c.thing_id in proposed_thing_ids for c in g.contributors):
                    for eff in self._manifest.effects:
                        if eff.causal_gate_id == g.id:
                            unlocked_effects.append(eff.id)

            return TradeoffProposalComparisonDTO(
                proposed_thing_ids=proposed_thing_ids,
                total_cost=total_cost,
                aggregate_roi=round(agg_roi, 10),
                concern_coverage_deltas=coverage_deltas,
                unlocked_effect_ids=sorted(set(unlocked_effects)),
                reasoning_recommendation=None,
            )

    def build_thing_focal_dashboard(
        self,
        thing_id: str,
        as_of_date: date,
        telemetry_rollups: list[TelemetryRollupDTO],
    ) -> ThingFocalDashboardDTO:
        """Generate a 2-hop focal ego-network dashboard centered on a single Thing."""
        with self._lock:
            thing = next((t for t in self._manifest.things if t.id == thing_id), None)
            if not thing:
                dummy = ThingDTO(
                    id=thing_id,
                    name=thing_id,
                    description="",
                    lifecycle="PROPOSED",
                    owner_org_id="",
                    estimated_cost=0.0,
                    risk_factor=1.0,
                )
                return ThingFocalDashboardDTO(
                    thing=dummy,
                    upstream_dependencies=[],
                    downstream_dependents=[],
                    produced_effects=[],
                    telemetry_rollups=[],
                    impacted_concerns=[],
                    direct_roi=0.0,
                )

            upstream_ids: set[str] = set()
            downstream_ids: set[str] = set()
            for edge in self._manifest.edges:
                if not _is_edge_active(edge, as_of_date):
                    continue
                if edge.source_id == thing_id:
                    downstream_ids.add(edge.target_id)
                elif edge.target_id == thing_id:
                    upstream_ids.add(edge.source_id)

            upstream_things = [t for t in self._manifest.things if t.id in upstream_ids]
            downstream_things = [t for t in self._manifest.things if t.id in downstream_ids]

            produced: list[EffectDTO] = []
            for g in self._manifest.causal_gates:
                if any(c.thing_id == thing_id for c in g.contributors):
                    for e in self._manifest.effects:
                        if e.causal_gate_id == g.id:
                            produced.append(e)

            direct_roi = self.calculate_thing_roi(thing_id, as_of_date)

            impacted_concerns: list[ConcernCoverageItemDTO] = []
            for edge in self._manifest.edges:
                if not _is_edge_active(edge, as_of_date):
                    continue
                if edge.source_id == thing_id and edge.relationship in (RelationshipType.IMPACTS, RelationshipType.SUPPORTS):
                    con = next((c for c in self._manifest.concerns if c.id == edge.target_id), None)
                    if con:
                        impacted_concerns.append(
                            ConcernCoverageItemDTO(
                                concern_id=con.id,
                                concern_name=con.name,
                                owner_org_id=con.owner_org_id,
                                priority=con.priority,
                                coverage_score=min(1.0, edge.weight),
                                contributing_thing_ids=[thing_id],
                                satisfied_by_effect_ids=[e.id for e in produced],
                            )
                        )

            return ThingFocalDashboardDTO(
                thing=thing,
                upstream_dependencies=upstream_things,
                downstream_dependents=downstream_things,
                produced_effects=produced,
                telemetry_rollups=[r for r in telemetry_rollups if r.thing_id == thing_id],
                impacted_concerns=impacted_concerns,
                direct_roi=direct_roi,
            )

    def evaluate_pareto_frontier(
        self,
        budget_ceiling: float,
        as_of_date: date | None = None,
    ) -> ParetoFrontierDTO:
        """Evaluate Pareto-optimal frontier of candidate Things under a budget ceiling."""
        eff_date = as_of_date or date.today()
        with self._lock:
            candidates = [t for t in self._manifest.things if t.lifecycle == LifecycleStatus.PROPOSED]
            if not candidates:
                candidates = list(self._manifest.things)

            if not candidates:
                return ParetoFrontierDTO(budget_ceiling=budget_ceiling, optimal_portfolios=[])

            max_k = min(len(candidates), 10)
            valid_portfolios: list[TradeoffProposalComparisonDTO] = []

            for k in range(1, max_k + 1):
                for combo in itertools.combinations(candidates, k):
                    cost = sum(t.estimated_cost for t in combo)
                    if cost <= budget_ceiling:
                        thing_ids = [t.id for t in combo]
                        tradeoff = self.evaluate_tradeoff_matrix(thing_ids, eff_date)
                        valid_portfolios.append(tradeoff)

            optimal: list[TradeoffProposalComparisonDTO] = []
            for p1 in valid_portfolios:
                is_dominated = False
                for p2 in valid_portfolios:
                    if p1 is p2:
                        continue
                    if (
                        p2.total_cost <= p1.total_cost
                        and p2.aggregate_roi >= p1.aggregate_roi
                        and (p2.total_cost < p1.total_cost or p2.aggregate_roi > p1.aggregate_roi)
                    ):
                        is_dominated = True
                        break
                if not is_dominated and not any(
                    opt.total_cost == p1.total_cost and opt.aggregate_roi == p1.aggregate_roi
                    for opt in optimal
                ):
                    optimal.append(p1)

            optimal.sort(key=lambda p: (p.total_cost, p.aggregate_roi))

            return ParetoFrontierDTO(
                budget_ceiling=budget_ceiling,
                optimal_portfolios=optimal,
            )

    def validate_manifest_diagnostics(
        self,
        manifest: BijouManifestDTO | None = None,
    ) -> DiagnosticReportDTO:
        """Perform topological and diagnostic linting on a manifest or current graph."""
        with self._lock:
            m = manifest or self._manifest
            diag_graph = nx.DiGraph()

            for t in m.things:
                diag_graph.add_node(t.id)
            for c in m.concerns:
                diag_graph.add_node(c.id)
            for e in m.effects:
                diag_graph.add_node(e.id)
            for g in m.causal_gates:
                diag_graph.add_node(g.id)
                for contrib in g.contributors:
                    diag_graph.add_edge(contrib.thing_id, g.id)
            for org in m.organizations:
                diag_graph.add_node(org.id)

            for edge in m.edges:
                diag_graph.add_edge(edge.source_id, edge.target_id)
                if edge.source_milestone_id and edge.target_milestone_id:
                    diag_graph.add_edge(edge.source_milestone_id, edge.target_milestone_id)

            blockers: list[str] = []
            warnings: list[str] = []
            cycles_detected: list[list[str]] = []

            try:
                raw_cycles = list(nx.simple_cycles(diag_graph))
                for cycle in raw_cycles:
                    cycles_detected.append(cycle)
                    blockers.append(f"Cycle detected: {' -> '.join(cycle)}")
            except nx.NetworkXError:
                pass

            orphans = [node for node in diag_graph.nodes if diag_graph.degree(node) == 0]
            for orphan in orphans:
                warnings.append(f"Orphan node detected: {orphan}")

            return DiagnosticReportDTO(
                blockers=blockers,
                warnings=warnings,
                cycles_detected=cycles_detected,
            )


    def build_clustered_spheres_view(
        self,
        as_of_date: date,
        org_filter: str | None = None,
    ) -> ClusteredSpheresViewDTO:
        with self._lock:
            palette = [
                "#06b6d4",
                "#3b82f6",
                "#8b5cf6",
                "#ec4899",
                "#10b981",
                "#f59e0b",
                "#6366f1",
                "#14b8a6",
            ]

            org_map = {org.id: org for org in self._manifest.organizations}
            org_colors = {}
            for i, org in enumerate(self._manifest.organizations):
                org_colors[org.id] = palette[i % len(palette)]

            active_things = list(self._manifest.things)
            if org_filter:
                active_things = [t for t in active_things if t.owner_org_id == org_filter]

            active_thing_ids = {t.id for t in active_things}

            upstream_map = {t.id: [] for t in active_things}
            downstream_map = {t.id: [] for t in active_things}
            edges_list = []
            macro_counts = {}

            for edge in self._manifest.edges:
                if not _is_edge_active(edge, as_of_date):
                    continue

                src_id = edge.source_id
                tgt_id = edge.target_id

                if src_id in active_thing_ids and tgt_id in active_thing_ids:
                    downstream_map[src_id].append(tgt_id)
                    upstream_map[tgt_id].append(src_id)

                    src_thing = next((t for t in active_things if t.id == src_id), None)
                    tgt_thing = next((t for t in active_things if t.id == tgt_id), None)
                    src_org = src_thing.owner_org_id if src_thing else ""
                    tgt_org = tgt_thing.owner_org_id if tgt_thing else ""
                    is_cross = bool(src_org and tgt_org and src_org != tgt_org)

                    edges_list.append(
                        ClusteredDependencyEdgeDTO(
                            edge_id=edge.id,
                            source_thing_id=src_id,
                            target_thing_id=tgt_id,
                            relationship=edge.relationship,
                            is_cross_org=is_cross,
                            source_org_id=src_org,
                            target_org_id=tgt_org,
                        )
                    )

                    if is_cross:
                        pair = (src_org, tgt_org)
                        if pair not in macro_counts:
                            macro_counts[pair] = []
                        if src_id not in macro_counts[pair]:
                            macro_counts[pair].append(src_id)
                        if tgt_id not in macro_counts[pair]:
                            macro_counts[pair].append(tgt_id)

            nodes_list = []
            for t in active_things:
                max_trl = max([m.trl for m in t.milestones], default=1) if t.milestones else 1
                cross_partners = set()
                for edge in edges_list:
                    if edge.source_thing_id == t.id and edge.is_cross_org:
                        cross_partners.add(edge.target_org_id)
                    elif edge.target_thing_id == t.id and edge.is_cross_org:
                        cross_partners.add(edge.source_org_id)

                nodes_list.append(
                    ClusteredThingNodeDTO(
                        thing_id=t.id,
                        name=t.name,
                        description=t.description,
                        cluster_org_id=t.owner_org_id,
                        lifecycle=t.lifecycle,
                        trl=max_trl,
                        estimated_cost=t.estimated_cost,
                        risk_factor=t.risk_factor,
                        upstream_thing_ids=upstream_map.get(t.id, []),
                        downstream_thing_ids=downstream_map.get(t.id, []),
                        is_cross_cutting=len(cross_partners) > 0,
                        cross_org_partner_ids=sorted(list(cross_partners)),
                    )
                )

            clusters_list = []
            for org in self._manifest.organizations:
                if org_filter and org.id != org_filter:
                    continue
                owned = [t for t in active_things if t.owner_org_id == org.id]
                tot_cost = sum(t.estimated_cost for t in owned)
                clusters_list.append(
                    OrganizationClusterDTO(
                        org_id=org.id,
                        org_name=org.name,
                        echelon_level=org.echelon_level,
                        mission_statement=org.mission_statement,
                        color=org_colors.get(org.id, "#0284c7"),
                        total_cost=tot_cost,
                        thing_ids=[t.id for t in owned],
                    )
                )

            macro_edges_list = []
            for (src_org, tgt_org), things_inv in macro_counts.items():
                macro_edges_list.append(
                    MacroOrgDependencyEdgeDTO(
                        source_org_id=src_org,
                        target_org_id=tgt_org,
                        dependency_count=len(things_inv),
                        involved_thing_ids=sorted(things_inv),
                    )
                )

            return ClusteredSpheresViewDTO(
                as_of_date=as_of_date,
                clusters=clusters_list,
                nodes=nodes_list,
                edges=edges_list,
                macro_org_edges=macro_edges_list,
            )
