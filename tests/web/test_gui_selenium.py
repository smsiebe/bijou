"""End-to-End Headless Browser GUI Tests for Bijou v2 Web Interface using Selenium.

Verifies:
1. View A: Stateful Capability Progression DAG + Hover Emphasis + Pedigree/Perspective controls
2. View B: Tri-Partite Architectural Flow + Indirect Shared-Interest Paths
3. Global Neural Graph View: Free-floating Orgs/Efforts/Interests + Node Dragging + Hover Emphasis
4. Graph-Native Editing: Right-click canvas creation modal + Drag-to-connect Edge Creation modal
5. Toggleable Bill of Efforts Cart Dock (mitigator toggle & live simulation)
6. Contextual Entity Puck Inspector, Executive Briefing & Entity Studio
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
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from bijou.api.app import create_app
from bijou.config import BijouSettings
from bijou.sdk import BijouClient, ManifestIngestor


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


def test_gui_views_graph_native_editing_and_studio(live_gui_server: str, browser_driver: webdriver.Chrome) -> None:
    driver = browser_driver
    wait = WebDriverWait(driver, 10)
    driver.get(live_gui_server)

    assert "Bijou" in driver.title
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "effort-card")))

    # 1. View A renders 6 Effort cards, SVG connectors & hover neighborhood emphasis
    effort_cards = driver.find_elements(By.CLASS_NAME, "effort-card")
    assert len(effort_cards) == 6
    svg_paths = driver.find_elements(By.CSS_SELECTOR, "#canvas-svg-layer path")
    assert len(svg_paths) >= 5

    hover_card = driver.find_element(By.CSS_SELECTOR, ".effort-card[data-effort-id='eff-optical-bench']")
    ActionChains(driver).move_to_element(hover_card).perform()
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".effort-card.highlighted")) >= 2)
    assert len(driver.find_elements(By.CSS_SELECTOR, ".effort-card.dimmed")) >= 3

    first_card = driver.find_element(By.CSS_SELECTOR, ".effort-card[data-effort-id='eff-edge-correlator']")

    # 2. Contextual Effort Puck opens & closes cleanly
    driver.execute_script("arguments[0].click();", first_card)
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "puck-backdrop").get_attribute("class"))
    wait.until(lambda d: "Correlator" in d.find_element(By.ID, "puck-title").text)
    driver.execute_script("document.getElementById('btn-close-puck').click();")

    # 3. Switch to View B: Tri-Partite Architectural Flow
    driver.execute_script("document.getElementById('btn-mode-b').click();")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tripartite-grid")))
    tri_nodes = driver.find_elements(By.CLASS_NAME, "tri-node")
    assert len(tri_nodes) >= 15

    # 4. Switch to Global Neural Graph & verify non-overlapping free-floating nodes + wheel zoom + dragging
    driver.execute_script("document.getElementById('btn-mode-neural').click();")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "neural-node")))
    neural_nodes = driver.find_elements(By.CLASS_NAME, "neural-node")
    assert len(neural_nodes) >= 15

    # Verify zero bounding-box overlaps on rendered Global Neural Graph nodes
    overlap_pairs = driver.execute_script(
        "var els = Array.from(document.querySelectorAll('.neural-node'));"
        "var rects = els.map(function(el){ return {id: el.dataset.entityId, r: el.getBoundingClientRect()}; });"
        "var bad = [];"
        "for (var i = 0; i < rects.length; i++) {"
        "  for (var j = i + 1; j < rects.length; j++) {"
        "    var a = rects[i].r, b = rects[j].r;"
        "    if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) {"
        "      bad.push([rects[i].id, rects[j].id]);"
        "    }"
        "  }"
        "}"
        "return bad;"
    )
    assert overlap_pairs == [], f"Overlapping neural nodes found: {overlap_pairs}"

    # Verify scroll-wheel zoom works smoothly on canvas viewport & Fit resets it
    viewport = driver.find_element(By.ID, "canvas-viewport")
    driver.execute_script(
        "var r = arguments[0].getBoundingClientRect();"
        "arguments[0].dispatchEvent(new WheelEvent('wheel', {bubbles:true, cancelable:true, deltaY:-120, clientX: r.left + 200, clientY: r.top + 200}));",
        viewport,
    )
    wait.until(lambda d: d.find_element(By.ID, "zoom-level-label").text != "100%")
    driver.execute_script("document.getElementById('btn-zoom-reset').click();")
    wait.until(lambda d: d.find_element(By.ID, "zoom-level-label").text == "100%")

    # Verify layer toggles (hide/show Interests) & breadcrumb Back/Reset
    assert len(driver.find_elements(By.CSS_SELECTOR, ".neural-node.kind-interest")) >= 4
    driver.execute_script("document.getElementById('neural-toggle-interests').click();")
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".neural-node.kind-interest")) == 0)
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "canvas-breadcrumb-bar").get_attribute("class"))

    # Verify Org multi-filter narrows visible graph, then Back & Reset Graph restore full graph
    driver.execute_script("document.getElementById('btn-neural-org-filter').click();")
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "neural-org-filter-menu").get_attribute("class"))
    driver.execute_script("document.querySelector('#neural-org-filter-menu input[type=checkbox]').click();")
    wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "crumb-btn")) >= 3)
    driver.execute_script("document.getElementById('btn-breadcrumb-back').click();")
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".neural-node.kind-interest")) == 0)
    driver.execute_script("document.getElementById('btn-breadcrumb-reset').click();")
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".neural-node.kind-interest")) >= 4)

    # Verify right-click Node Isolation + Breadcrumb Reset
    isolate_target = driver.find_element(By.CSS_SELECTOR, ".neural-node[data-entity-id='eff-optical-bench']")
    total_before_isolate = len(driver.find_elements(By.CLASS_NAME, "neural-node"))
    driver.execute_script(
        "var r = arguments[0].getBoundingClientRect();"
        "arguments[0].dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true, button:2, clientX: r.left + 20, clientY: r.top + 20}));",
        isolate_target,
    )
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "graph-context-menu").get_attribute("class"))
    focus_btn = driver.find_element(By.CSS_SELECTOR, "#graph-context-menu [data-act='focus']")
    driver.execute_script("arguments[0].click();", focus_btn)
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".neural-node.focus-root")) == 1)
    assert len(driver.find_elements(By.CLASS_NAME, "neural-node")) < total_before_isolate
    driver.execute_script("document.getElementById('btn-breadcrumb-reset').click();")
    wait.until(lambda d: len(d.find_elements(By.CLASS_NAME, "neural-node")) == total_before_isolate)

    drag_node = driver.find_element(By.CSS_SELECTOR, ".neural-node[data-entity-id='eff-edge-correlator']")
    before_left = drag_node.value_of_css_property("left")
    ActionChains(driver).drag_and_drop_by_offset(drag_node, 70, 45).perform()
    after_left = drag_node.value_of_css_property("left")
    assert before_left != after_left

    # 5. Graph-native Right-click Canvas Context Menu -> Create Effort Modal
    driver.execute_script(
        "var r = arguments[0].getBoundingClientRect();"
        "arguments[0].dispatchEvent(new MouseEvent('contextmenu', {bubbles:true, cancelable:true, button:2, clientX: r.left + 40, clientY: r.top + 80}));",
        viewport,
    )
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "graph-context-menu").get_attribute("class"))
    create_btn = driver.find_element(By.CSS_SELECTOR, "#graph-context-menu [data-act='create'][data-kind='effort']")
    driver.execute_script("arguments[0].click();", create_btn)

    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "graph-node-modal-backdrop").get_attribute("class"))
    driver.find_element(By.ID, "gm-node-name").send_keys("Selenium Rapid Sensor Test")
    driver.find_element(By.ID, "gm-node-save-btn").click()
    wait.until(lambda d: "hidden" in d.find_element(By.ID, "graph-node-modal-backdrop").get_attribute("class"))
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".neural-node[data-entity-id='eff-selenium-rapid-sensor-test']")) == 1)

    # 6. Drag-to-connect from node connect port to another node -> Non-Technical Edge Creation Popup
    src_port = driver.find_element(
        By.CSS_SELECTOR,
        ".neural-node[data-entity-id='eff-edge-correlator'] .node-connect-port",
    )
    dst_node = driver.find_element(
        By.CSS_SELECTOR,
        ".neural-node[data-entity-id='eff-selenium-rapid-sensor-test']",
    )
    edge_count_before = len(driver.find_elements(By.CSS_SELECTOR, "#canvas-svg-layer path[data-edge-id]"))
    ActionChains(driver).click_and_hold(src_port).move_to_element(dst_node).release(dst_node).perform()
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "graph-edge-modal-backdrop").get_attribute("class"))
    edge_modal_text = driver.find_element(By.ID, "graph-edge-modal").text
    assert "NON_BLOCKING_INFORMS" not in edge_modal_text
    assert "SPECIALIZES" not in edge_modal_text
    driver.find_element(By.ID, "gm-edge-save-btn").click()
    wait.until(lambda d: "hidden" in d.find_element(By.ID, "graph-edge-modal-backdrop").get_attribute("class"))
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "#canvas-svg-layer path[data-edge-id]")) > edge_count_before)

    # 7. Open Bill of Efforts Cart Drawer on top of active view & run live simulation
    driver.execute_script("document.getElementById('btn-toggle-dock').click();")
    wait.until(lambda d: "hidden" not in d.find_element(By.ID, "bill-of-efforts-dock").get_attribute("class"))
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".boe-mit-toggle")))
    driver.execute_script("document.querySelector('.boe-mit-toggle').click();")
    wait.until(lambda d: int(d.find_element(By.ID, "cart-badge-count").text) >= 1)

    # 8. Switch Perspective Switcher to Managed Org Owner
    persp_select = Select(driver.find_element(By.ID, "perspective-select"))
    if len(persp_select.options) > 1:
        persp_select.select_by_index(1)

    # 9. Lens 2: Executive Briefing
    driver.execute_script("document.getElementById('nav-lens-briefing').click();")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "briefing-quadrants")))
    quads = driver.find_elements(By.CLASS_NAME, "quadrant-box")
    assert len(quads) == 4

    # 10. Lens 3: Entity & Graph Studio + Diagnostics
    driver.execute_script("document.getElementById('nav-lens-studio').click();")
    wait.until(EC.presence_of_element_located((By.ID, "st-org-form")))
    diag_tab = driver.find_element(By.CSS_SELECTOR, ".studio-tab[data-tab='diagnostics']")
    driver.execute_script("arguments[0].click();", diag_tab)
    wait.until(EC.presence_of_element_located((By.ID, "st-manifest-json")))

    # Verify zero SEVERE JS console errors across entire journey
    logs = driver.get_log("browser")
    severe = [entry for entry in logs if entry.get("level") == "SEVERE"]
    assert not severe, f"SEVERE JS console errors detected: {severe}"
