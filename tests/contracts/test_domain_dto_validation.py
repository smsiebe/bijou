"""Unit tests verifying byte-level JSON/YAML roundtripping and validation bounds."""

import json
from datetime import date, datetime, timezone

import pytest
import yaml
from pydantic import ValidationError

from bijou.core.contracts import (
    AccumulatorPattern,
    BijouManifestDTO,
    CausalContributorDTO,
    CausalGateDTO,
    CausalMechanismType,
    ConcernDTO,
    ConcernSatisfactionLinkDTO,
    EffectDTO,
    EffectTier,
    GraphEdgeDTO,
    LifecycleStatus,
    MilestoneDTO,
    MilestoneStatus,
    OrganizationDTO,
    RelationshipType,
    SlipSimulationRequestDTO,
    ThingDTO,
)


def _build_sample_manifest() -> BijouManifestDTO:
    """Create a fully populated sample manifest for round-trip testing."""
    org = OrganizationDTO(
        id="org-1",
        name="Joint Commands",
        echelon_level=1,
        mission_statement="Sovereign coordination across theaters",
        peer_org_ids=["org-2"],
        tags=["command", "joint"],
    )
    concern = ConcernDTO(
        id="con-1",
        name="Low-Latency Comms",
        description="Deliver sub-50ms tactical comms",
        owner_org_id="org-1",
        priority=0.95,
        target_metric_sla=50.0,
    )
    ms = MilestoneDTO(
        id="ms-1",
        thing_id="th-1",
        sequence_index=0,
        name="Field Test",
        description="TRL 7 Demonstration",
        target_date=date(2027, 6, 30),
        status=MilestoneStatus.IN_PROGRESS,
        cost_delta=15000.0,
        lane="Edge Routing",
        trl=7,
    )
    thing = ThingDTO(
        id="th-1",
        name="AuraGateway Edge Mesh",
        description="Tactical software gateway",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-1",
        estimated_cost=250000.0,
        risk_factor=2.5,
        milestones=[ms],
    )
    gate = CausalGateDTO(
        id="gate-1",
        name="Dual Sensor Ingest Gate",
        mechanism=CausalMechanismType.COMBINATORIAL_AND,
        contributors=[
            CausalContributorDTO(thing_id="th-1", milestone_id="ms-1", contribution_weight=1.0)
        ],
    )
    effect = EffectDTO(
        id="eff-1",
        name="Edge Comms Latency <= 50ms",
        description="Operational capability",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-1",
        accumulator=AccumulatorPattern.SUM,
        target_threshold=50.0,
        satisfies_concerns=[
            ConcernSatisfactionLinkDTO(concern_id="con-1", weight=0.8, confidence=0.95)
        ],
    )
    edge = GraphEdgeDTO(
        id="edge-1",
        source_id="th-1",
        target_id="con-1",
        relationship=RelationshipType.IMPACTS,
        weight=0.9,
    )
    return BijouManifestDTO(
        schema_version="1.0.0",
        exported_at=datetime(2026, 11, 1, 20, 0, 0, tzinfo=timezone.utc),
        organizations=[org],
        concerns=[concern],
        things=[thing],
        causal_gates=[gate],
        effects=[effect],
        edges=[edge],
    )


def test_manifest_byte_level_roundtrip() -> None:
    """Serializes a complete BijouManifestDTO to JSON and YAML and restores an identical object."""
    original = _build_sample_manifest()

    # JSON roundtrip
    json_str = original.model_dump_json(by_alias=True)
    json_data = json.loads(json_str)
    restored_from_json = BijouManifestDTO.model_validate(json_data)
    assert restored_from_json == original

    # YAML roundtrip
    yaml_str = yaml.dump(json_data)
    yaml_data = yaml.safe_load(yaml_str)
    restored_from_yaml = BijouManifestDTO.model_validate(yaml_data)
    assert restored_from_yaml == original


def test_causal_gate_threshold_validation() -> None:
    """Verifies CausalGateDTO with mechanism=THRESHOLD_K_OF_N and threshold_k=None raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        CausalGateDTO(
            id="gate-invalid",
            name="Invalid Threshold Gate",
            mechanism=CausalMechanismType.THRESHOLD_K_OF_N,
            threshold_k=None,
        )
    assert "threshold_k is required" in str(exc_info.value)

    # Valid threshold_k should succeed
    gate = CausalGateDTO(
        id="gate-valid",
        name="Valid Threshold Gate",
        mechanism=CausalMechanismType.THRESHOLD_K_OF_N,
        threshold_k=2,
    )
    assert gate.threshold_k == 2


def test_slip_simulation_rejects_zero_days() -> None:
    """Verifies SlipSimulationRequestDTO(milestone_id='ms-1', slip_days=0) raises ValidationError."""
    with pytest.raises(ValidationError):
        SlipSimulationRequestDTO(milestone_id="ms-1", slip_days=0)

    # Valid slip_days >= 1 succeeds
    valid_req = SlipSimulationRequestDTO(milestone_id="ms-1", slip_days=1)
    assert valid_req.slip_days == 1
