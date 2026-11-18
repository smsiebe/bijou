"""Integration tests for Bijou v2 Offline Snapshot generation, desktop bridge export, and JS runtime parity."""

import base64
import io
import json
import re
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from bijou.adapters.db import SqlAlchemyGraphRepository
from bijou.adapters.telemetry import DuckDbTelemetryStore
from bijou.api.app import app
from bijou.api.deps import set_orchestrator
from bijou.cli import main
from bijou.core.contracts import (
    BillOfEffortsSimulationRequestDTO,
    BlockingMode,
    ConfidenceLevel,
    EffortDTO,
    EffortEffortEdgeDTO,
    EffortInterestEdgeDTO,
    InterestDTO,
    MitigatorDTO,
    OrganizationDTO,
    OrgEffortEdgeDTO,
    OrgInterestEdgeDTO,
    OrgOrgEdgeDTO,
    OrgOrgRelationType,
    ResourceCategory,
    ResourcePoolDTO,
    ResourceRequirementDTO,
    RiskDTO,
    RiskSeverity,
    SimulatedPoolAllocationDTO,
)
from bijou.core.engine import InMemoryGraphProjectionEngine
from bijou.services import BijouOrchestrationService
from bijou.services.snapshot import (
    build_snapshot_data,
    build_snapshot_zip_bytes,
    export_snapshot_to_file,
)
from bijou.web import BijouDesktopBridge


