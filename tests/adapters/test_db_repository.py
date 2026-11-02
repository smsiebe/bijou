"""Unit and adversarial concurrency tests for SqlAlchemyGraphRepository."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest

from bijou.adapters.db import SqlAlchemyGraphRepository
from bijou.core.contracts import (
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
    ThingDTO,
)
from bijou.core.ports.exceptions import EntityNotFoundError


@pytest.fixture
def temp_db(tmp_path: Path) -> SqlAlchemyGraphRepository:
    """Fixture providing an isolated file-backed SQLite WAL database repository."""
    db_file = tmp_path / "test_bijou.db"
    repo = SqlAlchemyGraphRepository(f"sqlite:///{db_file}")
    yield repo
    repo.close()


def test_crud_and_manifest_roundtrip_persistence(temp_db: SqlAlchemyGraphRepository) -> None:
    """Inserts all entity types, exports a manifest, wipes DB with replace_all=True, re-imports, and verifies identical state."""
    repo = temp_db

    # 1. Insert entities
    org = OrganizationDTO(
        id="org-1",
        name="Joint Command",
        echelon_level=1,
        mission_statement="Multi-domain superiority",
    )
    repo.upsert_organization(org)

    concern = ConcernDTO(
        id="con-1",
        name="Automated Target Cueing",
        description="Sub-minute sensor to shooter",
        owner_org_id="org-1",
        priority=0.9,
    )
    repo.upsert_concern(concern)

    ms = MilestoneDTO(
        id="ms-1",
        thing_id="th-1",
        sequence_index=0,
        name="Prototype",
        description="Demo",
        target_date=date(2027, 1, 1),
        status=MilestoneStatus.COMMITTED,
        lane="CV Pipeline",
        trl=6,
    )
    thing = ThingDTO(
        id="th-1",
        name="Autonomous CV Target Node",
        description="Edge AI payload",
        lifecycle=LifecycleStatus.ACTIVE,
        owner_org_id="org-1",
        estimated_cost=100000.0,
        risk_factor=2.0,
        milestones=[ms],
    )
    repo.upsert_thing(thing)

    gate = CausalGateDTO(
        id="gate-1",
        name="CV Ingest Gate",
        mechanism=CausalMechanismType.ADDITIVE,
        contributors=[CausalContributorDTO(thing_id="th-1", milestone_id="ms-1", contribution_weight=1.0)],
    )
    repo.upsert_causal_gate(gate)

    effect = EffectDTO(
        id="eff-1",
        name="Target Cueing Delay < 60s",
        description="Real-time cueing",
        tier=EffectTier.TIER_1_STRATEGIC,
        causal_gate_id="gate-1",
        satisfies_concerns=[ConcernSatisfactionLinkDTO(concern_id="con-1", weight=1.0)],
    )
    repo.upsert_effect(effect)

    edge = GraphEdgeDTO(
        id="edge-1",
        source_id="th-1",
        target_id="con-1",
        relationship=RelationshipType.IMPACTS,
    )
    repo.upsert_edge(edge)

    # 2. Export manifest
    manifest = repo.export_manifest()
    assert len(manifest.organizations) == 1
    assert len(manifest.concerns) == 1
    assert len(manifest.things) == 1
    assert len(manifest.causal_gates) == 1
    assert len(manifest.effects) == 1
    assert len(manifest.edges) == 1

    # 3. Wipe database with replace_all=True using empty manifest
    repo.import_manifest(BijouManifestDTO(), replace_all=True)
    assert len(repo.list_organizations()) == 0
    assert len(repo.list_things()) == 0

    # 4. Re-import saved manifest
    counts = repo.import_manifest(manifest, replace_all=True)
    assert counts["organizations"] == 1
    assert counts["things"] == 1

    # 5. Verify restored state
    restored_thing = repo.get_thing("th-1")
    assert restored_thing is not None
    assert restored_thing.name == thing.name
    assert len(restored_thing.milestones) == 1
    assert restored_thing.milestones[0].id == "ms-1"


def test_concurrent_readers_and_writers_no_deadlock(temp_db: SqlAlchemyGraphRepository) -> None:
    """Spawns 16 threads simultaneously reading and upserting ThingDTO records against file-backed SQLite WAL."""
    repo = temp_db

    # Baseline org
    repo.upsert_organization(
        OrganizationDTO(
            id="org-concurrent",
            name="Concurrent Org",
            echelon_level=2,
            mission_statement="Stress test",
        )
    )

    def worker(worker_id: int) -> None:
        thing_id = f"th-worker-{worker_id % 4}"
        ms = MilestoneDTO(
            id=f"ms-{worker_id}",
            thing_id=thing_id,
            sequence_index=0,
            name=f"MS {worker_id}",
            description="Testing",
            target_date=date(2027, 1, 1),
            status=MilestoneStatus.IN_PROGRESS,
            lane="Testing",
            trl=5,
        )
        thing = ThingDTO(
            id=thing_id,
            name=f"Thing {thing_id}",
            description="Concurrent write",
            lifecycle=LifecycleStatus.ACTIVE,
            owner_org_id="org-concurrent",
            estimated_cost=50000.0 * (worker_id + 1),
            risk_factor=1.5,
            milestones=[ms],
        )
        # Write
        repo.upsert_thing(thing)
        # Read
        retrieved = repo.get_thing(thing_id)
        assert retrieved is not None
        # List
        _ = repo.list_things()

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(worker, i) for i in range(32)]
        for f in futures:
            f.result()  # Will raise if any deadlock or exception occurred

    things = repo.list_things()
    assert len(things) == 4


def test_atomic_rollback_on_invalid_manifest_edge(temp_db: SqlAlchemyGraphRepository) -> None:
    """Verifies that importing a manifest with a dangling edge target leaves existing database records untouched."""
    repo = temp_db

    # Create baseline entity
    org = OrganizationDTO(
        id="org-baseline",
        name="Baseline Org",
        echelon_level=1,
        mission_statement="Should survive",
    )
    repo.upsert_organization(org)

    # Manifest with a dangling edge target
    invalid_manifest = BijouManifestDTO(
        organizations=[
            OrganizationDTO(
                id="org-new",
                name="New Org",
                echelon_level=2,
                mission_statement="Should be rolled back",
            )
        ],
        edges=[
            GraphEdgeDTO(
                id="edge-dangling",
                source_id="org-new",
                target_id="non-existent-target-id",
                relationship=RelationshipType.SUPPORTS,
            )
        ],
    )

    with pytest.raises(EntityNotFoundError):
        repo.import_manifest(invalid_manifest, replace_all=False)

    # Verify rollback: org-baseline exists, org-new does NOT exist
    assert repo.get_organization("org-baseline") is not None
    assert repo.get_organization("org-new") is None
