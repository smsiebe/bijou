"""4X Game-Style Tech Tree layout stratification and milestone slip simulation."""

from collections import defaultdict
from collections.abc import Callable
from datetime import date, timedelta

import networkx as nx

from bijou.core.contracts.enums import (
    CausalMechanismType,
    RelationshipType,
    TechTreeNodeState,
    TechTreeStratificationMode,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    GraphEdgeDTO,
    MilestoneDTO,
    ThingDTO,
)
from bijou.core.contracts.views import (
    SlipSimulationRequestDTO,
    SlipSimulationResponseDTO,
    TechTreeEdgeDTO,
    TechTreeNodeDTO,
    TechTreeViewDTO,
)
from bijou.core.engine.causal import evaluate_causal_gate_yield, resolve_milestone_state


def _is_edge_active(edge: GraphEdgeDTO, as_of_date: date) -> bool:
    """Return False if edge is outside its effective_start or effective_end window relative to as_of_date."""
    if edge.effective_start and as_of_date < edge.effective_start:
        return False
    return not (edge.effective_end and as_of_date > edge.effective_end)


def build_tech_tree_graph(
    manifest: BijouManifestDTO,
    as_of_date: date,
    stratification_mode: TechTreeStratificationMode,
    org_filter: str | None = None,
    simulated_slips: dict[str, int] | None = None,
    cancelled_milestone_ids: set[str] | None = None,
) -> tuple[TechTreeViewDTO, dict[str, TechTreeNodeState]]:
    """Build a deterministic stratified 4X Tech Tree view."""
    simulated_slips = simulated_slips or {}
    cancelled_milestone_ids = cancelled_milestone_ids or set()

    # Index milestones
    milestones_by_id: dict[str, tuple[ThingDTO, MilestoneDTO]] = {}
    for t in manifest.things:
        if org_filter and t.owner_org_id != org_filter:
            continue
        for ms in t.milestones:
            milestones_by_id[ms.id] = (t, ms)

    # Pre-calculate effective dates with simulated slips
    eff_target_dates: dict[str, date] = {}
    eff_dates: dict[str, date] = {}
    for ms_id, (thing, ms) in milestones_by_id.items():
        slip = simulated_slips.get(ms_id, 0)
        eff_target = ms.target_date + timedelta(days=slip)
        eff_target_dates[ms_id] = eff_target
        if ms.actual_date:
            eff_act = ms.actual_date + timedelta(days=slip) if slip > 0 else ms.actual_date
        else:
            eff_act = None
        eff_dates[ms_id] = eff_act or eff_target

    # Build DAG of milestone dependencies
    ms_dag = nx.DiGraph()
    for ms_id in milestones_by_id:
        ms_dag.add_node(ms_id)

    # Within a Thing, earlier milestones are implicit prerequisites of subsequent ones
    for t in manifest.things:
        sorted_ms = sorted(t.milestones, key=lambda m: m.sequence_index)
        for i in range(len(sorted_ms) - 1):
            ms_dag.add_edge(sorted_ms[i].id, sorted_ms[i + 1].id)

    # Explicit cross-thing milestone edges (filtered by active date window)
    for edge in manifest.edges:
        if not _is_edge_active(edge, as_of_date):
            continue
        if (
            edge.relationship == RelationshipType.DEPENDS_ON
            and edge.source_milestone_id
            and edge.target_milestone_id
            and edge.target_milestone_id in ms_dag
            and edge.source_milestone_id in ms_dag
        ):
            ms_dag.add_edge(edge.target_milestone_id, edge.source_milestone_id)

    # Topologically evaluate milestone states
    milestone_states: dict[str, TechTreeNodeState] = {}
    if nx.is_directed_acyclic_graph(ms_dag):
        topo_order = list(nx.topological_sort(ms_dag))
    else:
        topo_order = sorted(milestones_by_id.keys())

    for ms_id in topo_order:
        if ms_id not in milestones_by_id:
            continue
        thing, ms = milestones_by_id[ms_id]
        is_cancelled = ms_id in cancelled_milestone_ids
        slip = simulated_slips.get(ms_id, 0)
        is_slipped = slip > 0

        upstream_preds = list(ms_dag.predecessors(ms_id))
        upstream_states = [milestone_states[p] for p in upstream_preds if p in milestone_states]

        # Check if an upstream prerequisite's slipped target date exceeds this milestone's target date
        has_schedule_violation = False
        for p in upstream_preds:
            if p in eff_target_dates and eff_target_dates[p] > ms.target_date:
                has_schedule_violation = True
                break

        state = resolve_milestone_state(
            milestone=ms,
            as_of_date=as_of_date,
            upstream_prerequisite_states=upstream_states,
            is_cancelled=is_cancelled,
            effective_date=eff_dates[ms_id],
            effective_target_date=eff_target_dates[ms_id],
            is_slipped=is_slipped,
            has_schedule_violation=has_schedule_violation,
        )
        milestone_states[ms_id] = state

    # Stratification Layout
    tiers: list[dict[str, str | int]] = []
    lanes_set: set[str] = set()

    # Pre-calculate topological depths
    topo_depths: dict[str, int] = {}
    for ms_id in topo_order:
        preds = list(ms_dag.predecessors(ms_id))
        topo_depths[ms_id] = max((topo_depths[p] + 1 for p in preds if p in topo_depths), default=0)

    # Pre-calculate fiscal eras
    fiscal_eras: list[tuple[int, int]] = sorted({
        (
            (ms.target_date + timedelta(days=simulated_slips.get(ms.id, 0))).year,
            ((ms.target_date + timedelta(days=simulated_slips.get(ms.id, 0))).month - 1) // 6 + 1,
        )
        for _, ms in milestones_by_id.values()
    })
    era_to_order = {era: idx for idx, era in enumerate(fiscal_eras)}

    if stratification_mode == TechTreeStratificationMode.TRL_TIERS:
        tiers = [
            {"tier_id": "tier-foundational", "tier_name": "TRL 1-3 (Foundational)", "order": 0},
            {"tier_id": "tier-development", "tier_name": "TRL 4-6 (Development)", "order": 1},
            {"tier_id": "tier-fielded", "tier_name": "TRL 7-9 (Operational)", "order": 2},
        ]
    elif stratification_mode == TechTreeStratificationMode.FISCAL_ERA:
        for idx, (yr, hf) in enumerate(fiscal_eras):
            tiers.append({"tier_id": f"era-{yr}-h{hf}", "tier_name": f"FY{yr} H{hf}", "order": idx})
    else:  # TOPOLOGICAL_DEPTH
        max_depth = max(topo_depths.values(), default=0)
        for d in range(max_depth + 1):
            tiers.append({"tier_id": f"depth-{d}", "tier_name": f"Level {d}", "order": d})

    # Find unlocked effects per milestone
    milestone_unlocked_effects: dict[str, list[str]] = defaultdict(list)
    for gate in manifest.causal_gates:
        matching_effects = [e.id for e in manifest.effects if e.causal_gate_id == gate.id]
        for contrib in gate.contributors:
            if contrib.milestone_id:
                milestone_unlocked_effects[contrib.milestone_id].extend(matching_effects)

    nodes: list[TechTreeNodeDTO] = []
    for ms_id in sorted(milestones_by_id.keys()):
        thing, ms = milestones_by_id[ms_id]
        lanes_set.add(ms.lane)
        eff_date = ms.target_date + timedelta(days=simulated_slips.get(ms.id, 0))

        if stratification_mode == TechTreeStratificationMode.TRL_TIERS:
            if ms.trl <= 3:
                t_id, t_order = "tier-foundational", 0
            elif ms.trl <= 6:
                t_id, t_order = "tier-development", 1
            else:
                t_id, t_order = "tier-fielded", 2
        elif stratification_mode == TechTreeStratificationMode.FISCAL_ERA:
            era = (eff_date.year, (eff_date.month - 1) // 6 + 1)
            t_order = era_to_order.get(era, 0)
            t_id = f"era-{era[0]}-h{era[1]}"
        else:  # TOPOLOGICAL_DEPTH
            t_order = topo_depths.get(ms.id, 0)
            t_id = f"depth-{t_order}"

        nodes.append(
            TechTreeNodeDTO(
                node_id=f"{thing.id}:{ms.id}",
                thing_id=thing.id,
                milestone_id=ms.id,
                title=ms.name,
                thing_name=thing.name,
                owner_org_id=thing.owner_org_id,
                tier_id=t_id,
                tier_order=t_order,
                lane_id=ms.lane,
                state=milestone_states[ms.id],
                target_date=eff_date,
                actual_date=ms.actual_date,
                cost_estimate=thing.estimated_cost + ms.cost_delta,
                trl=ms.trl,
                unlocked_effect_ids=sorted(set(milestone_unlocked_effects.get(ms.id, []))),
            )
        )

    # Collect sorted swimlanes
    lanes = [{"lane_id": lane, "lane_name": lane} for lane in sorted(lanes_set)]

    # Compute Edges
    edges: list[TechTreeEdgeDTO] = []
    node_id_map = {ms.id: f"{t.id}:{ms.id}" for t, ms in milestones_by_id.values()}

    for u, v in ms_dag.edges():
        if u in node_id_map and v in node_id_map:
            u_state = milestone_states.get(u, TechTreeNodeState.LOCKED)
            is_satisfied = u_state == TechTreeNodeState.ACHIEVED
            edge_id = f"edge-{u}-{v}"
            edges.append(
                TechTreeEdgeDTO(
                    edge_id=edge_id,
                    source_node_id=node_id_map[u],
                    target_node_id=node_id_map[v],
                    gate_type=CausalMechanismType.ADDITIVE,
                    is_satisfied=is_satisfied,
                    is_critical_path=topo_depths.get(v, 0) > 1,
                )
            )

    return TechTreeViewDTO(
        as_of_date=as_of_date,
        stratification_mode=stratification_mode,
        tiers=tiers,
        lanes=lanes,
        nodes=nodes,
        edges=edges,
    ), milestone_states


def simulate_slip_propagation(
    manifest: BijouManifestDTO,
    request: SlipSimulationRequestDTO,
    as_of_date: date,
    base_roi: float,
    calculate_roi_fn: Callable[[dict[str, TechTreeNodeState], dict[str, float]], float],
) -> SlipSimulationResponseDTO:
    """Propagate a milestone slip or cancellation downstream and compute blast radius."""
    simulated_slips: dict[str, int] = {request.milestone_id: request.slip_days}
    cancelled_ids: set[str] = {request.milestone_id} if request.simulate_cancellation else set()

    # Find the target milestone
    target_ms: MilestoneDTO | None = None
    for t in manifest.things:
        for ms in t.milestones:
            if ms.id == request.milestone_id:
                target_ms = ms
                break
        if target_ms:
            break

    if target_ms is None:
        return SlipSimulationResponseDTO(
            slipped_milestone_id=request.milestone_id,
            slip_days=request.slip_days,
            cancelled=request.simulate_cancellation,
            impacted_node_states={},
            degraded_effect_ids=[],
            broken_concern_ids=[],
            roi_delta=0.0,
        )

    # Build baseline tech tree
    _, baseline_states = build_tech_tree_graph(
        manifest,
        as_of_date,
        TechTreeStratificationMode.TRL_TIERS,
    )

    # Evaluate baseline gate yields
    baseline_gate_yields = {
        g.id: evaluate_causal_gate_yield(g, baseline_states) for g in manifest.causal_gates
    }

    # Propagate date slip downstream
    ms_dag = nx.DiGraph()
    for t in manifest.things:
        sorted_ms = sorted(t.milestones, key=lambda m: m.sequence_index)
        for i in range(len(sorted_ms) - 1):
            ms_dag.add_edge(sorted_ms[i].id, sorted_ms[i + 1].id)
    for edge in manifest.edges:
        if not _is_edge_active(edge, as_of_date):
            continue
        if edge.relationship == RelationshipType.DEPENDS_ON and edge.source_milestone_id and edge.target_milestone_id:
            ms_dag.add_edge(edge.target_milestone_id, edge.source_milestone_id)

    # Collect all downstream dependents
    if request.milestone_id in ms_dag:
        downstream = nx.descendants(ms_dag, request.milestone_id)
        for dep_ms_id in downstream:
            simulated_slips[dep_ms_id] = max(simulated_slips.get(dep_ms_id, 0), request.slip_days)
            if request.simulate_cancellation:
                cancelled_ids.add(dep_ms_id)

    # Re-build tree with slips applied
    _, post_slip_states = build_tech_tree_graph(
        manifest,
        as_of_date,
        TechTreeStratificationMode.TRL_TIERS,
        simulated_slips=simulated_slips,
        cancelled_milestone_ids=cancelled_ids,
    )

    # Identify impacted nodes
    impacted_states: dict[str, TechTreeNodeState] = {}
    for ms_id, new_state in post_slip_states.items():
        old_state = baseline_states.get(ms_id)
        if old_state != new_state:
            impacted_states[ms_id] = new_state

    # Evaluate post-slip gate yields
    post_gate_yields = {
        g.id: evaluate_causal_gate_yield(g, post_slip_states) for g in manifest.causal_gates
    }

    degraded_effect_ids: list[str] = []
    for effect in manifest.effects:
        is_degraded = False
        if effect.causal_gate_id:
            base_yield = baseline_gate_yields.get(effect.causal_gate_id, 1.0)
            new_yield = post_gate_yields.get(effect.causal_gate_id, 1.0)
            if new_yield < base_yield:
                is_degraded = True
            else:
                gate = next((g for g in manifest.causal_gates if g.id == effect.causal_gate_id), None)
                if gate:
                    for contrib in gate.contributors:
                        if (
                            contrib.milestone_id
                            and contrib.milestone_id in impacted_states
                            and impacted_states[contrib.milestone_id]
                            in (
                                TechTreeNodeState.BLOCKED,
                                TechTreeNodeState.LOCKED,
                            )
                        ):
                            is_degraded = True
                            break
        if is_degraded:
            degraded_effect_ids.append(effect.id)

    # Broken concerns
    broken_concern_ids: list[str] = []
    for effect in manifest.effects:
        if effect.id in degraded_effect_ids:
            for link in effect.satisfies_concerns:
                if link.concern_id not in broken_concern_ids:
                    broken_concern_ids.append(link.concern_id)

    # Compute post-slip ROI
    post_roi = calculate_roi_fn(post_slip_states, post_gate_yields)
    roi_delta = post_roi - base_roi

    return SlipSimulationResponseDTO(
        slipped_milestone_id=request.milestone_id,
        slip_days=request.slip_days,
        cancelled=request.simulate_cancellation,
        impacted_node_states=impacted_states,
        degraded_effect_ids=sorted(degraded_effect_ids),
        broken_concern_ids=sorted(broken_concern_ids),
        roi_delta=round(roi_delta, 4),
    )
