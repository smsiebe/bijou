"""State-aware and dependency-relative forecasting engine for Effort progression trees."""

from datetime import date, timedelta

import networkx as nx

from bijou.core.contracts.enums import (
    BlockingMode,
    EffortState,
    ForecastHorizonStatus,
    RiskStatus,
)
from bijou.core.contracts.models import (
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    OrgEffortEdgeDTO,
    RiskDTO,
)
from bijou.core.contracts.views import (
    ForecastedEffortNodeDTO,
    IndirectBenefitPathDTO,
)
from bijou.core.ports.exceptions import GraphCycleError


def detect_cycles_in_graph(nodes: list[str], directed_edges: list[tuple[str, str]]) -> list[list[str]]:
    """Detect simple cycles in a directed graph."""
    g = nx.DiGraph()
    g.add_nodes_from(nodes)
    g.add_edges_from(directed_edges)
    try:
        return [list(cycle) for cycle in nx.simple_cycles(g)]
    except nx.NetworkXError:
        return []


def resolve_effort_forecasts(
    efforts: list[EffortDTO],
    effort_edges: list[EffortEffortEdgeDTO],
    org_effort_edges: list[OrgEffortEdgeDTO],
    effort_interest_edges: list[EffortInterestEdgeDTO],
    indirect_paths: list[IndirectBenefitPathDTO],
    as_of_date: date,
    extra_slips: dict[str, int] | None = None,
    toggle_mitigators: dict[str, bool] | None = None,
    cancelled_effort_ids: set[str] | None = None,
    extra_risks: list[RiskDTO] | None = None,
) -> list[ForecastedEffortNodeDTO]:
    """Resolve Effort progression forecasts respecting explicit, duration-only, and unknown timing."""
    slips_map = extra_slips or {}
    mit_toggles = toggle_mitigators or {}
    cancelled_ids = cancelled_effort_ids or set()
    extra_risk_by_effort: dict[str, list[RiskDTO]] = {}
    for r in extra_risks or []:
        extra_risk_by_effort.setdefault(r.effort_id, []).append(r)

    efforts_by_id = {e.id: e for e in efforts}

    # Build full Effort dependency DAG for topological ordering & SPOF analysis
    dag = nx.DiGraph()
    for e in efforts:
        dag.add_node(e.id)

    blocking_preds: dict[str, list[str]] = {e.id: [] for e in efforts}
    informing_preds: dict[str, list[str]] = {e.id: [] for e in efforts}

    for edge in effort_edges:
        if edge.source_effort_id not in efforts_by_id or edge.target_effort_id not in efforts_by_id:
            continue
        dag.add_edge(edge.source_effort_id, edge.target_effort_id, blocking_mode=edge.blocking_mode)
        if edge.blocking_mode == BlockingMode.BLOCKING:
            blocking_preds[edge.target_effort_id].append(edge.source_effort_id)
        else:
            informing_preds[edge.target_effort_id].append(edge.source_effort_id)

    if not nx.is_directed_acyclic_graph(dag):
        cycle = nx.find_cycle(dag)
        cycle_nodes = [u for u, _v in cycle] + [cycle[0][0]]
        raise GraphCycleError(cycle_nodes)

    topo_order = list(nx.topological_sort(dag))

    # Centrality on blocking subgraph for SPOF detection
    blocking_dag = nx.DiGraph()
    for e in efforts:
        blocking_dag.add_node(e.id)
    for edge in effort_edges:
        if (
            edge.blocking_mode == BlockingMode.BLOCKING
            and edge.source_effort_id in efforts_by_id
            and edge.target_effort_id in efforts_by_id
        ):
            blocking_dag.add_edge(edge.source_effort_id, edge.target_effort_id)

    centrality = nx.betweenness_centrality(blocking_dag) if len(efforts) > 2 else {e.id: 0.0 for e in efforts}

    # Precompute mappings for Orgs, Interests, Indirect Beneficiaries, Coverage
    funding_orgs_map: dict[str, list[str]] = {}
    org_alloc_totals: dict[str, dict[str, float]] = {}
    for oe in org_effort_edges:
        funding_orgs_map.setdefault(oe.effort_id, [])
        if oe.org_id not in funding_orgs_map[oe.effort_id]:
            funding_orgs_map[oe.effort_id].append(oe.org_id)
        org_alloc_totals.setdefault(oe.effort_id, {})
        org_alloc_totals[oe.effort_id][oe.org_id] = (
            org_alloc_totals[oe.effort_id].get(oe.org_id, 0.0) + oe.allocation_amount
        )

    aligned_interests_map: dict[str, list[str]] = {}
    for ei in effort_interest_edges:
        aligned_interests_map.setdefault(ei.effort_id, [])
        if ei.interest_id not in aligned_interests_map[ei.effort_id]:
            aligned_interests_map[ei.effort_id].append(ei.interest_id)

    indirect_org_map: dict[str, list[str]] = {}
    for path in indirect_paths:
        indirect_org_map.setdefault(path.effort_id, [])
        if path.beneficiary_org_id not in indirect_org_map[path.effort_id]:
            indirect_org_map[path.effort_id].append(path.beneficiary_org_id)

    # Topological forward pass
    depth_map: dict[str, int] = {}
    resolved: dict[str, ForecastedEffortNodeDTO] = {}

    for eff_id in topo_order:
        effort = efforts_by_id[eff_id]

        # Resolve effective state & mitigators/risks with scenario overrides
        effective_state = EffortState.CANCELLED if eff_id in cancelled_ids else effort.state
        combined_risks = list(effort.risks) + extra_risk_by_effort.get(eff_id, [])
        active_risks = [r for r in combined_risks if r.status == RiskStatus.ACTIVE]

        exercised_mits = []
        unexercised_mits = []
        effective_req_list = list(effort.resource_requirements)

        for m in effort.mitigators:
            is_ex = mit_toggles.get(m.id, m.is_exercised)
            if is_ex:
                exercised_mits.append(m)
                effective_req_list.extend(m.additional_requirements)
            else:
                unexercised_mits.append(m)

        targeted_reduction: dict[str, int] = {}
        targeted_factor: dict[str, float] = {}
        untargeted_slip_reduction = 0
        for m in exercised_mits:
            if m.risk_id:
                targeted_reduction[m.risk_id] = targeted_reduction.get(m.risk_id, 0) + m.slip_reduction_days
                targeted_factor[m.risk_id] = min(
                    1.0, targeted_factor.get(m.risk_id, 0.0) + m.risk_reduction_factor
                )
            else:
                untargeted_slip_reduction += m.slip_reduction_days

        residual_risk_slip = 0
        for r in active_risks:
            red_days = targeted_reduction.get(r.id, 0)
            if red_days == 0 and r.id in targeted_factor:
                red_days = int(round(r.potential_slip_days * targeted_factor[r.id]))
            residual_risk_slip += max(0, r.potential_slip_days - red_days)

        external_slip = slips_map.get(eff_id, 0)
        net_slip_days = max(0, residual_risk_slip - untargeted_slip_reduction + external_slip)

        # Topological depth
        all_preds = blocking_preds[eff_id] + informing_preds[eff_id]
        depth_map[eff_id] = max((depth_map[p] + 1 for p in all_preds if p in depth_map), default=0)

        # Resource coverage ratio computation
        req_count = len(effective_req_list)
        total_est_cost = sum(
            (r.estimated_cost_usd or (r.quantity if r.unit.upper() == "USD" else 0.0))
            for r in effective_req_list
        )
        effort_org_edges = [oe for oe in org_effort_edges if oe.effort_id == eff_id]
        if req_count == 0:
            coverage_ratio = 1.0 if effort_org_edges else 0.0
        else:
            matched = 0
            covered_req_ids = {oe.requirement_id for oe in effort_org_edges if oe.requirement_id}
            for req in effective_req_list:
                if req.id in covered_req_ids or any(oe.resourcing_type == req.category and oe.allocation_amount >= req.quantity for oe in effort_org_edges):
                    matched += 1
            coverage_ratio = round(min(1.0, matched / req_count), 3)

        # Primary org = highest monetary/unit contributor or first funder
        funders = funding_orgs_map.get(eff_id, [])
        primary_org: str | None = None
        if org_alloc_totals.get(eff_id):
            primary_org = max(org_alloc_totals[eff_id].items(), key=lambda x: x[1])[0]
        elif funders:
            primary_org = funders[0]

        # Timing & Horizon computation based on state & blocking dependencies
        horizon_status: ForecastHorizonStatus
        f_start: date | None = None
        f_end: date | None = None
        rel_offset: int | None = None
        blocked_unknown: list[str] = []

        if effective_state == EffortState.CANCELLED:
            horizon_status = ForecastHorizonStatus.CANCELLED
        elif effective_state == EffortState.COMPLETED:
            # Completed efforts are historical anchors; date doesn't block anything
            horizon_status = ForecastHorizonStatus.COMPLETED_HISTORICAL
            f_start = effort.start_date
            f_end = effort.end_date or (
                (effort.start_date + timedelta(days=effort.estimated_duration_days))
                if (effort.start_date and effort.estimated_duration_days)
                else None
            )
        elif effective_state == EffortState.IN_WORK:
            if effort.end_date is not None:
                f_start = effort.start_date
                f_end = effort.end_date + timedelta(days=net_slip_days)
                horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
            elif effort.start_date is not None and effort.estimated_duration_days is not None:
                f_start = effort.start_date
                f_end = effort.start_date + timedelta(days=effort.estimated_duration_days + net_slip_days)
                horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
            elif effort.estimated_duration_days is not None and not any(
                resolved[p].horizon_status in (ForecastHorizonStatus.OPEN_ENDED_ACTIVE, ForecastHorizonStatus.RELATIVE_TO_DEPENDENCY, ForecastHorizonStatus.UNSCHEDULED_PLAN)
                for p in blocking_preds[eff_id]
            ):
                f_start = effort.start_date or as_of_date
                f_end = f_start + timedelta(days=effort.estimated_duration_days + net_slip_days)
                horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
            else:
                # Open-ended active work ("closes when it closes")
                f_start = effort.start_date
                f_end = None
                horizon_status = ForecastHorizonStatus.OPEN_ENDED_ACTIVE
                if effort.estimated_duration_days is not None:
                    rel_offset = effort.estimated_duration_days + net_slip_days
        else:
            # Future states: BACKLOGGED, PLANNED, DISCOVERY_PENDING
            incomplete_blocking = [
                p
                for p in blocking_preds[eff_id]
                if resolved[p].horizon_status != ForecastHorizonStatus.COMPLETED_HISTORICAL
            ]

            unknown_blocking = [
                p
                for p in incomplete_blocking
                if resolved[p].forecast_end is None
            ]

            if unknown_blocking:
                # Relative horizon tied to completion of unknown/open upstream blocking dependencies
                horizon_status = ForecastHorizonStatus.RELATIVE_TO_DEPENDENCY
                blocked_unknown = unknown_blocking
                upstream_max_rel = max(
                    (resolved[p].relative_offset_days or 0) for p in unknown_blocking
                )
                own_dur = (effort.estimated_duration_days + net_slip_days) if effort.estimated_duration_days else 0
                rel_offset = (upstream_max_rel + own_dur) if (upstream_max_rel > 0 or own_dur > 0) else None
            elif incomplete_blocking:
                # All blocking predecessors have known forecast_end
                max_pred_end = max(resolved[p].forecast_end for p in incomplete_blocking if resolved[p].forecast_end is not None)
                earliest_start = max_pred_end
                if effort.start_date and effort.start_date > earliest_start:
                    earliest_start = effort.start_date
                f_start = earliest_start

                if effort.end_date is not None:
                    # Wait if dependency slips past our start or shifts window
                    shift = max(0, (earliest_start - effort.start_date).days) if effort.start_date else 0
                    f_end = effort.end_date + timedelta(days=shift + net_slip_days)
                    horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
                elif effort.estimated_duration_days is not None:
                    f_end = earliest_start + timedelta(days=effort.estimated_duration_days + net_slip_days)
                    horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
                else:
                    # Dependency completes at calendar date, but this effort's duration is unknown
                    horizon_status = ForecastHorizonStatus.RELATIVE_TO_DEPENDENCY
                    f_end = None
                    blocked_unknown = incomplete_blocking
            else:
                # No blocking incomplete dependencies
                if effort.end_date is not None:
                    f_start = effort.start_date
                    f_end = effort.end_date + timedelta(days=net_slip_days)
                    horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
                elif effort.estimated_duration_days is not None:
                    f_start = effort.start_date or as_of_date
                    f_end = f_start + timedelta(days=effort.estimated_duration_days + net_slip_days)
                    horizon_status = ForecastHorizonStatus.EXPLICIT_SCHEDULE
                else:
                    f_start = effort.start_date
                    f_end = None
                    horizon_status = ForecastHorizonStatus.UNSCHEDULED_PLAN

        out_blocking_count = sum(
            1 for e_edge in effort_edges
            if e_edge.source_effort_id == eff_id and e_edge.blocking_mode == BlockingMode.BLOCKING
        )
        is_spof = (centrality.get(eff_id, 0.0) > 0.15) or (out_blocking_count >= 2)

        resolved[eff_id] = ForecastedEffortNodeDTO(
            effort=effort,
            timing_mode=effort.timing_mode,
            horizon_status=horizon_status,
            forecast_start=f_start,
            forecast_end=f_end,
            relative_offset_days=rel_offset,
            blocked_by_effort_ids=blocked_unknown,
            informing_effort_ids=informing_preds[eff_id],
            topological_depth=depth_map[eff_id],
            slack_days=None,  # Computed in backward pass below for calendar nodes
            is_spof=is_spof,
            funding_org_ids=funders,
            primary_org_id=primary_org,
            aligned_interest_ids=aligned_interests_map.get(eff_id, []),
            indirect_beneficiary_org_ids=indirect_org_map.get(eff_id, []),
            total_estimated_cost_usd=round(total_est_cost, 2),
            resourcing_coverage_ratio=coverage_ratio,
            active_risk_count=len(active_risks),
            exercised_mitigator_count=len(exercised_mits),
            unexercised_mitigator_count=len(unexercised_mits),
        )

    # Backward CPM pass for calendar-anchored slack_days
    calendar_ends = [n.forecast_end for n in resolved.values() if n.forecast_end is not None]
    if calendar_ends:
        horizon_max = max(calendar_ends)
        late_start: dict[str, date] = {}
        for eff_id in reversed(topo_order):
            node = resolved[eff_id]
            if node.forecast_end is None:
                continue
            succs = [
                succ for succ in blocking_dag.successors(eff_id)
                if succ in late_start
            ]
            if succs:
                late_finish = min(late_start[s] for s in succs)
            else:
                late_finish = horizon_max
            slack = (late_finish - node.forecast_end).days
            dur = (node.forecast_end - node.forecast_start).days if node.forecast_start else 0
            late_start[eff_id] = late_finish - timedelta(days=dur)
            resolved[eff_id] = node.model_copy(update={"slack_days": max(0, slack)})

    return [resolved[eid] for eid in topo_order]
