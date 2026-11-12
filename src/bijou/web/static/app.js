/* ==========================================================================
   Bijou v2 Application Controller
   Coordinates Lens Navigation, A/B/C Canvas Switcher, Perspective Seam,
   Pedigree Filters, Pan/Zoom, Entity Puck, Briefing, and Studio
   ========================================================================== */

(function (global) {
  "use strict";

  const state = {
    activeLens: "canvas",
    canvasMode: "A", // "A" | "B" | "C"
    minConfidence: "",
    includeHierarchyPriorities: true,
    asOfDate: "",
    orgFilter: "",
    clusterBy: "state",
    showIndirect: true,
    showPartners: true,
    zoom: 1.0,
    treeView: null,
    triView: null,
    simulationResult: null,
  };

  function notify(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4500);
  }

  function buildViewParams(extra = {}) {
    const p = {
      include_hierarchy_priorities: state.includeHierarchyPriorities,
      ...extra,
    };
    if (state.minConfidence) p.min_confidence = state.minConfidence;
    if (state.asOfDate) p.as_of_date = state.asOfDate;
    if (state.orgFilter && extra.includeOrgFilter) p.org_filter = state.orgFilter;
    return p;
  }

  function applyZoom() {
    const world = document.getElementById("canvas-world");
    const label = document.getElementById("zoom-level-label");
    if (world) world.style.transform = `scale(${state.zoom.toFixed(2)})`;
    if (label) label.textContent = `${Math.round(state.zoom * 100)}%`;
  }

  async function initPerspectiveDropdown() {
    try {
      const pstate = await global.BijouApi.getPerspectiveState();
      const sel = document.getElementById("perspective-select");
      if (!sel) return;
      const { escapeHtml } = global.BijouApi;
      const managedOpts = (pstate.managed_organizations || [])
        .map(
          (o) =>
            `<option value="OWNER:${escapeHtml(o.id)}">Org Owner: ${escapeHtml(o.name)}</option>`
        )
        .join("");
      sel.innerHTML = `<option value="GLOBAL_ANALYST">Global Analyst (Read/Model All)</option>${managedOpts}`;
    } catch (_) {
      // Fallback leaves default Global Analyst option intact
    }
  }

  let dockController = null;
  let puckController = null;
  let briefingController = null;
  let studioController = null;

  function renderCanvasStage() {
    const svgEl = document.getElementById("canvas-svg-layer");
    const domEl = document.getElementById("canvas-dom-layer");
    const worldEl = document.getElementById("canvas-world");
    const aOverlays = document.getElementById("view-a-overlay-wrap");
    const bOverlays = document.getElementById("view-b-overlay-wrap");

    if (state.canvasMode === "B") {
      aOverlays?.classList.add("hidden");
      bOverlays?.classList.remove("hidden");
      global.BijouViewB.renderViewBTripartite({
        triView: state.triView,
        svgEl,
        domEl,
        worldEl,
        showIndirect: state.showIndirect,
        showPartners: state.showPartners,
        onSelectEntity: (kind, id) => puckController.open(kind, id, buildViewParams()),
      });
    } else {
      aOverlays?.classList.remove("hidden");
      bOverlays?.classList.add("hidden");
      const activeTree =
        state.canvasMode === "C" && state.simulationResult?.projected_tree
          ? state.simulationResult.projected_tree
          : state.treeView;
      const impactedIds =
        state.canvasMode === "C" && state.simulationResult
          ? state.simulationResult.impacted_effort_ids
          : [];

      global.BijouViewA.renderViewADag({
        treeView: activeTree,
        svgEl,
        domEl,
        worldEl,
        clusterBy: state.clusterBy,
        impactedIds,
        onSelectEffort: (effortId) => puckController.open("effort", effortId, buildViewParams()),
      });
    }
  }

  async function refreshAllData() {
    const healthBadge = document.getElementById("engine-health-badge");
    try {
      await global.BijouApi.health();
      if (healthBadge) {
        healthBadge.textContent = "ENGINE ONLINE";
        healthBadge.classList.remove("warn");
      }
    } catch (_) {
      if (healthBadge) {
        healthBadge.textContent = "ENGINE OFFLINE";
        healthBadge.classList.add("warn");
      }
    }

    try {
      const [tree, tri] = await Promise.all([
        global.BijouApi.getCapabilityTree(buildViewParams({ includeOrgFilter: true })),
        global.BijouApi.getTripartiteFlow(buildViewParams()),
      ]);
      state.treeView = tree;
      state.triView = tri;

      // Populate top Org Scope filter in View A
      const orgFilterSel = document.getElementById("view-a-org-filter");
      if (orgFilterSel) {
        const { escapeHtml } = global.BijouApi;
        const orgs = tri.capability_tree?.organizations || tree.organizations || [];
        const prev = state.orgFilter;
        orgFilterSel.innerHTML =
          `<option value="">All Organizations</option>` +
          orgs.map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)}</option>`).join("");
        orgFilterSel.value = prev;
        briefingController.setOrganizations(orgs);
      }

      dockController.setBaseline(tri.capability_tree || tree, tri.pool_balances || []);
      renderCanvasStage();

      if (state.activeLens === "briefing") {
        await briefingController.refresh(buildViewParams());
      } else if (state.activeLens === "studio") {
        await studioController.refresh();
      }
    } catch (err) {
      notify(`Failed to load Bijou graph: ${err.message}`, "error");
    }
  }

  function switchLens(lens) {
    state.activeLens = lens;
    document.querySelectorAll(".lens-btn").forEach((b) => b.classList.toggle("active", b.dataset.lens === lens));
    document.querySelectorAll(".lens-panel").forEach((p) => p.classList.toggle("active", p.id === `lens-${lens}`));

    if (lens === "briefing") {
      briefingController.refresh(buildViewParams());
    } else if (lens === "studio") {
      studioController.refresh();
    } else {
      renderCanvasStage();
    }
  }

  function switchCanvasMode(mode) {
    state.canvasMode = mode;
    document.querySelectorAll(".abc-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));

    if (mode === "C") {
      dockController.setOpen(true);
      document.getElementById("boe-mode-subtitle").textContent = "Live Decision Workbench (Mode C)";
    } else {
      dockController.setOpen(false);
    }
    renderCanvasStage();
  }

  function setupPanning() {
    const viewport = document.getElementById("canvas-viewport");
    if (!viewport) return;
    let isPanning = false;
    let startX = 0;
    let startY = 0;
    let scrollLeft = 0;
    let scrollTop = 0;

    viewport.addEventListener("mousedown", (e) => {
      if (e.target.closest(".effort-card, .tri-node, button, input, select")) return;
      isPanning = true;
      startX = e.pageX - viewport.offsetLeft;
      startY = e.pageY - viewport.offsetTop;
      scrollLeft = viewport.scrollLeft;
      scrollTop = viewport.scrollTop;
    });
    window.addEventListener("mouseup", () => {
      isPanning = false;
    });
    viewport.addEventListener("mousemove", (e) => {
      if (!isPanning) return;
      e.preventDefault();
      const x = e.pageX - viewport.offsetLeft;
      const y = e.pageY - viewport.offsetTop;
      viewport.scrollLeft = scrollLeft - (x - startX);
      viewport.scrollTop = scrollTop - (y - startY);
    });
  }

  async function boot() {
    dockController = new global.BillOfEffortsDock({
      notify,
      onSimulationUpdated: (simRes) => {
        state.simulationResult = simRes;
        if (state.canvasMode !== "C" && simRes) {
          switchCanvasMode("C");
        } else {
          renderCanvasStage();
        }
      },
      onCommitted: async () => {
        state.simulationResult = null;
        await refreshAllData();
      },
    });

    puckController = new global.EntityPuck({
      notify,
      onStageMitigator: (mitId, nextVal) => {
        switchLens("canvas");
        switchCanvasMode("C");
        dockController.stageMitigator(mitId, nextVal);
      },
      onEditInStudio: async (tab, id) => {
        switchLens("studio");
        await studioController.refresh();
        if (tab === "efforts") studioController.openEffortForEdit(id);
      },
    });

    briefingController = new global.BriefingController({ notify });
    studioController = new global.StudioController({
      notify,
      onGraphMutated: async () => {
        await initPerspectiveDropdown();
        await refreshAllData();
      },
    });

    // Wire Lens Navigation
    document.querySelectorAll(".lens-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchLens(btn.dataset.lens));
    });

    // Wire A / B / C Canvas Switcher
    document.querySelectorAll(".abc-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchCanvasMode(btn.dataset.mode));
    });

    // Wire Perspective Switcher
    document.getElementById("perspective-select")?.addEventListener("change", (ev) => {
      const val = ev.target.value;
      if (val.startsWith("OWNER:")) {
        const oid = val.slice(6);
        global.BijouApi.setPerspective("MANAGED_ORG_OWNER", oid);
        notify(`Switched perspective to Managed Org Owner (${oid})`, "info");
      } else {
        global.BijouApi.setPerspective("GLOBAL_ANALYST", null);
        notify("Switched perspective to Global Analyst", "info");
      }
      refreshAllData();
    });

    // Wire Top Filters
    document.getElementById("pedigree-select")?.addEventListener("change", (ev) => {
      state.minConfidence = ev.target.value;
      refreshAllData();
    });

    document.getElementById("hierarchy-priority-toggle")?.addEventListener("change", (ev) => {
      state.includeHierarchyPriorities = Boolean(ev.target.checked);
      refreshAllData();
    });

    document.getElementById("as-of-date-input")?.addEventListener("change", (ev) => {
      state.asOfDate = ev.target.value || "";
      refreshAllData();
    });

    document.getElementById("btn-global-refresh")?.addEventListener("click", () => refreshAllData());

    // Wire View Overlays
    document.getElementById("view-a-org-filter")?.addEventListener("change", (ev) => {
      state.orgFilter = ev.target.value;
      refreshAllData();
    });

    document.getElementById("view-a-cluster-by")?.addEventListener("change", (ev) => {
      state.clusterBy = ev.target.value;
      renderCanvasStage();
    });

    document.getElementById("view-b-show-indirect")?.addEventListener("change", (ev) => {
      state.showIndirect = Boolean(ev.target.checked);
      renderCanvasStage();
    });

    document.getElementById("view-b-show-partners")?.addEventListener("change", (ev) => {
      state.showPartners = Boolean(ev.target.checked);
      renderCanvasStage();
    });

    // Dock Toggle & Zoom
    document.getElementById("btn-toggle-dock")?.addEventListener("click", () => {
      dockController.setOpen(!dockController.isOpen());
    });
    document.getElementById("btn-close-dock")?.addEventListener("click", () => {
      dockController.setOpen(false);
    });

    document.getElementById("btn-zoom-in")?.addEventListener("click", () => {
      state.zoom = Math.min(1.8, state.zoom + 0.15);
      applyZoom();
    });
    document.getElementById("btn-zoom-out")?.addEventListener("click", () => {
      state.zoom = Math.max(0.55, state.zoom - 0.15);
      applyZoom();
    });
    document.getElementById("btn-zoom-reset")?.addEventListener("click", () => {
      state.zoom = 1.0;
      applyZoom();
    });

    setupPanning();
    await initPerspectiveDropdown();
    await refreshAllData();
  }

  document.addEventListener("DOMContentLoaded", boot);
})(window);
