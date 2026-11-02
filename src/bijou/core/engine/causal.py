"""Causal gate evaluation and milestone state resolution engine."""

from datetime import date

from bijou.core.contracts.enums import (
    CausalMechanismType,
    MilestoneStatus,
    TechTreeNodeState,
)
from bijou.core.contracts.models import (
    CausalGateDTO,
    MilestoneDTO,
)


def resolve_milestone_state(
    milestone: MilestoneDTO,
    as_of_date: date,
    upstream_prerequisite_states: list[TechTreeNodeState],
    is_cancelled: bool = False,
) -> TechTreeNodeState:
    """Resolve the effective TechTreeNodeState for a milestone given upstream prerequisites.

    Rules:
    - If cancelled: BLOCKED
    - If status == ACHIEVED and (actual_date or target_date) <= as_of_date: ACHIEVED
    - If any upstream prerequisite is SLIPPED or BLOCKED: BLOCKED
    - If status == IN_PROGRESS and all upstream prerequisites are ACHIEVED: ACTIVE
    - If status in (ESTIMATED, COMMITTED) and all upstream prerequisites are ACHIEVED: UNLOCKED_READY
    - If one or more upstream prerequisites are not yet ACHIEVED: LOCKED
    """
    if is_cancelled:
        return TechTreeNodeState.BLOCKED

    effective_date = milestone.actual_date or milestone.target_date

    if milestone.status == MilestoneStatus.ACHIEVED and effective_date <= as_of_date:
        return TechTreeNodeState.ACHIEVED

    # If any upstream prerequisite is BLOCKED, this node is BLOCKED
    if any(s == TechTreeNodeState.BLOCKED for s in upstream_prerequisite_states):
        return TechTreeNodeState.BLOCKED

    # Check if all upstream prerequisites are ACHIEVED
    all_upstream_achieved = all(s == TechTreeNodeState.ACHIEVED for s in upstream_prerequisite_states)

    if milestone.status == MilestoneStatus.IN_PROGRESS and all_upstream_achieved:
        return TechTreeNodeState.ACTIVE

    if milestone.status in (MilestoneStatus.ESTIMATED, MilestoneStatus.COMMITTED) and all_upstream_achieved:
        return TechTreeNodeState.UNLOCKED_READY

    # If some upstream prerequisites are not ACHIEVED (e.g. LOCKED or ACTIVE)
    return TechTreeNodeState.LOCKED


def evaluate_causal_gate_yield(
    gate: CausalGateDTO,
    milestone_states: dict[str, TechTreeNodeState],
    thing_states: dict[str, str] | None = None,
) -> float:
    """Calculate the operational yield [0.0, 1.0] of a Causal Gate based on contributor states.

    - ADDITIVE: min(1.0, sum of contribution_weight of achieved contributors)
    - COMBINATORIAL_AND: 1.0 iff ALL contributors are ACHIEVED, else 0.0
    - THRESHOLD_K_OF_N: 1.0 iff >= threshold_k contributors are ACHIEVED, else 0.0
    """
    achieved_weights: list[float] = []
    total_contributors = len(gate.contributors)

    if total_contributors == 0:
        return 1.0

    for contrib in gate.contributors:
        is_achieved = False
        if contrib.milestone_id:
            state = milestone_states.get(contrib.milestone_id)
            if state == TechTreeNodeState.ACHIEVED:
                is_achieved = True
        elif thing_states:
            # If contributor only anchors to Thing
            t_status = thing_states.get(contrib.thing_id)
            if t_status in ("ACTIVE", "DELIVERED"):
                is_achieved = True

        if is_achieved:
            achieved_weights.append(contrib.contribution_weight)

    achieved_count = len(achieved_weights)

    if gate.mechanism == CausalMechanismType.ADDITIVE:
        return min(1.0, float(sum(achieved_weights)))

    if gate.mechanism == CausalMechanismType.COMBINATORIAL_AND:
        return 1.0 if achieved_count == total_contributors else 0.0

    if gate.mechanism == CausalMechanismType.THRESHOLD_K_OF_N:
        k = gate.threshold_k or 1
        return 1.0 if achieved_count >= k else 0.0

    return 0.0