def _create_seeded_orchestrator(tmp_path: Path) -> BijouOrchestrationService:
    repo = SqlAlchemyGraphRepository(db_uri=f"sqlite:///{tmp_path}/test_snapshot.db")
    telemetry_store = DuckDbTelemetryStore(db_path=str(tmp_path / "test_snapshot.duckdb"))
    projection_engine = InMemoryGraphProjectionEngine()
    svc = BijouOrchestrationService(
        repository=repo,
        projection_engine=projection_engine,
        telemetry_store=telemetry_store,
        reasoning_broker=None,
    )
    svc.initialize()

    # Seed hierarchy + partner organizations
    svc.upsert_organization(OrganizationDTO(id="org-parent", name="Parent Command", is_managed=True, echelon_level=0))
    svc.upsert_organization(OrganizationDTO(id="org-alpha", name="Alpha Command", is_managed=True, echelon_level=1))
    svc.upsert_organization(OrganizationDTO(id="org-bravo", name="Bravo Partner", is_managed=False, echelon_level=1))

    svc.upsert_org_org_edge(
        OrgOrgEdgeDTO(
            id="oo-parent",
            source_org_id="org-parent",
            target_org_id="org-alpha",
            relation_type=OrgOrgRelationType.HIERARCHICAL_PARENT,
            confidence=ConfidenceLevel.CONFIRMED,
        )
    )

    svc.upsert_resource_pool(
        ResourcePoolDTO(
            id="pool-money",
            org_id="org-alpha",
            name="FY27 Resiliency Capital",
            category=ResourceCategory.MONEY,
            capacity=1_000_000.0,
            unit="USD",
            restricted_interest_ids=["intr-cyber"],
        )
    )
    svc.upsert_resource_pool(
        ResourcePoolDTO(
            id="pool-staff",
            org_id="org-alpha",
            name="Generalist Engineering Pool",
            category=ResourceCategory.STAFF,
            capacity=5.0,
            unit="FTE",
            skill_tag="Junior Generalist",
        )
    )

    svc.upsert_interest(InterestDTO(id="intr-cyber", name="Cyber Resiliency"))
    svc.upsert_interest(InterestDTO(id="intr-other", name="Unrelated Fleet Logistics"))

    svc.upsert_org_interest_edge(
        OrgInterestEdgeDTO(
            id="oi-parent-cyber",
            org_id="org-parent",
            interest_id="intr-cyber",
            priority_rank=0.9,
            allow_hierarchy_inheritance=True,
            confidence=ConfidenceLevel.CONFIRMED,
        )
    )
    svc.upsert_org_interest_edge(
        OrgInterestEdgeDTO(
            id="oi-alpha-other",
            org_id="org-alpha",
            interest_id="intr-other",
            priority_rank=0.5,
            confidence=ConfidenceLevel.UNCONFIRMED,
        )
    )

    svc.upsert_effort(
        EffortDTO(
            id="eff-quantum",
            name="Post-Quantum Key Exchange",
            description="Test description with </script><script>alert(1)</script> literal.",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 1),
            resource_requirements=[
                ResourceRequirementDTO(
                    id="req-1",
                    label="Quantum Crypto Lead",
                    category=ResourceCategory.STAFF,
                    quantity=1.0,
                    unit="FTE",
                    required_skill="Post-Quantum Crypto",
                )
            ],
            risks=[
                RiskDTO(
                    id="risk-key",
                    effort_id="eff-quantum",
                    title="Algorithm Standardization Delay",
                    severity=RiskSeverity.MEDIUM,
                    potential_slip_days=20,
                )
            ],
            mitigators=[
                MitigatorDTO(
                    id="mit-accel",
                    effort_id="eff-quantum",
                    risk_id="risk-key",
                    name="Dedicated Formal Verification Surge",
                    slip_reduction_days=20,
                    is_exercised=False,
                    additional_requirements=[
                        ResourceRequirementDTO(
                            id="req-mit-usd",
                            label="External Audit Surge",
                            category=ResourceCategory.MONEY,
                            quantity=50_000.0,
                            unit="USD",
                            estimated_cost_usd=50_000.0,
                        )
                    ],
                )
            ],
        )
    )

    svc.upsert_effort(
        EffortDTO(
            id="eff-downstream",
            name="Zero-Trust Fleet Rollout",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 10, 1),
        )
    )

    svc.upsert_org_effort_edge(
        OrgEffortEdgeDTO(
            id="oe-alpha-quantum",
            org_id="org-alpha",
            effort_id="eff-quantum",
            resourcing_type=ResourceCategory.MONEY,
            resource_pool_id="pool-money",
            allocation_amount=250_000.0,
            allocation_unit="USD",
            confidence=ConfidenceLevel.CONFIRMED,
        )
    )
    svc.upsert_effort_interest_edge(
        EffortInterestEdgeDTO(
            id="ei-quantum-cyber",
            effort_id="eff-quantum",
            interest_id="intr-cyber",
            confidence=ConfidenceLevel.CONFIRMED,
        )
    )
    svc.upsert_effort_interest_edge(
        EffortInterestEdgeDTO(
            id="ei-downstream-other",
            effort_id="eff-downstream",
            interest_id="intr-other",
            confidence=ConfidenceLevel.UNCONFIRMED,
        )
    )
    svc.upsert_effort_effort_edge(
        EffortEffortEdgeDTO(
            id="ee-block",
            source_effort_id="eff-quantum",
            target_effort_id="eff-downstream",
            blocking_mode=BlockingMode.BLOCKING,
            confidence=ConfidenceLevel.CONFIRMED,
        )
    )

    return svc


def test_build_snapshot_data(tmp_path: Path) -> None:
    """Verifies that build_snapshot_data aggregates complete portfolio state, views, tools, and briefings."""
    svc = _create_seeded_orchestrator(tmp_path)
    data = build_snapshot_data(svc, as_of_date=date(2026, 5, 1))

    assert data["meta"]["version"] == "2.0.2"
    assert data["meta"]["read_only"] is True
    assert data["meta"]["as_of_date"] == "2026-05-01"

    assert data["health"]["status"] == "healthy"
    assert data["health"]["engine"] == "bijou-v2-snapshot"

    assert len(data["organizations"]) == 3
    assert len(data["resource_pools"]) == 2
    assert len(data["interests"]) == 2
    assert len(data["efforts"]) == 2
    assert len(data["tools"]) >= 4

    assert len(data["views"]["capability_tree"]["nodes"]) == 2
    assert "eff-quantum" in data["focal"]["efforts"]
    assert "org-alpha" in data["focal"]["organizations"]
    assert "org-alpha" in data["briefings"]["organizations"]
    assert "eff-quantum" in data["briefings"]["efforts"]


