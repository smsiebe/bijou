"""In-memory thread-safe graph projection, forecasting, and Bill of Efforts simulation engine."""

import threading
from datetime import date

from bijou.core.contracts.enums import (
    AccessMode,
    ConfidenceLevel,
    OrgOrgRelationType,
    ResourceCategory,
    RiskStatus,
)
from bijou.core.contracts.manifest import BijouManifestDTO
from bijou.core.contracts.models import (
    EffortDTO,
    InterestDTO,
    OrgEffortEdgeDTO,
    OrganizationDTO,
    RiskDTO,
)
from bijou.core.contracts.telemetry import TelemetryRollupDTO
from bijou.core.contracts.views import (
    BillOfEffortsSimulationRequestDTO,
    BillOfEffortsSimulationResponseDTO,
    CapabilityTreeViewDTO,
    DiagnosticReportDTO,
    EffortFocalDashboardDTO,
    ForecastedEffortNodeDTO,
    InterestFocalDashboardDTO,
    OrgFocalDashboardDTO,
    PerspectiveBriefingDTO,
    ResourcePoolBalanceDTO,
    SkillMismatchWarningDTO,
    TriPartiteFlowViewDTO,
)
from bijou.core.engine.forecasting import detect_cycles_in_graph, resolve_effort_forecasts
from bijou.core.engine.traversal import (
    compute_dynamic_hierarchy_priorities,
    compute_pool_balances,
    discover_indirect_benefits_and_partnerships,
    evaluate_skill_mismatch,
    get_interest_ancestors,
    get_interest_descendants,
)
from bijou.core.ports.exceptions import EntityNotFoundError
from bijou.core.ports.graph_engine import IGraphProjectionEngine


_CONFIDENCE_RANK = {
    ConfidenceLevel.CONFIRMED: 3,
    ConfidenceLevel.ASSESSED: 2,
    ConfidenceLevel.UNCONFIRMED: 1,
}


def _passes_confidence(conf: ConfidenceLevel, min_confidence: ConfidenceLevel | None) -> bool:
    if min_confidence is None:
        return True
    return _CONFIDENCE_RANK.get(conf, 0) >= _CONFIDENCE_RANK.get(min_confidence, 0)


