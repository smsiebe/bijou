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
    effective_date: date | None = None,
    effective_target_date: date | None = None,
    is_slipped: bool = False,
    has_schedule_violation: bool = False,
) -> TechTreeNodeState:
    """Resolve the effective TechTreeNodeState for a milestone given upstream prerequisites.

    Rules:
    - If cancelled or schedule violated: BLOCKED
    - If any upstream prerequisite is BLOCKED: BLOCKED
    - If explicitly slipped past as_of_date: BLOCKED if previously ACHIEVED, else LOCKED
    - If status == ACHIEVED and effective_date <= as_of_date: ACHIEVED
    - If any upstream prerequisite is not ACHIEVED: LOCKED
    - If status == IN_PROGRESS and all upstream prerequisites are ACHIEVED: ACTIVE
    - If status in (ESTIMATED, COMMITTED) and all upstream prerequisites are ACHIEVED: UNLOCKED_READY
    - Otherwise: LOCKED
    """
    if is_cancelled or has_schedule_violation:
        return TechTreeNodeState.BLOCKED

    eff_target = effective_target_date or milestone.target_date
    eff_date = effective_date or (milestone.actual_date or milestone.target_date)

    # If any upstream prerequisite is BLOCKED, this node is BLOCKED
    if any(s == TechTreeNodeState.BLOCKED for s in upstream_prerequisite_states):
        return TechTreeNodeState.BLOCKED

    # Slipped milestone whose effective target or actual date exceeds as_of_date
    if is_slipped and (eff_target > as_of_date or eff_date > as_of_date):
        if milestone.status == MilestoneStatus.ACHIEVED:
            return TechTreeNodeState.BLOCKED
        return TechTreeNodeState.LOCKED

    if milestone.status == MilestoneStatus.ACHIEVED and eff_date <= as_of_date:
        return TechTreeNodeState.ACHIEVED

    # Check if all upstream prerequisites are ACHIEVED
    all_upstream_achieved = all(s == TechTreeNodeState.ACHIEVED for s in upstream_prerequisite_states)
    if not all_upstream_achieved:
        return TechTreeNodeState.LOCKED

    if milestone.status == MilestoneStatus.IN_PROGRESS:
        return TechTreeNodeState.ACTIVE

    if milestone.status in (MilestoneStatus.ESTIMATED, MilestoneStatus.COMMITTED):
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