def test_build_snapshot_zip_file_export_and_script_escaping(tmp_path: Path) -> None:
    """Verifies snapshot ZIP structure, relative paths, script tag escaping, and disk export."""
    svc = _create_seeded_orchestrator(tmp_path)

    zip_bytes = build_snapshot_zip_bytes(svc, as_of_date=date(2026, 5, 1))
    assert len(zip_bytes) > 1000

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = set(zf.namelist())
        assert {
            "index.html",
            "static/snapshot_data.js",
            "static/offline_adapter.js",
            "static/app.js",
            "static/api.js",
            "static/styles.css",
        }.issubset(namelist)

        index_html = zf.read("index.html").decode("utf-8")
        assert 'src="./static/' in index_html
        assert 'href="./static/' in index_html
        assert 'src="/static/' not in index_html
        assert 'href="/static/' not in index_html
        assert "snapshot_data.js" in index_html
        assert "offline_adapter.js" in index_html

        snap_js = zf.read("static/snapshot_data.js").decode("utf-8")
        assert "__BIJOU_SNAPSHOT__" in snap_js
        # No unescaped closing script tags inside JS payload
        assert "</script>" not in snap_js
        assert "<\\/script>" in snap_js

        json_start = snap_js.find("global.__BIJOU_SNAPSHOT__ = ") + len("global.__BIJOU_SNAPSHOT__ = ")
        json_end = snap_js.rfind(";\n})(window);")
        parsed_data = json.loads(snap_js[json_start:json_end])
        assert parsed_data["meta"]["read_only"] is True
        eff_q = next(e for e in parsed_data["efforts"] if e["id"] == "eff-quantum")
        assert "</script><script>alert(1)</script>" in eff_q["description"]

    export_file = tmp_path / "test_export.zip"
    result_path = export_snapshot_to_file(svc, export_file, as_of_date=date(2026, 5, 1))
    assert result_path == export_file
    assert export_file.exists()
    assert zipfile.is_zipfile(export_file)


def test_offline_snapshot_bundle_zero_external_links(tmp_path: Path) -> None:
    """Verifies all files inside the exported snapshot ZIP contain zero external CDN links."""
    svc = _create_seeded_orchestrator(tmp_path)
    zip_bytes = build_snapshot_zip_bytes(svc)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(tmp_path / "extracted_snapshot")

    extracted_dir = tmp_path / "extracted_snapshot"
    files_to_check = (
        list(extracted_dir.glob("**/*.html"))
        + list(extracted_dir.glob("**/*.css"))
        + list(extracted_dir.glob("**/*.js"))
    )
    assert len(files_to_check) >= 10

    url_pattern = re.compile(r"https?://(?!www\.w3\.org/)[^\s\"'>]+")
    violations = []
    for f in files_to_check:
        content = f.read_text(encoding="utf-8")
        matches = url_pattern.findall(content)
        if matches:
            violations.append((f.name, matches))

    assert not violations, f"Detected external URL dependencies in snapshot bundle: {violations}"


def test_api_v1_snapshot_export_zip_and_base64(tmp_path: Path) -> None:
    """Verifies GET /api/v1/snapshot/export returns binary ZIP by default and base64 envelope on request."""
    svc = _create_seeded_orchestrator(tmp_path)
    set_orchestrator(svc)
    try:
        client = TestClient(app)

        # Default ZIP stream
        resp = client.get("/api/v1/snapshot/export?as_of_date=2026-05-01")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert 'filename="bijou_snapshot_2026-05-01.zip"' in resp.headers["content-disposition"]
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert "index.html" in zf.namelist()
            assert "static/snapshot_data.js" in zf.namelist()

        # Desktop-bridge friendly base64 JSON envelope
        b64_resp = client.get("/api/v1/snapshot/export?as_of_date=2026-05-01&format=base64")
        assert b64_resp.status_code == 200
        assert b64_resp.headers["content-type"] == "application/json"
        envelope = b64_resp.json()
        assert envelope["filename"] == "bijou_snapshot_2026-05-01.zip"
        assert envelope["media_type"] == "application/zip"
        decoded_zip = base64.b64decode(envelope["content_base64"])
        assert len(decoded_zip) == envelope["size_bytes"]
        assert zipfile.is_zipfile(io.BytesIO(decoded_zip))
    finally:
        set_orchestrator(None)


