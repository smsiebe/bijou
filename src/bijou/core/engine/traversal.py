"""Graph traversal utilities for Interest DAGs, Color-of-Money, Partnerships, and Skill Checks."""

import uuid
from collections import deque

from bijou.core.contracts.enums import (
    ConfidenceLevel,
    OrgOrgRelationType,
    RiskSeverity,
    RiskStatus,
)
from bijou.core.contracts.models import (
    EffortDTO,
    EffortInterestEdgeDTO,
    InterestInterestEdgeDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
)
from bijou.core.contracts.views import (
    DynamicOrgInterestPriorityDTO,
    IndirectBenefitPathDTO,
    ResourcePoolBalanceDTO,
    SharedInterestPartnershipDTO,
    SkillMismatchWarningDTO,
)


def get_interest_descendants(
    interest_id: str,
    interest_edges: list[InterestInterestEdgeDTO],
) -> set[str]:
    """Return interest_id plus all descendant child Interest IDs in the Interest DAG."""
    children_map: dict[str, list[str]] = {}
    for edge in interest_edges:
        children_map.setdefault(edge.parent_interest_id, []).append(edge.child_interest_id)

    visited: set[str] = {interest_id}
    queue: deque[str] = deque([interest_id])
    while queue:
        curr = queue.popleft()
        for child in children_map.get(curr, []):
            if child not in visited:
                visited.add(child)
                queue.append(child)
    return visited


def get_interest_ancestors(
    interest_id: str,
    interest_edges: list[InterestInterestEdgeDTO],
) -> set[str]:
    """Return interest_id plus all ancestor parent Interest IDs in the Interest DAG."""
    parents_map: dict[str, list[str]] = {}
    for edge in interest_edges:
        parents_map.setdefault(edge.child_interest_id, []).append(edge.parent_interest_id)

    visited: set[str] = {interest_id}
    queue: deque[str] = deque([interest_id])
    while queue:
        curr = queue.popleft()
        for parent in parents_map.get(curr, []):
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)
    return visited


def compute_pool_balances(
    pools: list[ResourcePoolDTO],
    efforts: list[EffortDTO],
    org_effort_edges: list[OrgEffortEdgeDTO],
    effort_interest_edges: list[EffortInterestEdgeDTO],
    interest_edges: list[InterestInterestEdgeDTO],
) -> list[ResourcePoolBalanceDTO]:
    """Evaluate pool allocations, remaining capacity, and Color-of-Money Interest eligibility."""
    effort_names = {e.id: e.name for e in efforts}
    effort_interests: dict[str, set[str]] = {}
    for ei in effort_interest_edges:
        effort_interests.setdefault(ei.effort_id, set()).add(ei.interest_id)

    balances: list[ResourcePoolBalanceDTO] = []
    for pool in pools:
        # Color of money: eligible if effort serves any restricted interest OR any descendant sub-interest
        eligible: set[str] = set()
        for root_interest_id in pool.restricted_interest_ids:
            eligible |= get_interest_descendants(root_interest_id, interest_edges)

        allocated = 0.0
        violations: list[str] = []
        for oe in org_effort_edges:
            if oe.resource_pool_id == pool.id:
                allocated += oe.allocation_amount
                if pool.restricted_interest_ids:
                    served = effort_interests.get(oe.effort_id, set())
                    if not (served & eligible):
                        eff_label = effort_names.get(oe.effort_id, oe.effort_id)
                        violations.append(
                            f"Pool '{pool.name}' earmarked for {pool.restricted_interest_ids} "
                            f"cannot fund Effort '{eff_label}' (serves {sorted(served) or 'none'})"
                        )

        balances.append(
            ResourcePoolBalanceDTO(
                pool=pool,
                allocated_amount=allocated,
                remaining_amount=pool.capacity - allocated,
                eligible_interest_ids=sorted(eligible),
                color_of_money_violations=violations,
            )
        )
    return balances


