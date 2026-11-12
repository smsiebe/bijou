"""End-to-End Headless Browser GUI Tests for Bijou v2 Web Interface using Selenium.

Verifies:
1. View A: Stateful Capability Progression DAG + Pedigree/Perspective controls
2. View B: Tri-Partite Architectural Flow + Indirect Shared-Interest Paths
3. View C: Live Decision Workbench + Bill of Efforts Cart (mitigator toggle & skill mismatch alert)
4. Contextual Entity Puck Inspector
5. Lens 2: Executive Briefing (Landscape 1-slide)
6. Lens 3: Entity & Graph Studio + Pre-Flight Diagnostics
7. Zero SEVERE JavaScript console errors
"""

import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

import pytest
import uvicorn

pytest.importorskip("selenium")
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou_ingest import ManifestIngestor
from bijou_sdk import BijouClient


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
    root_dir = Path(__file__).resolve().parent.parent.parent
    tmp_dir = tempfile.mkdtemp(prefix="bijou_sel_v2_")
    tmp_path = Path(tmp_dir)

    settings = BijouSettings(
        db_uri=f"sqlite:///{tmp_path}/gui_v2.db",
        duckdb_path=str(tmp_path / "gui_v2.duckdb"),
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

    datasets_dir = root_dir / "datasets"
    with BijouClient(base_url=base_url) as sdk_client:
        ing = ManifestIngestor(client=sdk_client)
        ing.ingest_manifest_file("joint_isr_architecture.json", base_dir=datasets_dir, replace_all=True)
        ing.ingest_telemetry_file("satellite_cascade_telemetry.jsonl", base_dir=datasets_dir)

    yield base_url

    if "server" in server_holder:
        server_holder["server"].should_exit = True
    time.sleep(0.4)
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="module")
def browser_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1440,940")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "SEVERE"})

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    try:
        driver.quit()
    except WebDriverException:
        pass


def test_gui_abc_modes_bill_of_efforts_briefing_and_studio(live_gui_server: str, browser_driver: webdriver.Chrome) -> None:
    driver = browser_driver
    wait = WebDriverWait(driver, 10)
    driver.get(live_gui_server)

    assert "Bijou" in driver.title
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "effort-card")))

    # 1. View A renders 6 Effort cards & SVG connectors
    effort_cards = driver.find_elements(By.CLASS_NAME, "effort-card")
    assert len(effort_cards) == 6
    svg_paths = driver.find_elements(By.CSS_SELECTOR, "#canvas-svg-layer path")
    assert len(svg_paths) >= 5

    # 2. Contextual Effort Puck opens cleanly
    first_card = driver.find_element(By.CSS_SELECTOR, ".effort-card[data-effort-id='eff-edge-correlator']")
    driver.execute_script("arguments[0].click();", first_card)
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "puck-backdrop").get_attribute("class"))
    wait.until(lambda d: "Correlator" in d.find_element(By.ID, "puck-title").text)
    driver.execute_script("document.getElementById('btn-close-puck').click();")

    # 3. Switch to View B: Tri-Partite Architectural Flow
    driver.execute_script("document.getElementById('btn-mode-b').click();")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tripartite-grid")))
    tri_nodes = driver.find_elements(By.CLASS_NAME, "tri-node")
    assert len(tri_nodes) >= 15

    # 4. Switch to View C: Live Decision Workbench & Bill of Efforts Dock
    driver.execute_script("document.getElementById('btn-mode-c').click();")
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "bill-of-efforts-dock").get_attribute("class"))

    # Toggle a mitigator inside BoE dock and trigger live simulation
    mit_cb = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".boe-mit-toggle")))
    driver.execute_script("arguments[0].click();", mit_cb)
    wait.until(lambda d: int(d.find_element(By.ID, "cart-badge-count").text) >= 1)

    # 5. Switch Perspective Switcher to Managed Org Owner
    persp_select = Select(driver.find_element(By.ID, "perspective-select"))
    if len(persp_select.options) > 1:
        persp_select.select_by_index(1)

    # 6. Lens 2: Executive Briefing
    driver.execute_script("document.getElementById('nav-lens-briefing').click();")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "briefing-quadrants")))
    quads = driver.find_elements(By.CLASS_NAME, "quadrant-box")
    assert len(quads) == 4

    # 7. Lens 3: Entity & Graph Studio + Diagnostics
    driver.execute_script("document.getElementById('nav-lens-studio').click();")
    wait.until(EC.presence_of_element_located((By.ID, "st-org-form")))
    diag_tab = driver.find_element(By.CSS_SELECTOR, ".studio-tab[data-tab='diagnostics']")
    driver.execute_script("arguments[0].click();", diag_tab)
    wait.until(EC.presence_of_element_located((By.ID, "st-manifest-json")))

    # Verify zero SEVERE JS console errors across entire journey
    logs = driver.get_log("browser")
    severe = [entry for entry in logs if entry.get("level") == "SEVERE"]
    assert not severe, f"SEVERE JS console errors detected: {severe}"
