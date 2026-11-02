"""End-to-End Headless Browser GUI Tests for Bijou Web Interface using Selenium.

Exercises the live application shell across all 4 decision-support lenses:
1. 4X Stratified Tech Tree & What-If Slip Simulation Drawer
2. Executive Multi-Perspective 1-Slide Briefing (4 Quadrants)
3. Single-Thing Focal Dashboard & Live Portfolio Trade-Off Matrix
4. Manifest JSON Studio & Quick Entity Administration
"""

import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from bijou_ingest import ManifestIngestor
from bijou_sdk import BijouClient
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bijou.api.app import create_app
from bijou.config import BijouSettings


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_test_server(app, host: str, port: int, server_holder: dict) -> None:
    config = uvicorn.Config(app=app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    server_holder["server"] = server
    server.run()


@pytest.fixture(scope="module")
def live_gui_server():
    """Module-scoped fixture starting an isolated Bijou server with ingested datasets."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    tmp_dir = tempfile.mkdtemp(prefix="bijou_sel_")
    tmp_path = Path(tmp_dir)

    db_file = tmp_path / "gui_test.db"
    duckdb_file = tmp_path / "gui_telemetry.duckdb"

    settings = BijouSettings(
        db_uri=f"sqlite:///{db_file}",
        duckdb_path=str(duckdb_file),
        enable_reasoning=False,
    )
    app = create_app(settings)

    port = find_free_port()
    host = "127.0.0.1"
    server_holder: dict = {}
    server_thread = threading.Thread(
        target=run_test_server,
        args=(app, host, port, server_holder),
        daemon=True,
    )
    server_thread.start()

    base_url = f"http://{host}:{port}"
    for _ in range(50):
        try:
            with socket.create_connection((host, port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    # Ingest reference datasets into live running server over HTTP
    datasets_dir = root_dir / "datasets"
    yaml_path = datasets_dir / "joint_isr_architecture.yaml"
    jsonl_path = datasets_dir / "satellite_cascade_telemetry.jsonl"

    with BijouClient(base_url=base_url) as sdk_client:
        ingestor = ManifestIngestor(client=sdk_client)
        ingestor.ingest_manifest_file(yaml_path, base_dir=datasets_dir)
        ingestor.ingest_telemetry_file(jsonl_path, base_dir=datasets_dir)

    yield base_url

    if "server" in server_holder:
        server_holder["server"].should_exit = True
    time.sleep(0.5)

    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def browser_driver():
    """Module-scoped headless Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,940")

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    try:
        driver.quit()
    except WebDriverException:
        pass


def test_gui_full_lens_workflows_and_interactions(live_gui_server: str, browser_driver: webdriver.Chrome) -> None:
    """Verifies all 4 lenses and drawer workflows in headless Chrome."""
    driver = browser_driver
    wait = WebDriverWait(driver, 10)
    driver.get(live_gui_server)

    # 1. Shell & Header Verification
    assert "Bijou" in driver.title
    brand_el = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "brand")))
    assert "BIJOU" in brand_el.text

    # 2. Lens 1: Tech Tree & SVG Connectors
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "node-card")))
    node_cards = driver.find_elements(By.CLASS_NAME, "node-card")
    assert len(node_cards) >= 10

    # Verify SVG overlay contains drawn paths
    svg_overlay = driver.find_element(By.CLASS_NAME, "tech-tree-svg-overlay")
    assert svg_overlay is not None
    edge_paths = svg_overlay.find_elements(By.TAG_NAME, "path")
    assert len(edge_paths) > 0

    # 3. What-If Slip Simulation Drawer
    target_card = driver.find_element(By.CSS_SELECTOR, ".node-card[data-milestone-id='ms-space-chamber-proto']")
    driver.execute_script("arguments[0].click();", target_card)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#slip-drawer.open")))
    time.sleep(0.4)

    drawer_title = driver.find_element(By.ID, "drawer-milestone-title").text
    assert "Thermal Vacuum Chamber Test" in drawer_title or len(drawer_title) > 0

    days_slider = driver.find_element(By.ID, "slip-days-slider")
    driver.execute_script("arguments[0].value = 90;", days_slider)

    apply_btn = driver.find_element(By.ID, "apply-slip-btn")
    driver.execute_script("arguments[0].click();", apply_btn)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#slip-simulation-results div")))
    results_text = driver.find_element(By.ID, "slip-simulation-results").text
    assert "Impacted Nodes" in results_text
    assert "ROI Delta" in results_text

    # Test Decision Provenance Ledger (REC-019)
    author_input = driver.find_element(By.ID, "decision-author")
    just_input = driver.find_element(By.ID, "decision-justification")
    commit_btn = driver.find_element(By.ID, "commit-decision-btn")
    author_input.send_keys("Chief Architect")
    just_input.send_keys("Accelerated thermal testing to mitigate sensor payload delivery risk.")
    driver.execute_script("arguments[0].click();", commit_btn)
    time.sleep(0.5)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#drawer-decision-logs div")))
    logs_text = driver.find_element(By.ID, "drawer-decision-logs").text
    assert "Chief Architect" in logs_text
    assert "Accelerated thermal testing" in logs_text

    close_btn = driver.find_element(By.ID, "close-drawer-btn")
    driver.execute_script("arguments[0].click();", close_btn)
    time.sleep(0.3)

    # 4. Lens 2: Executive Perspective Briefing
    briefing_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='briefing-one-pager']")
    briefing_tab.click()

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "briefing-slide")))
    briefing_slide = driver.find_element(By.CLASS_NAME, "briefing-slide")
    assert "Executive Perspective Briefing" in briefing_slide.text

    # Verify 4 quadrants
    quadrants = driver.find_elements(By.CLASS_NAME, "quadrant-card")
    assert len(quadrants) >= 4
    quadrant_texts = [q.text for q in quadrants]
    assert any("Supported Concerns" in t for t in quadrant_texts)
    assert any("Owned Things" in t for t in quadrant_texts)
    assert any("Cross-Org Dependencies" in t for t in quadrant_texts)
    assert any("Committed Cost" in t for t in quadrant_texts)

    # 5. Lens 3: Single-Thing Focal Dashboard & Trade-Off Matrix
    focal_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='focal-dashboard']")
    focal_tab.click()

    # Select thing known to have operational telemetry events
    thing_select = wait.until(EC.presence_of_element_located((By.ID, "focal-thing-select")))
    driver.execute_script("arguments[0].value = 'thing-hypersonic-sensor-constellation';", thing_select)

    inspect_btn = wait.until(EC.element_to_be_clickable((By.ID, "focal-refresh-btn")))
    inspect_btn.click()

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#focal-dashboard-target .quadrant-card")))
    focal_target = driver.find_element(By.ID, "focal-dashboard-target")
    assert "Milestone Progression" in focal_target.text
    assert "Direct Causal Linkages" in focal_target.text

    # Verify 2-Hop Radial Ego-Network HTML5 Canvas (REC-013)
    canvas = driver.find_element(By.ID, "ego-network-canvas")
    assert canvas is not None

    # Verify Telemetry Rollups with inline SVG Sparklines (REC-014)
    sparklines = driver.find_elements(By.CLASS_NAME, "telemetry-sparkline")
    assert len(sparklines) > 0

    # Verify Pareto Frontier Optimizer (REC-008)
    pareto_btn = driver.find_element(By.ID, "compute-pareto-btn")
    driver.execute_script("arguments[0].click();", pareto_btn)
    time.sleep(0.6)

    pareto_wrapper = driver.find_element(By.ID, "pareto-scatterplot-wrapper")
    assert pareto_wrapper.is_displayed()
    pareto_svg = driver.find_element(By.ID, "pareto-scatter-svg")
    assert pareto_svg is not None

    # Check candidate boxes and run tradeoff
    checkboxes = driver.find_elements(By.CLASS_NAME, "tradeoff-candidate-checkbox")
    assert len(checkboxes) >= 2
    for cb in checkboxes[:2]:
        if not cb.is_selected():
            driver.execute_script("arguments[0].click();", cb)

    tradeoff_btn = driver.find_element(By.ID, "run-tradeoff-btn")
    driver.execute_script("arguments[0].click();", tradeoff_btn)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tradeoff-results-target h4")))
    tradeoff_results = driver.find_element(By.ID, "tradeoff-results-target").text
    assert "Trade-Off Evaluation Results" in tradeoff_results
    assert "Aggregate ROI" in tradeoff_results

    # 6. Lens 4: Manifest JSON Studio, Diagnostics & Direct Manipulation Workbench
    crud_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='crud-studio']")
    crud_tab.click()

    export_btn = wait.until(EC.element_to_be_clickable((By.ID, "crud-export-btn")))
    export_btn.click()
    time.sleep(0.8)

    json_textarea = driver.find_element(By.ID, "crud-manifest-json")
    exported_val = json_textarea.get_attribute("value")
    assert "organizations" in exported_val
    assert "things" in exported_val
    assert "causal_gates" in exported_val

    # Verify Pre-Flight Diagnostics Linter HUD (REC-017)
    validate_btn = driver.find_element(By.ID, "crud-validate-btn")
    driver.execute_script("arguments[0].click();", validate_btn)
    time.sleep(0.6)

    hud = driver.find_element(By.ID, "crud-diagnostic-hud")
    assert hud.is_displayed()
    assert "CRITICAL TOPOLOGICAL BLOCKERS" in hud.text or "ALL PRE-FLIGHT CHECKS PASSED" in hud.text or "Zero blockers" in hud.text

    # Verify Visual Entity Direct Manipulation Workbench (REC-016)
    visual_cards = driver.find_elements(By.CLASS_NAME, "visual-card")
    assert len(visual_cards) > 0
    visual_lanes = driver.find_elements(By.CLASS_NAME, "visual-lane")
    assert len(visual_lanes) == 4