def evaluate_skill_mismatch(
    effort_id: str,
    assigned_skill: str | None,
    requirement: ResourceRequirementDTO | None,
    is_generic: bool = False,
    human_slip_penalty_days: int | None = None,
) -> SkillMismatchWarningDTO | None:
    """Detect non-transferable skill mismatch and emit an automated Risk with operator-settable penalty."""
    if is_generic or requirement is None:
        return None
    if not requirement.required_skill or not assigned_skill:
        return None

    req_norm = requirement.required_skill.strip().lower()
    asg_norm = assigned_skill.strip().lower()
    if req_norm == asg_norm:
        return None

    suggested_days = human_slip_penalty_days if human_slip_penalty_days is not None else 30
    risk = RiskDTO(
        id=f"risk-mismatch-{uuid.uuid4().hex[:6]}",
        effort_id=effort_id,
        title=f"Skill Mismatch: {assigned_skill} assigned to {requirement.required_skill}",
        description=(
            f"Non-transferable skill mismatch on requirement '{requirement.label}'. "
            f"Expected '{requirement.required_skill}', received '{assigned_skill}'."
        ),
        severity=RiskSeverity.HIGH if suggested_days >= 21 else RiskSeverity.MEDIUM,
        likelihood=0.75,
        potential_slip_days=suggested_days,
        is_skill_mismatch_risk=True,
        status=RiskStatus.ACTIVE,
        related_requirement_id=requirement.id,
    )

    return SkillMismatchWarningDTO(
        effort_id=effort_id,
        requirement_id=requirement.id,
        required_skill=requirement.required_skill,
        assigned_skill=assigned_skill,
        message=(
            f"Skill mismatch warning: assigned '{assigned_skill}' does not match required "
            f"'{requirement.required_skill}' on '{requirement.label}'. Risk registered."
        ),
        suggested_slip_penalty_days=suggested_days,
        generated_risk=risk,
    )


def discover_indirect_benefits_and_partnerships(
    orgs: list[OrganizationDTO],
    org_interest_edges: list[OrgInterestEdgeDTO],
    org_effort_edges: list[OrgEffortEdgeDTO],
    effort_interest_edges: list[EffortInterestEdgeDTO],
    interest_edges: list[InterestInterestEdgeDTO],
    org_org_edges: list[OrgOrgEdgeDTO],
) -> tuple[list[IndirectBenefitPathDTO], list[SharedInterestPartnershipDTO]]:
    """Compute indirect benefits (Org -> Interest <- Effort <- Resourcing Org) and partnerships."""
    # Direct Org -> Effort map
    direct_org_efforts: dict[str, set[str]] = {}
    effort_resourcing_orgs: dict[str, set[str]] = {}
    for oe in org_effort_edges:
        direct_org_efforts.setdefault(oe.org_id, set()).add(oe.effort_id)
        effort_resourcing_orgs.setdefault(oe.effort_id, set()).add(oe.org_id)

    # Expand Org interests (including ancestors/descendants for shared alignment)
    org_direct_interests: dict[str, dict[str, float]] = {}
    for oi in org_interest_edges:
        org_direct_interests.setdefault(oi.org_id, {})[oi.interest_id] = oi.priority_rank

    effort_interest_map: dict[str, list[EffortInterestEdgeDTO]] = {}
    for ei in effort_interest_edges:
        effort_interest_map.setdefault(ei.effort_id, []).append(ei)

    indirect_paths: list[IndirectBenefitPathDTO] = []
    seen_path_keys: set[tuple[str, str, str]] = set()

    for oi in org_interest_edges:
        # Org has stake in oi.interest_id (and accepts efforts addressing descendants of oi.interest_id)
        relevant_interests = get_interest_descendants(oi.interest_id, interest_edges)
        for eff_id, ei_list in effort_interest_map.items():
            # Indirect means this org is NOT directly resourcing eff_id
            if eff_id in direct_org_efforts.get(oi.org_id, set()):
                continue
            funders = sorted(effort_resourcing_orgs.get(eff_id, set()))
            if not funders:
                continue
            for ei in ei_list:
                if ei.interest_id in relevant_interests:
                    key = (oi.org_id, ei.interest_id, eff_id)
                    if key not in seen_path_keys:
                        seen_path_keys.add(key)
                        combined_conf = (
                            ConfidenceLevel.UNCONFIRMED
                            if ConfidenceLevel.UNCONFIRMED in (oi.confidence, ei.confidence)
                            else ConfidenceLevel.ASSESSED
                            if ConfidenceLevel.ASSESSED in (oi.confidence, ei.confidence)
                            else ConfidenceLevel.CONFIRMED
                        )
                        indirect_paths.append(
                            IndirectBenefitPathDTO(
                                beneficiary_org_id=oi.org_id,
                                via_interest_id=ei.interest_id,
                                effort_id=eff_id,
                                resourcing_org_ids=funders,
                                confidence=combined_conf,
                            )
                        )

    # Potential & Active Shared-Interest Partnerships
    existing_org_links: set[tuple[str, str]] = set()
    for oo in org_org_edges:
        existing_org_links.add((oo.source_org_id, oo.target_org_id))
        existing_org_links.add((oo.target_org_id, oo.source_org_id))

    org_expanded_interests: dict[str, dict[str, float]] = {}
    for oid, direct_map in org_direct_interests.items():
        expanded: dict[str, float] = {}
        for iid, prio in direct_map.items():
            for desc_iid in get_interest_descendants(iid, interest_edges):
                expanded[desc_iid] = max(expanded.get(desc_iid, 0.0), prio)
        org_expanded_interests[oid] = expanded

    partnerships: list[SharedInterestPartnershipDTO] = []
    org_ids = [o.id for o in orgs]
    for i in range(len(org_ids)):
        for j in range(i + 1, len(org_ids)):
            oa = org_ids[i]
            ob = org_ids[j]
            map_a = org_expanded_interests.get(oa, {})
            map_b = org_expanded_interests.get(ob, {})
            shared = sorted(set(map_a.keys()) & set(map_b.keys()))
            if shared:
                combined_score = sum((map_a[iid] + map_b[iid]) / 2.0 for iid in shared) / len(shared)
                partnerships.append(
                    SharedInterestPartnershipDTO(
                        org_a_id=oa,
                        org_b_id=ob,
                        shared_interest_ids=shared,
                        has_existing_org_link=(oa, ob) in existing_org_links,
                        combined_priority_score=round(combined_score, 3),
                    )
                )

    partnerships.sort(key=lambda p: (-len(p.shared_interest_ids), -p.combined_priority_score))
    return indirect_paths, partnerships


