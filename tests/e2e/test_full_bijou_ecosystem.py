"""End-to-End ecosystem workflow verifying full Joint ISR v2 reference dataset."""

from pathlib import Path

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou_ingest import ManifestIngestor
from bijou_sdk import BijouClient


def test_full_v2_ecosystem_scenario(tmp_path: Path) -> None:
    datasets_dir = Path(__file__).resolve().parent.parent.parent / "datasets"
    app = create_app(
        BijouSettings(
            db_uri=f"sqlite:///{tmp_path}/e2e.db",
            duckdb_path=str(tmp_path / "e2e.duckdb"),
            enable_reasoning=False,
        )
    )
    with BijouClient(app=app) as client:
        ing = ManifestIngestor(client)
        ing.ingest_manifest_file("joint_isr_architecture.json", base_dir=datasets_dir, replace_all=True)
        ing.ingest_telemetry_file("satellite_cascade_telemetry.jsonl", base_dir=datasets_dir)

        view_b = client.get_tripartite_flow()
        # Tactical Airborne ISR Wing & IC Cell derive indirect benefits without direct resourcing
        assert len(view_b.indirect_benefits) >= 3
        assert len(view_b.shared_interest_partnerships) >= 1

        # Simulate exercising a mitigator + mismatched RF skill allocation
        sim = client.simulate_bill_of_efforts(
            {
                "toggle_mitigators": {"mit-reserved-scif-block": True},
                "add_allocations": [
                    {
                        "org_id": "org-strat-space",
                        "pool_id": "pool-ml-engineers",
                        "effort_id": "eff-edge-correlator",
                        "requirement_id": "req-edge-rf",
                        "resourcing_type": "STAFF",
                        "amount": 1.0,
                        "unit": "FTE",
                        "assigned_skill": "Edge ML / C++ Engineer",
                        "is_generic": False,
                        "human_slip_penalty_days": 55,
                    }
                ],
            }
        )
        assert len(sim.skill_mismatch_warnings) == 1
        assert sim.skill_mismatch_warnings[0]["suggested_slip_penalty_days"] == 55
        assert len(sim.newly_registered_risks) == 1

        diag = client.validate_manifest()
        assert diag["blockers"] == []