def test_desktop_bridge_snapshot_export_dispatch(tmp_path: Path) -> None:
    """Verifies snapshot export works cleanly over in-process BijouDesktopBridge (zero HTTP ports)."""
    from bijou.config import BijouSettings

    settings = BijouSettings(
        db_uri=f"sqlite:///{tmp_path}/bridge_snap.db",
        duckdb_path=str(tmp_path / "bridge_snap.duckdb"),
        enable_reasoning=False,
    )
    with BijouDesktopBridge(settings=settings) as bridge:
        res_org = bridge.dispatch(
            "POST",
            "/api/v1/organizations",
            body={"id": "org-bridge", "name": "Bridge Org", "is_managed": True},
        )
        assert res_org["ok"] is True

        export_res = bridge.dispatch("GET", "/api/v1/snapshot/export?format=base64")
        assert export_res["ok"] is True
        assert export_res["status"] == 200
        payload = export_res["data"]
        assert payload["filename"].endswith(".zip")
        zip_bytes = base64.b64decode(payload["content_base64"])
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "index.html" in zf.namelist()
            snap_js = zf.read("static/snapshot_data.js").decode("utf-8")
            assert "org-bridge" in snap_js


def test_cli_export_snapshot_option(tmp_path: Path) -> None:
    """Verifies CLI flag --export-snapshot generates ZIP archive directly without running server."""
    db_file = tmp_path / "cli_test.db"
    duck_file = tmp_path / "cli_test.duckdb"
    target_zip = tmp_path / "cli_exported.zip"

    repo = SqlAlchemyGraphRepository(db_uri=f"sqlite:///{db_file}")
    repo.upsert_organization(OrganizationDTO(id="org-cli", name="CLI Org", is_managed=True))

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--export-snapshot",
            str(target_zip),
            "--db-uri",
            f"sqlite:///{db_file}",
            "--duckdb-path",
            str(duck_file),
        ],
    )
    assert result.exit_code == 0
    assert "Exported offline Bijou snapshot" in result.output
    assert target_zip.exists()

    with zipfile.ZipFile(target_zip) as zf:
        assert "index.html" in zf.namelist()
        assert "static/snapshot_data.js" in zf.namelist()


def test_offline_adapter_runtime_parity_with_node(tmp_path: Path) -> None:
    """Executes snapshot_data.js + offline_adapter.js + api.js in Node.js to validate runtime behavior."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js runtime not available in environment")

    svc = _create_seeded_orchestrator(tmp_path)
    zip_bytes = build_snapshot_zip_bytes(svc, as_of_date=date(2026, 5, 1))
    extract_dir = tmp_path / "node_runtime_test"
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(extract_dir)

    # Compare directly against Python orchestrator ground-truth simulation
    sim_req = BillOfEffortsSimulationRequestDTO(
        effort_slips={"eff-quantum": 40},
        toggle_mitigators={"mit-accel": True},
        add_allocations=[
            SimulatedPoolAllocationDTO(
                org_id="org-alpha",
                pool_id="pool-staff",
                effort_id="eff-quantum",
                requirement_id="req-1",
                resourcing_type=ResourceCategory.STAFF,
                amount=1.0,
                unit="FTE",
                is_generic=False,
            ),
            SimulatedPoolAllocationDTO(
                org_id="org-alpha",
                pool_id="pool-money",
                effort_id="eff-downstream",
                resourcing_type=ResourceCategory.MONEY,
                amount=10_000.0,
                unit="USD",
                is_generic=False,
            ),
        ],
    )
    py_sim = svc.simulate_bill_of_efforts(sim_req, as_of_date=date(2026, 5, 1)).model_dump(mode="json")
    py_ends = {n["effort"]["id"]: n["forecast_end"] for n in py_sim["projected_tree"]["nodes"]}
    assert py_ends["eff-quantum"] == "2026-08-10"
    assert py_ends["eff-downstream"] == "2026-11-10"

    harness = r"""
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = process.argv[2];