class InMemoryGraphProjectionEngine(IGraphProjectionEngine):
    """Thread-safe deterministic projection and portfolio analysis engine for Bijou v2."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._manifest = BijouManifestDTO()

    def rebuild_projection(self, manifest: BijouManifestDTO) -> None:
        """Replace in-memory manifest snapshot under exclusive write lock."""
        with self._lock:
            self._manifest = manifest

    def validate_dag_acyclic(self) -> dict[str, list[list[str]]]:
        """Verify Effort and Interest DAGs are acyclic, returning detected cycles by graph."""
        with self._lock:
            effort_cycles = detect_cycles_in_graph(
                [e.id for e in self._manifest.efforts],
                [(ee.source_effort_id, ee.target_effort_id) for ee in self._manifest.effort_effort_edges],
            )
            interest_cycles = detect_cycles_in_graph(
                [i.id for i in self._manifest.interests],
                [(ie.parent_interest_id, ie.child_interest_id) for ie in self._manifest.interest_interest_edges],
            )
            return {
                "effort_cycles": effort_cycles,
                "interest_cycles": interest_cycles,
            }

    def _build_tree_from_manifest(
        self,
        m: BijouManifestDTO,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
        org_filter: str | None = None,
        extra_slips: dict[str, int] | None = None,
        toggle_mitigators: dict[str, bool] | None = None,
        cancelled_effort_ids: set[str] | None = None,
        extra_risks: list[RiskDTO] | None = None,
    ) -> CapabilityTreeViewDTO:
        # Filter typed edges by confidence pedigree threshold
        oo_edges = [e for e in m.org_org_edges if _passes_confidence(e.confidence, min_confidence)]
        oi_edges = [e for e in m.org_interest_edges if _passes_confidence(e.confidence, min_confidence)]
        ii_edges = [e for e in m.interest_interest_edges if _passes_confidence(e.confidence, min_confidence)]
        oe_edges = [e for e in m.org_effort_edges if _passes_confidence(e.confidence, min_confidence)]
        ei_edges = [e for e in m.effort_interest_edges if _passes_confidence(e.confidence, min_confidence)]
        ee_edges = [e for e in m.effort_effort_edges if _passes_confidence(e.confidence, min_confidence)]

        indirect_paths, _ = discover_indirect_benefits_and_partnerships(
            orgs=m.organizations,
            org_interest_edges=oi_edges,
            org_effort_edges=oe_edges,
            effort_interest_edges=ei_edges,
            interest_edges=ii_edges,
            org_org_edges=oo_edges,
        )

        nodes = resolve_effort_forecasts(
            efforts=m.efforts,
            effort_edges=ee_edges,
            org_effort_edges=oe_edges,
            effort_interest_edges=ei_edges,
            indirect_paths=indirect_paths,
            as_of_date=as_of_date,
            extra_slips=extra_slips,
            toggle_mitigators=toggle_mitigators,
            cancelled_effort_ids=cancelled_effort_ids,
            extra_risks=extra_risks,
        )

        if org_filter:
            allowed_effort_ids = {
                n.effort.id
                for n in nodes
                if org_filter in n.funding_org_ids or org_filter in n.indirect_beneficiary_org_ids
            }
            nodes = [n for n in nodes if n.effort.id in allowed_effort_ids]
            ee_edges = [
                ee
                for ee in ee_edges
                if ee.source_effort_id in allowed_effort_ids and ee.target_effort_id in allowed_effort_ids
            ]

        effective_priorities = compute_dynamic_hierarchy_priorities(
            orgs=m.organizations,
            org_org_edges=oo_edges,
            org_interest_edges=oi_edges,
            enable_inheritance=include_hierarchy_priorities,
        )

        return CapabilityTreeViewDTO(
            as_of_date=as_of_date,
            nodes=nodes,
            effort_edges=ee_edges,
            organizations=m.organizations,
            resource_pools=m.resource_pools,
            interests=m.interests,
            org_org_edges=oo_edges,
            org_interest_edges=oi_edges,
            interest_interest_edges=ii_edges,
            org_effort_edges=oe_edges,
            effort_interest_edges=ei_edges,
            effective_priorities=effective_priorities,
        )

    def build_capability_tree_view(
        self,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
        org_filter: str | None = None,
    ) -> CapabilityTreeViewDTO:
        """Construct the stateful capability progression tree projection (View A)."""
        with self._lock:
            return self._build_tree_from_manifest(
                m=self._manifest,
                as_of_date=as_of_date,
                include_hierarchy_priorities=include_hierarchy_priorities,
                min_confidence=min_confidence,
                org_filter=org_filter,
            )

    def build_tripartite_flow_view(
        self,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
        min_confidence: ConfidenceLevel | None = None,
    ) -> TriPartiteFlowViewDTO:
        """Construct the Orgs <-> Efforts <-> Interests Tri-Partite flow projection (View B)."""
        with self._lock:
            tree = self._build_tree_from_manifest(
                m=self._manifest,
                as_of_date=as_of_date,
                include_hierarchy_priorities=include_hierarchy_priorities,
                min_confidence=min_confidence,
            )
            pool_balances = compute_pool_balances(
                pools=tree.resource_pools,
                efforts=self._manifest.efforts,
                org_effort_edges=tree.org_effort_edges,
                effort_interest_edges=tree.effort_interest_edges,
                interest_edges=tree.interest_interest_edges,
            )
            indirect_paths, partnerships = discover_indirect_benefits_and_partnerships(
                orgs=tree.organizations,
                org_interest_edges=tree.org_interest_edges,
                org_effort_edges=tree.org_effort_edges,
                effort_interest_edges=tree.effort_interest_edges,
                interest_edges=tree.interest_interest_edges,
                org_org_edges=tree.org_org_edges,
            )
            return TriPartiteFlowViewDTO(
                as_of_date=as_of_date,
                capability_tree=tree,
                pool_balances=pool_balances,
                indirect_benefits=indirect_paths,
                shared_interest_partnerships=partnerships,
            )

    def simulate_bill_of_efforts(
        self,
        request: BillOfEffortsSimulationRequestDTO,
        as_of_date: date,
    ) -> BillOfEffortsSimulationResponseDTO:
        """Evaluate transient Mitigator toggles, ResourcePool assignments, and slip shocks (View C)."""
        with self._lock:
            base_tree = self._build_tree_from_manifest(self._manifest, as_of_date=as_of_date)
            base_nodes_by_id = {n.effort.id: n for n in base_tree.nodes}

            pools_by_id = {p.id: p for p in self._manifest.resource_pools}
            efforts_by_id = {e.id: e for e in self._manifest.efforts}

            # 1. Construct transient OrgEffortEdges snapshot
            remove_set = set(request.remove_edge_ids)
            sim_org_effort = [
                oe for oe in self._manifest.org_effort_edges if oe.id not in remove_set
            ]

            warnings: list[SkillMismatchWarningDTO] = []
            new_risks: list[RiskDTO] = []
            cost_delta = 0.0

            # Check mitigator resource cost deltas
            for effort in self._manifest.efforts:
                for mit in effort.mitigators:
                    base_ex = mit.is_exercised
                    sim_ex = request.toggle_mitigators.get(mit.id, base_ex)
                    if sim_ex != base_ex:
                        mit_cost = sum(
                            (r.estimated_cost_usd or (r.quantity if r.unit.upper() == "USD" else 0.0))
                            for r in mit.additional_requirements
                        )
                        cost_delta += mit_cost if sim_ex else -mit_cost

            for idx, alloc in enumerate(request.add_allocations):
                target_eff = efforts_by_id.get(alloc.effort_id)
                if not target_eff:
                    continue

                assigned_skill = alloc.assigned_skill
                if assigned_skill is None and alloc.pool_id and alloc.pool_id in pools_by_id:
                    assigned_skill = pools_by_id[alloc.pool_id].skill_tag

                # Check requirement skill matching if requirement specified
                matched_req = None
                if alloc.requirement_id:
                    all_reqs = list(target_eff.resource_requirements)
                    for mit in target_eff.mitigators:
                        all_reqs.extend(mit.additional_requirements)
                    matched_req = next((r for r in all_reqs if r.id == alloc.requirement_id), None)

                warning = evaluate_skill_mismatch(
                    effort_id=alloc.effort_id,
                    assigned_skill=assigned_skill,
                    requirement=matched_req,
                    is_generic=alloc.is_generic,
                    human_slip_penalty_days=alloc.human_slip_penalty_days,
                )
                if warning:
                    warnings.append(warning)
                    new_risks.append(warning.generated_risk)

                if alloc.resourcing_type == ResourceCategory.MONEY or alloc.unit.upper() == "USD":
                    cost_delta += alloc.amount

                sim_org_effort.append(
                    OrgEffortEdgeDTO(
                        id=f"sim-alloc-{idx}",
                        org_id=alloc.org_id,
                        effort_id=alloc.effort_id,
                        resourcing_type=alloc.resourcing_type,
                        resource_pool_id=alloc.pool_id,
                        requirement_id=alloc.requirement_id,
                        allocation_amount=alloc.amount,
                        allocation_unit=alloc.unit,
                        assigned_skill=assigned_skill,
                        is_generic=alloc.is_generic,
                        confidence=ConfidenceLevel.CONFIRMED,
                        provenance_note="Simulated in Bill of Efforts workbench",
                    )
                )

            # Check removed edges monetary reduction
            for oe in self._manifest.org_effort_edges:
                if oe.id in remove_set and (
                    oe.resourcing_type == ResourceCategory.MONEY or oe.allocation_unit.upper() == "USD"
                ):
                    cost_delta -= oe.allocation_amount

            sim_manifest = self._manifest.model_copy(update={"org_effort_edges": sim_org_effort})

            projected_tree = self._build_tree_from_manifest(
                m=sim_manifest,
                as_of_date=as_of_date,
                extra_slips=request.effort_slips,
                toggle_mitigators=request.toggle_mitigators,
                cancelled_effort_ids=set(request.cancelled_effort_ids),
                extra_risks=new_risks,
            )

            pool_balances = compute_pool_balances(
                pools=sim_manifest.resource_pools,
                efforts=sim_manifest.efforts,
                org_effort_edges=sim_org_effort,
                effort_interest_edges=sim_manifest.effort_interest_edges,
                interest_edges=sim_manifest.interest_interest_edges,
            )

            impacted_ids: list[str] = []
            for p_node in projected_tree.nodes:
                b_node = base_nodes_by_id.get(p_node.effort.id)
                if b_node is None:
                    impacted_ids.append(p_node.effort.id)
                    continue
                if (
                    p_node.horizon_status != b_node.horizon_status
                    or p_node.forecast_end != b_node.forecast_end
                    or p_node.relative_offset_days != b_node.relative_offset_days
                    or p_node.resourcing_coverage_ratio != b_node.resourcing_coverage_ratio
                    or p_node.active_risk_count != b_node.active_risk_count
                    or p_node.exercised_mitigator_count != b_node.exercised_mitigator_count
                ):
                    impacted_ids.append(p_node.effort.id)

            # Compute Interest coverage delta across Effort->Interest edges
            base_interest_cov = self._compute_interest_coverage_map(base_tree.nodes, sim_manifest)
            sim_interest_cov = self._compute_interest_coverage_map(projected_tree.nodes, sim_manifest)
            coverage_deltas = {
                iid: round(sim_interest_cov.get(iid, 0.0) - base_interest_cov.get(iid, 0.0), 3)
                for iid in sim_interest_cov
            }

            base_risk_total = sum(n.active_risk_count for n in base_tree.nodes)
            sim_risk_total = sum(n.active_risk_count for n in projected_tree.nodes)

            return BillOfEffortsSimulationResponseDTO(
                projected_tree=projected_tree,
                pool_balances=pool_balances,
                skill_mismatch_warnings=warnings,
                newly_registered_risks=new_risks,
                impacted_effort_ids=impacted_ids,
                interest_coverage_deltas=coverage_deltas,
                total_cost_delta=round(cost_delta, 2),
                net_risk_count_delta=sim_risk_total - base_risk_total,
            )

    def _compute_interest_coverage_map(
        self,
        nodes: list[ForecastedEffortNodeDTO],
        manifest: BijouManifestDTO,
    ) -> dict[str, float]:
        node_map = {n.effort.id: n for n in nodes}
        scores: dict[str, list[float]] = {i.id: [] for i in manifest.interests}
        for ei in manifest.effort_interest_edges:
            if ei.interest_id in scores and ei.effort_id in node_map:
                n = node_map[ei.effort_id]
                # Active/Completed efforts with good resource coverage contribute positively
                health = max(0.1, n.resourcing_coverage_ratio) * ei.impact_weight
                if n.effort.state.value == "CANCELLED":
                    health = 0.0
                scores[ei.interest_id].append(health)
        return {
            iid: round(min(1.0, sum(vals) / len(vals)), 3) if vals else 0.0
            for iid, vals in scores.items()
        }

    def build_effort_focal_dashboard(
        self,
        effort_id: str,
        as_of_date: date,
        telemetry_rollups: list[TelemetryRollupDTO],
    ) -> EffortFocalDashboardDTO:
        """Generate a deep focal dashboard for a single Effort."""
        with self._lock:
            tree = self._build_tree_from_manifest(self._manifest, as_of_date=as_of_date)
            node_map = {n.effort.id: n for n in tree.nodes}
            target_node = node_map.get(effort_id)
            if target_node is None:
                raise EntityNotFoundError(f"Effort '{effort_id}' not found")

            efforts_by_id = {e.id: e for e in self._manifest.efforts}
            interests_by_id = {i.id: i for i in self._manifest.interests}

            upstream_ids = {
                ee.source_effort_id
                for ee in self._manifest.effort_effort_edges
                if ee.target_effort_id == effort_id
            }
            downstream_ids = {
                ee.target_effort_id
                for ee in self._manifest.effort_effort_edges
                if ee.source_effort_id == effort_id
            }

            upstream_efforts = [efforts_by_id[uid] for uid in upstream_ids if uid in efforts_by_id]
            downstream_efforts = [efforts_by_id[did] for did in downstream_ids if did in efforts_by_id]
            resourcing_edges = [oe for oe in self._manifest.org_effort_edges if oe.effort_id == effort_id]

            direct_interest_ids = [
                ei.interest_id for ei in self._manifest.effort_interest_edges if ei.effort_id == effort_id
            ]
            aligned_interests = [interests_by_id[iid] for iid in direct_interest_ids if iid in interests_by_id]

            ancestor_ids: set[str] = set()
            for iid in direct_interest_ids:
                ancestor_ids |= get_interest_ancestors(iid, self._manifest.interest_interest_edges)
            ancestor_only_ids = ancestor_ids - set(direct_interest_ids)
            ancestor_interests = [interests_by_id[aid] for aid in ancestor_only_ids if aid in interests_by_id]

            indirect_paths, _ = discover_indirect_benefits_and_partnerships(
                orgs=self._manifest.organizations,
                org_interest_edges=self._manifest.org_interest_edges,
                org_effort_edges=self._manifest.org_effort_edges,
                effort_interest_edges=self._manifest.effort_interest_edges,
                interest_edges=self._manifest.interest_interest_edges,
                org_org_edges=self._manifest.org_org_edges,
            )
            eff_indirect = [p for p in indirect_paths if p.effort_id == effort_id]

            return EffortFocalDashboardDTO(
                forecast=target_node,
                upstream_dependencies=upstream_efforts,
                downstream_dependents=downstream_efforts,
                resourcing_edges=resourcing_edges,
                aligned_interests=aligned_interests,
                ancestor_interest_categories=ancestor_interests,
                indirect_beneficiaries=eff_indirect,
                telemetry_rollups=telemetry_rollups,
            )

    def build_org_focal_dashboard(
        self,
        org_id: str,
        as_of_date: date,
        include_hierarchy_priorities: bool = True,
    ) -> OrgFocalDashboardDTO:
        """Generate a deep focal dashboard for an Organization."""
        with self._lock:
            org = next((o for o in self._manifest.organizations if o.id == org_id), None)
            if org is None:
                raise EntityNotFoundError(f"Organization '{org_id}' not found")

            tree = self._build_tree_from_manifest(
                self._manifest,
                as_of_date=as_of_date,
                include_hierarchy_priorities=include_hierarchy_priorities,
            )
            org_pools = [p for p in self._manifest.resource_pools if p.org_id == org_id]
            pool_balances = compute_pool_balances(
                pools=org_pools,
                efforts=self._manifest.efforts,
                org_effort_edges=self._manifest.org_effort_edges,
                effort_interest_edges=self._manifest.effort_interest_edges,
                interest_edges=self._manifest.interest_interest_edges,
            )

            direct_efforts = [n for n in tree.nodes if org_id in n.funding_org_ids]
            indirect_paths, partnerships = discover_indirect_benefits_and_partnerships(
                orgs=self._manifest.organizations,
                org_interest_edges=self._manifest.org_interest_edges,
                org_effort_edges=self._manifest.org_effort_edges,
                effort_interest_edges=self._manifest.effort_interest_edges,
                interest_edges=self._manifest.interest_interest_edges,
                org_org_edges=self._manifest.org_org_edges,
            )
            org_indirect = [p for p in indirect_paths if p.beneficiary_org_id == org_id]
            org_partnerships = [p for p in partnerships if p.org_a_id == org_id or p.org_b_id == org_id]
            org_prios = [ep for ep in tree.effective_priorities if ep.org_id == org_id]
            org_rels = [
                oo
                for oo in self._manifest.org_org_edges
                if oo.source_org_id == org_id or oo.target_org_id == org_id
            ]

            return OrgFocalDashboardDTO(
                organization=org,
                pool_balances=pool_balances,
                direct_funded_efforts=direct_efforts,
                indirect_benefit_paths=org_indirect,
                org_interest_priorities=org_prios,
                org_relationships=org_rels,
                potential_partnerships=org_partnerships,
            )

    def build_interest_focal_dashboard(
        self,
        interest_id: str,
        as_of_date: date,
    ) -> InterestFocalDashboardDTO:
        """Generate a deep focal dashboard for an Interest and its taxonomy lineage."""
        with self._lock:
            interest = next((i for i in self._manifest.interests if i.id == interest_id), None)
            if interest is None:
                raise EntityNotFoundError(f"Interest '{interest_id}' not found")

            interests_by_id = {i.id: i for i in self._manifest.interests}
            anc_ids = get_interest_ancestors(interest_id, self._manifest.interest_interest_edges) - {interest_id}
            desc_ids = get_interest_descendants(interest_id, self._manifest.interest_interest_edges) - {interest_id}
            lineage_ids = {interest_id} | desc_ids

            ancestors = [interests_by_id[aid] for aid in anc_ids if aid in interests_by_id]
            descendants = [interests_by_id[did] for did in desc_ids if did in interests_by_id]

            all_balances = compute_pool_balances(
                pools=self._manifest.resource_pools,
                efforts=self._manifest.efforts,
                org_effort_edges=self._manifest.org_effort_edges,
                effort_interest_edges=self._manifest.effort_interest_edges,
                interest_edges=self._manifest.interest_interest_edges,
            )
            eligible_pools = [
                pb for pb in all_balances if interest_id in pb.eligible_interest_ids
            ]

            tree = self._build_tree_from_manifest(self._manifest, as_of_date=as_of_date)
            aligned_effort_ids = {
                ei.effort_id for ei in self._manifest.effort_interest_edges if ei.interest_id in lineage_ids
            }
            aligned_efforts = [n for n in tree.nodes if n.effort.id in aligned_effort_ids]
            stances = [oi for oi in self._manifest.org_interest_edges if oi.interest_id == interest_id]

            return InterestFocalDashboardDTO(
                interest=interest,
                ancestor_interests=ancestors,
                descendant_interests=descendants,
                eligible_resource_pools=eligible_pools,
                aligned_efforts=aligned_efforts,
                stakeholder_stances=stances,
            )

    def build_perspective_briefing(
        self,
        subject_org_id: str,
        active_access_mode: AccessMode,
        include_hierarchy_inheritance: bool,
        as_of_date: date,
    ) -> PerspectiveBriefingDTO:
        """Assemble an executive Multi-Perspective 1-Slide Briefing projection."""
        with self._lock:
            org_dash = self.build_org_focal_dashboard(
                org_id=subject_org_id,
                as_of_date=as_of_date,
                include_hierarchy_priorities=include_hierarchy_inheritance,
            )

            total_usd = sum(
                oe.allocation_amount
                for oe in self._manifest.org_effort_edges
                if oe.org_id == subject_org_id
                and (oe.resourcing_type == ResourceCategory.MONEY or oe.allocation_unit.upper() == "USD")
            )

            active_risks: list[RiskDTO] = []
            for node in org_dash.direct_funded_efforts:
                for risk in node.effort.risks:
                    if risk.status == RiskStatus.ACTIVE:
                        active_risks.append(risk)

            return PerspectiveBriefingDTO(
                subject_org_id=subject_org_id,
                active_access_mode=active_access_mode,
                include_hierarchy_inheritance=include_hierarchy_inheritance,
                as_of_date=as_of_date,
                directly_resourced_efforts=org_dash.direct_funded_efforts,
                indirect_benefits=org_dash.indirect_benefit_paths,
                priority_interests=org_dash.org_interest_priorities,
                pool_balances=org_dash.pool_balances,
                active_risks=active_risks,
                partnership_opportunities=org_dash.potential_partnerships,
                total_allocated_usd=round(total_usd, 2),
                executive_summary_narrative=None,
                strategic_gaps=[],
            )

    def validate_manifest_diagnostics(
        self,
        manifest: BijouManifestDTO | None = None,
    ) -> DiagnosticReportDTO:
        """Perform topological, Color-of-Money, pool balance, and skill risk diagnostics."""
        with self._lock:
            m = manifest if manifest is not None else self._manifest
            blockers: list[str] = []
            warnings: list[str] = []

            effort_cycles = detect_cycles_in_graph(
                [e.id for e in m.efforts],
                [(ee.source_effort_id, ee.target_effort_id) for ee in m.effort_effort_edges],
            )
            interest_cycles = detect_cycles_in_graph(
                [i.id for i in m.interests],
                [(ie.parent_interest_id, ie.child_interest_id) for ie in m.interest_interest_edges],
            )
            for cyc in effort_cycles:
                blockers.append(f"Effort dependency cycle: {' -> '.join(cyc)}")
            for cyc in interest_cycles:
                blockers.append(f"Interest taxonomy cycle: {' -> '.join(cyc)}")

            pool_balances = compute_pool_balances(
                pools=m.resource_pools,
                efforts=m.efforts,
                org_effort_edges=m.org_effort_edges,
                effort_interest_edges=m.effort_interest_edges,
                interest_edges=m.interest_interest_edges,
            )

            color_violations: list[str] = []
            overallocated: list[str] = []
            for pb in pool_balances:
                color_violations.extend(pb.color_of_money_violations)
                blockers.extend(pb.color_of_money_violations)
                if pb.remaining_amount < 0:
                    msg = f"Pool '{pb.pool.name}' over-allocated by {abs(pb.remaining_amount)} {pb.pool.unit}"
                    overallocated.append(msg)
                    blockers.append(msg)

            skill_risks: list[str] = []
            efforts_by_id = {e.id: e for e in m.efforts}
            for effort in m.efforts:
                reqs_by_id = {r.id: r for r in effort.resource_requirements}
                for oe in m.org_effort_edges:
                    if oe.effort_id == effort.id and oe.requirement_id in reqs_by_id:
                        w = evaluate_skill_mismatch(
                            effort_id=effort.id,
                            assigned_skill=oe.assigned_skill,
                            requirement=reqs_by_id[oe.requirement_id],
                            is_generic=oe.is_generic,
                        )
                        if w:
                            skill_risks.append(w.message)
                            warnings.append(w.message)

                if effort.state.value in ("IN_WORK", "BACKLOGGED", "PLANNED") and not effort.risks:
                    # Benign informational note if unresourced
                    pass

            # Check orphan references
            org_ids = {o.id for o in m.organizations}
            interest_ids = {i.id for i in m.interests}
            for oi in m.org_interest_edges:
                if oi.org_id not in org_ids or oi.interest_id not in interest_ids:
                    blockers.append(f"Broken OrgInterestEdge '{oi.id}' reference")
            for ee in m.effort_effort_edges:
                if ee.source_effort_id not in efforts_by_id or ee.target_effort_id not in efforts_by_id:
                    blockers.append(f"Broken EffortEffortEdge '{ee.id}' reference")

            return DiagnosticReportDTO(
                blockers=blockers,
                warnings=warnings,
                effort_cycles=effort_cycles,
                interest_cycles=interest_cycles,
                color_of_money_violations=color_violations,
                overallocated_pools=overallocated,
                skill_mismatch_risks=skill_risks,
            )