def compute_dynamic_hierarchy_priorities(
    orgs: list[OrganizationDTO],
    org_org_edges: list[OrgOrgEdgeDTO],
    org_interest_edges: list[OrgInterestEdgeDTO],
    enable_inheritance: bool = True,
) -> list[DynamicOrgInterestPriorityDTO]:
    """Compute effective Org-Interest priorities dynamically without mutating raw links."""
    children_map: dict[str, list[str]] = {}
    for oo in org_org_edges:
        if oo.relation_type == OrgOrgRelationType.HIERARCHICAL_PARENT:
            children_map.setdefault(oo.source_org_id, []).append(oo.target_org_id)

    direct_map: dict[tuple[str, str], OrgInterestEdgeDTO] = {}
    all_interests: set[str] = set()
    for oi in org_interest_edges:
        direct_map[(oi.org_id, oi.interest_id)] = oi
        all_interests.add(oi.interest_id)

    effective: dict[tuple[str, str], DynamicOrgInterestPriorityDTO] = {}

    for (oid, iid), oi in direct_map.items():
        effective[(oid, iid)] = DynamicOrgInterestPriorityDTO(
            org_id=oid,
            interest_id=iid,
            direct_priority=oi.priority_rank,
            effective_priority=oi.priority_rank,
            inherited_from_org_id=None,
        )

    if enable_inheritance:
        # Propagate inheritable parent priorities BFS downward with slight decay or max
        for (parent_oid, iid), oi in direct_map.items():
            if not oi.allow_hierarchy_inheritance:
                continue
            queue: deque[tuple[str, float, str]] = deque([(parent_oid, oi.priority_rank, parent_oid)])
            visited: set[str] = {parent_oid}
            while queue:
                curr_oid, curr_prio, root_origin = queue.popleft()
                for child_oid in children_map.get(curr_oid, []):
                    if child_oid in visited:
                        continue
                    visited.add(child_oid)
                    inherited_prio = round(curr_prio * 0.9, 3)
                    existing = effective.get((child_oid, iid))
                    if existing is None or inherited_prio > existing.effective_priority:
                        effective[(child_oid, iid)] = DynamicOrgInterestPriorityDTO(
                            org_id=child_oid,
                            interest_id=iid,
                            direct_priority=existing.direct_priority if existing else None,
                            effective_priority=inherited_prio,
                            inherited_from_org_id=root_origin,
                        )
                    queue.append((child_oid, inherited_prio, root_origin))

    return sorted(effective.values(), key=lambda item: (item.org_id, -item.effective_priority))
