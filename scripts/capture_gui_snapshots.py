"""Automated GUI Testing and Reference Snapshot Generator for Bijou.

Starts an isolated Bijou ASGI server loaded with reference datasets,
drives headless Chrome via Selenium to exercise all 4 lenses,
verifies UI responsiveness and contract rendering, and saves
crisp snapshots to docs/assets/snapshots/.
"""

import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path

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


def run_server(app, host: str, port: int, server_holder: dict) -> None:
    config = uvicorn.Config(app=app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    server_holder["server"] = server
    server.run()


def capture_all_snapshots() -> None:
    root_dir = Path(__file__).resolve().parent.parent
    snapshots_dir = root_dir / "docs" / "assets" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="bijou_gui_")
    try:
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
            target=run_server,
            args=(app, host, port, server_holder),
            daemon=True,
        )
        server_thread.start()

        # Wait for server ready
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

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1440,940")

        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)

        try:
            print(f"Navigating to {base_url}...")
            driver.get(base_url)

            # Wait for app header and default Tech Tree canvas to load
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "app-header")))
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "node-card")))
            time.sleep(1.0)  # Allow SVG edge paths to render coordinates

            # Snapshot 1: 4X Stratified Tech Tree Canvas
            snap1 = snapshots_dir / "01_tech_tree_canvas.png"
            driver.save_screenshot(str(snap1))
            print(f"Captured: {snap1.name}")

            # Snapshot 2: What-If Slip Simulator Drawer
            # Click a milestone node card to open drawer
            node_card = driver.find_element(By.CSS_SELECTOR, ".node-card[data-milestone-id='ms-space-chamber-proto']")
            driver.execute_script("arguments[0].click();", node_card)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#slip-drawer.open")))
            time.sleep(0.5)  # Allow slide transition to finish

            # Set slip days to 90 and apply
            days_input = driver.find_element(By.ID, "slip-days-slider")
            driver.execute_script("arguments[0].value = 90;", days_input)

            apply_btn = driver.find_element(By.ID, "apply-slip-btn")
            driver.execute_script("arguments[0].click();", apply_btn)

            # Wait for calculation results
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#slip-simulation-results div")))

            # Commit a Decision Provenance Record (REC-019)
            author_input = driver.find_element(By.ID, "decision-author")
            just_input = driver.find_element(By.ID, "decision-justification")
            commit_btn = driver.find_element(By.ID, "commit-decision-btn")
            author_input.send_keys("Executive Flight Director")
            just_input.send_keys("Approved 90-day chamber re-test to validate multi-spectral sensor durability.")
            driver.execute_script("arguments[0].click();", commit_btn)
            time.sleep(0.8)

            snap2 = snapshots_dir / "02_slip_simulation_drawer.png"
            driver.save_screenshot(str(snap2))
            print(f"Captured: {snap2.name}")

            # Close drawer
            close_btn = driver.find_element(By.ID, "close-drawer-btn")
            driver.execute_script("arguments[0].click();", close_btn)
            time.sleep(0.4)

            # Snapshot 3: Executive Perspective Briefing (4 Quadrants)
            briefing_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='briefing-one-pager']")
            briefing_tab.click()
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "briefing-slide")))
            time.sleep(0.8)

            snap3 = snapshots_dir / "03_executive_briefing.png"
            driver.save_screenshot(str(snap3))
            print(f"Captured: {snap3.name}")

            # Snapshot 4: Single-Thing Focal Dashboard & Radial Ego-Network
            focal_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='focal-dashboard']")
            focal_tab.click()
            wait.until(EC.presence_of_element_located((By.ID, "focal-thing-select")))

            # Inspect selected thing
            inspect_btn = driver.find_element(By.ID, "focal-refresh-btn")
            inspect_btn.click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#focal-dashboard-target .quadrant-card")))
            time.sleep(1.0)

            snap4 = snapshots_dir / "04_focal_dashboard.png"
            driver.save_screenshot(str(snap4))
            print(f"Captured: {snap4.name}")

            # Snapshot 5: Trade-Off Matrix & Pareto Frontier Optimizer
            pareto_btn = driver.find_element(By.ID, "compute-pareto-btn")
            driver.execute_script("arguments[0].click();", pareto_btn)
            time.sleep(0.6)

            # Check two candidate boxes
            checkboxes = driver.find_elements(By.CLASS_NAME, "tradeoff-candidate-checkbox")
            if len(checkboxes) >= 2:
                for cb in checkboxes[:2]:
                    if not cb.is_selected():
                        driver.execute_script("arguments[0].click();", cb)

            tradeoff_btn = driver.find_element(By.ID, "run-tradeoff-btn")
            tradeoff_btn.click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tradeoff-results-target h4")))
            time.sleep(0.8)

            snap5 = snapshots_dir / "05_tradeoff_matrix.png"
            driver.save_screenshot(str(snap5))
            print(f"Captured: {snap5.name}")

            # Snapshot 6: Manifest JSON Studio, Diagnostic HUD & Visual Workbench
            crud_tab = driver.find_element(By.CSS_SELECTOR, "button[data-lens='crud-studio']")
            crud_tab.click()
            wait.until(EC.presence_of_element_located((By.ID, "crud-export-btn")))

            # Export manifest
            export_btn = driver.find_element(By.ID, "crud-export-btn")
            export_btn.click()
            time.sleep(1.0)

            # Run Pre-Flight Diagnostics (REC-017)
            validate_btn = driver.find_element(By.ID, "crud-validate-btn")
            driver.execute_script("arguments[0].click();", validate_btn)
            time.sleep(0.8)

            snap6 = snapshots_dir / "06_manifest_crud_studio.png"
            driver.save_screenshot(str(snap6))
            print(f"Captured: {snap6.name}")

            print("\nAll 6 GUI reference snapshots generated successfully!")

        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass
            if "server" in server_holder:
                server_holder["server"].should_exit = True
            time.sleep(0.5)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    capture_all_snapshots()