// Minimal browser/DOM stubs
const badgeEl = {
  textContent: "",
  title: "",
  classes: new Set(),
  classList: {
    add: (...c) => c.forEach((x) => badgeEl.classes.add(x)),
    remove: (...c) => c.forEach((x) => badgeEl.classes.delete(x)),
    contains: (c) => badgeEl.classes.has(c),
  },
};
const bodyClasses = new Set();
const documentStub = {
  readyState: "complete",
  getElementById: (id) => (id === "engine-health-badge" ? badgeEl : null),
  body: {
    classList: {
      add: (...c) => c.forEach((x) => bodyClasses.add(x)),
      contains: (c) => bodyClasses.has(c),
    },
  },
  addEventListener: () => {},
};
const windowObj = {
  document: documentStub,
  URLSearchParams,
  addEventListener: () => {},
  removeEventListener: () => {},
};
windowObj.window = windowObj;
windowObj.globalThis = windowObj;

const context = vm.createContext({
  window: windowObj,
  document: documentStub,
  URLSearchParams,
  console,
  setTimeout,
  clearTimeout,
});

for (const file of ["static/snapshot_data.js", "static/offline_adapter.js", "static/api.js"]) {
  const code = fs.readFileSync(path.join(root, file), "utf8");
  vm.runInContext(code, context, { filename: file });
}

(async () => {
  const api = windowObj.BijouApi;
  assert.strictEqual(windowObj.__BIJOU_SNAPSHOT_ACTIVE__, true);
  assert.strictEqual(badgeEl.textContent, "SNAPSHOT (OFFLINE)");
  assert.strictEqual(bodyClasses.has("bijou-snapshot-mode"), true);

  // 1. Health & Tools & Single Entity GETs
  const health = await api.health();
  assert.strictEqual(health.engine, "bijou-v2-snapshot");

  const tools = await api.listTools();
  assert.ok(Array.isArray(tools) && tools.length >= 4);

  const singleOrg = await api.getOrganization("org-alpha");
  assert.strictEqual(singleOrg.name, "Alpha Command");

  const singleIntr = await api.getInterest("intr-cyber");
  assert.strictEqual(singleIntr.name, "Cyber Resiliency");

  const singleEff = await api.getEffort("eff-quantum");
  assert.strictEqual(singleEff.name, "Post-Quantum Key Exchange");

  // 2. Hierarchy priority rollup toggle parity
  const treeInherited = await api.getCapabilityTree({ include_hierarchy_priorities: true });
  const alphaCyberInh = treeInherited.effective_priorities.find(
    (p) => p.org_id === "org-alpha" && p.interest_id === "intr-cyber"
  );
  assert.ok(alphaCyberInh && alphaCyberInh.inherited_from_org_id === "org-parent");

  const treeDirect = await api.getCapabilityTree({ include_hierarchy_priorities: false });
  const alphaCyberDir = treeDirect.effective_priorities.find(
    (p) => p.org_id === "org-alpha" && p.interest_id === "intr-cyber"
  );
  assert.strictEqual(alphaCyberDir, undefined);

  // 3. Confidence pedigree filtering
  const treeConfirmed = await api.getCapabilityTree({ min_confidence: "CONFIRMED" });
  assert.ok(treeConfirmed.org_interest_edges.every((e) => e.confidence === "CONFIRMED"));
  assert.ok(treeConfirmed.effort_interest_edges.every((e) => e.confidence === "CONFIRMED"));

  // 4. Org focal & briefing hierarchy toggle + perspective header reflection
  api.setPerspective("MANAGED_ORG_OWNER", "org-alpha");
  const persp = await api.getPerspectiveState();
  assert.strictEqual(persp.mode, "MANAGED_ORG_OWNER");
  assert.strictEqual(persp.active_org_id, "org-alpha");

  const orgBriefDir = await api.getBriefing({ subject_org_id: "org-alpha", include_hierarchy_inheritance: false });
  assert.strictEqual(orgBriefDir.active_access_mode, "MANAGED_ORG_OWNER");
  assert.strictEqual(orgBriefDir.include_hierarchy_inheritance, false);
  assert.ok(orgBriefDir.priority_interests.every((p) => p.inherited_from_org_id === null));

  // 5. Simulation: slip propagation + mitigator recovery + skill mismatch + Color-of-Money
  const sim = await api.simulateBillOfEfforts({
    effort_slips: { "eff-quantum": 40 },
    toggle_mitigators: { "mit-accel": true },
    add_allocations: [
      {
        org_id: "org-alpha",
        pool_id: "pool-staff",
        effort_id: "eff-quantum",
        requirement_id: "req-1",
        resourcing_type: "STAFF",
        amount: 1,
        unit: "FTE",
        is_generic: false,
      },
      {
        org_id: "org-alpha",
        pool_id: "pool-money",
        effort_id: "eff-downstream",
        resourcing_type: "MONEY",
        amount: 10000,
        unit: "USD",
        is_generic: false,
      },
    ],
  });

  // Base eff-quantum end=2026-06-01; mit-accel (-20d) cancels risk-key (+20d), skill mismatch adds +30d, plus +40d slip = +70d -> 2026-08-10
  const projQuantum = sim.projected_tree.nodes.find((n) => n.effort.id === "eff-quantum");
  const projDownstream = sim.projected_tree.nodes.find((n) => n.effort.id === "eff-downstream");
  assert.strictEqual(projQuantum.forecast_end, "2026-08-10");
  // Downstream started 2026-07-01 -> pushed to 2026-08-10 (+40d shift -> 2026-11-10)
  assert.strictEqual(projDownstream.forecast_end, "2026-11-10");
  assert.ok(sim.impacted_effort_ids.includes("eff-quantum"));
  assert.ok(sim.impacted_effort_ids.includes("eff-downstream"));

  // Skill mismatch warning registered
  assert.strictEqual(sim.skill_mismatch_warnings.length, 1);
  assert.strictEqual(sim.newly_registered_risks.length, 1);

  // Color-of-Money violation registered on pool-money -> eff-downstream (intr-other not cyber)
  const moneyPoolBal = sim.pool_balances.find((pb) => pb.pool.id === "pool-money");
  assert.ok(moneyPoolBal.color_of_money_violations.length === 1);
  // Cost delta: +50,000 mitigator surge + 10,000 money allocation = +60,000
  assert.strictEqual(sim.total_cost_delta, 60000);
  assert.strictEqual(sim.net_risk_count_delta, 1);

  // 6. Mutations cleanly blocked with HTTP 403
  let blockedMut = false;
  try {
    await api.upsertOrganization({ id: "x", name: "X" });
  } catch (err) {
    assert.strictEqual(err.status, 403);
    blockedMut = true;
  }
  assert.strictEqual(blockedMut, true);

  let blockedCommit = false;
  try {
    await api.commitBillOfEfforts({});
  } catch (err) {
    assert.strictEqual(err.status, 403);
    blockedCommit = true;
  }
  assert.strictEqual(blockedCommit, true);

  console.log("NODE_SNAPSHOT_PARITY_OK");
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
"""
    harness_path = tmp_path / "run_parity.js"
    harness_path.write_text(harness, encoding="utf-8")

    proc = subprocess.run(
        [node_bin, str(harness_path), str(extract_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Node parity harness failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "NODE_SNAPSHOT_PARITY_OK" in proc.stdout
