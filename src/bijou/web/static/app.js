/* ==========================================================================
   Bijou v2 Application Controller
   Coordinates Lens Navigation, Canvas Switcher (Capability Tree / Tri-Partite /
   Global Neural Graph), Bill of Efforts Dock Drawer, Graph-Native Editing,
   Layer Toggles, Multi-Entity Filters, Node Isolation + Breadcrumb History,
   Scroll-Wheel Cursor Zoom, Perspective Seam, Entity Puck, Briefing & Studio
   ========================================================================== */

(function (global) {
  "use strict";

  const state = {
    activeLens: "canvas",
    canvasMode: "A", // "A" | "B" | "NEURAL"
    minConfidence: "",
    includeHierarchyPriorities: true,
    asOfDate: "",
    orgFilter: "",
    clusterBy: "state",
    showIndirect: true,
    showPartners: true,
    neuralShowStructural: true,
    neuralShowIndirect: true,
    neuralShowOrgs: true,
    neuralShowEfforts: true,
    neuralShowInterests: true,
    neuralFilterOrgIds: [],
    neuralFilterInterestIds: [],
    focusNodeKey: null,
    focusLabel: "",
    zoom: 1.0,
    treeView: null,
    triView: null,
    simulationResult: null,
  };

  let filterHistory = [];
  let historyIndex = 0;

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

  function captureFilterSnapshot() {
    return {
      canvasMode: state.canvasMode,
      orgFilter: state.orgFilter,
      focusNodeKey: state.focusNodeKey,
      focusLabel: state.focusLabel,
      neuralShowOrgs: state.neuralShowOrgs,
      neuralShowEfforts: state.neuralShowEfforts,
      neuralShowInterests: state.neuralShowInterests,
      neuralFilterOrgIds: [...state.neuralFilterOrgIds],
      neuralFilterInterestIds: [...state.neuralFilterInterestIds],
    };
  }

  function snapshotsEqual(a, b) {
    return (
      a.canvasMode === b.canvasMode &&
      a.orgFilter === b.orgFilter &&
      a.focusNodeKey === b.focusNodeKey &&
      a.neuralShowOrgs === b.neuralShowOrgs &&
      a.neuralShowEfforts === b.neuralShowEfforts &&
      a.neuralShowInterests === b.neuralShowInterests &&
      a.neuralFilterOrgIds.length === b.neuralFilterOrgIds.length &&
      a.neuralFilterOrgIds.every((v, i) => v === b.neuralFilterOrgIds[i]) &&
      a.neuralFilterInterestIds.length === b.neuralFilterInterestIds.length &&
      a.neuralFilterInterestIds.every((v, i) => v === b.neuralFilterInterestIds[i])
    );
  }

  function isGraphFiltered() {
    return Boolean(
      state.focusNodeKey ||
        state.orgFilter ||
        !state.neuralShowOrgs ||
        !state.neuralShowEfforts ||
        !state.neuralShowInterests ||
        state.neuralFilterOrgIds.length > 0 ||
        state.neuralFilterInterestIds.length > 0
    );
  }

  function syncFilterControlsFromState() {
    const setChecked = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.checked = Boolean(val);
    };
    setChecked("neural-toggle-orgs", state.neuralShowOrgs);
    setChecked("neural-toggle-efforts", state.neuralShowEfforts);
    setChecked("neural-toggle-interests", state.neuralShowInterests);

    const viewASel = document.getElementById("view-a-org-filter");
    if (viewASel) viewASel.value = state.orgFilter;

    document.querySelectorAll(".abc-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.mode === state.canvasMode);
    });

    const orgMenu = document.getElementById("neural-org-filter-menu");
    if (orgMenu) {
      const selected = new Set(state.neuralFilterOrgIds);
      orgMenu.querySelectorAll("input[type='checkbox']").forEach((cb) => {
        cb.checked = selected.has(cb.value);
      });
    }
    const intrMenu = document.getElementById("neural-intr-filter-menu");
    if (intrMenu) {
      const selected = new Set(state.neuralFilterInterestIds);
      intrMenu.querySelectorAll("input[type='checkbox']").forEach((cb) => {
        cb.checked = selected.has(cb.value);
      });
    }

    const orgBtn = document.getElementById("btn-neural-org-filter");
    if (orgBtn) {
      orgBtn.textContent =
        state.neuralFilterOrgIds.length > 0
          ? `Orgs (${state.neuralFilterOrgIds.length}) ▾`
          : "Orgs: All ▾";
    }
    const intrBtn = document.getElementById("btn-neural-intr-filter");
    if (intrBtn) {
      intrBtn.textContent =
        state.neuralFilterInterestIds.length > 0
          ? `Interests (${state.neuralFilterInterestIds.length}) ▾`
          : "Interests: All ▾";
    }
  }

  function renderBreadcrumbBar() {
    const bar = document.getElementById("canvas-breadcrumb-bar");
    const trail = document.getElementById("breadcrumb-trail");
    const backBtn = document.getElementById("btn-breadcrumb-back");
    if (!bar || !trail) return;

    const showBar = isGraphFiltered() || historyIndex > 0;
    bar.classList.toggle("hidden", !showBar);
    if (backBtn) backBtn.disabled = historyIndex <= 0;

    if (!showBar) {
      trail.innerHTML = "";
      return;
    }

    const { escapeHtml } = global.BijouApi;
    trail.innerHTML = filterHistory
      .map((entry, idx) => {
        const sep = idx > 0 ? '<span class="crumb-sep">›</span>' : "";
        const activeCls = idx === historyIndex ? " active" : "";
        return `${sep}<button type="button" class="crumb-btn${activeCls}" data-crumb-idx="${idx}">${escapeHtml(entry.label)}</button>`;
      })
      .join("");

    trail.querySelectorAll(".crumb-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.dataset.crumbIdx, 10);
        if (!Number.isNaN(idx) && idx >= 0 && idx < filterHistory.length) {
          jumpToHistoryIndex(idx);
        }
      });
    });
  }

  function pushFilterHistory(label) {
    const snap = captureFilterSnapshot();
    if (filterHistory.length === 0) {
      filterHistory = [{ label: "Full Graph", snapshot: snap }];
      historyIndex = 0;
    } else if (!snapshotsEqual(filterHistory[historyIndex].snapshot, snap)) {
      filterHistory = filterHistory.slice(0, historyIndex + 1);
      filterHistory.push({ label, snapshot: snap });
      if (filterHistory.length > 24) {
        filterHistory.shift();
      }
      historyIndex = filterHistory.length - 1;
    }
    syncFilterControlsFromState();
    renderBreadcrumbBar();
  }

  async function jumpToHistoryIndex(idx) {
    const entry = filterHistory[idx];
    if (!entry) return;
    historyIndex = idx;
    const prevOrgFilter = state.orgFilter;
    const snap = entry.snapshot;

    state.canvasMode = snap.canvasMode;
    state.orgFilter = snap.orgFilter;
    state.focusNodeKey = snap.focusNodeKey;
    state.focusLabel = snap.focusLabel;
    state.neuralShowOrgs = snap.neuralShowOrgs;
    state.neuralShowEfforts = snap.neuralShowEfforts;
    state.neuralShowInterests = snap.neuralShowInterests;
    state.neuralFilterOrgIds = [...snap.neuralFilterOrgIds];
    state.neuralFilterInterestIds = [...snap.neuralFilterInterestIds];

    syncFilterControlsFromState();
    renderBreadcrumbBar();
    if (prevOrgFilter !== state.orgFilter) {
      await refreshAllData();
    } else {
      renderCanvasStage();
    }
  }

  async function stepBackFilter() {
    if (historyIndex > 0) {
      await jumpToHistoryIndex(historyIndex - 1);
    }
  }

  async function resetAllFilters() {
    const hadOrgScope = Boolean(state.orgFilter);
    state.orgFilter = "";
    state.focusNodeKey = null;
    state.focusLabel = "";
    state.neuralShowOrgs = true;
    state.neuralShowEfforts = true;
    state.neuralShowInterests = true;
    state.neuralFilterOrgIds = [];
    state.neuralFilterInterestIds = [];

    filterHistory = [{ label: "Full Graph", snapshot: captureFilterSnapshot() }];
    historyIndex = 0;
    syncFilterControlsFromState();
    renderBreadcrumbBar();

    if (hadOrgScope) {
      await refreshAllData();
    } else {
      renderCanvasStage();
    }
    notify("Graph filters reset to full view.", "info");
  }

  function populateFilterPopovers(orgs, interests) {
    const { escapeHtml } = global.BijouApi;

    const buildMenu = (menuId, title, items, currentIds, onChange) => {
      const menu = document.getElementById(menuId);
      if (!menu) return;
      const selected = new Set(currentIds);
      const sorted = [...(items || [])].sort((a, b) => a.name.localeCompare(b.name));
      menu.innerHTML = `
        <div class="filter-popover-header">
          <span>${escapeHtml(title)}</span>
          <button type="button" class="btn btn-ghost btn-xs filter-clear-btn">Clear</button>
        </div>
        <div class="filter-popover-list">
          ${sorted
            .map(
              (item) => `
            <label class="filter-popover-item">
              <input type="checkbox" value="${escapeHtml(item.id)}" ${selected.has(item.id) ? "checked" : ""} />
              <span>${escapeHtml(item.name)}</span>
            </label>`
            )
            .join("")}
        </div>
      `;

      menu.querySelector(".filter-clear-btn")?.addEventListener("click", () => {
        onChange([]);
      });
      menu.querySelectorAll("input[type='checkbox']").forEach((cb) => {
        cb.addEventListener("change", () => {
          const next = Array.from(menu.querySelectorAll("input[type='checkbox']:checked")).map((el) => el.value);
          onChange(next);
        });
      });
    };

    buildMenu("neural-org-filter-menu", "Filter by Organization", orgs, state.neuralFilterOrgIds, (next) => {
      state.neuralFilterOrgIds = next;
      pushFilterHistory(next.length ? `Orgs (${next.length})` : "All Orgs");
      renderCanvasStage();
    });

    buildMenu(
      "neural-intr-filter-menu",
      "Filter by Interest / Goal",
      interests,
      state.neuralFilterInterestIds,
      (next) => {
        state.neuralFilterInterestIds = next;
        pushFilterHistory(next.length ? `Interests (${next.length})` : "All Interests");
        renderCanvasStage();
      }
    );

    syncFilterControlsFromState();
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
  let graphEditor = null;

  function renderCanvasStage() {
    const svgEl = document.getElementById("canvas-svg-layer");
    const domEl = document.getElementById("canvas-dom-layer");
    const worldEl = document.getElementById("canvas-world");
    const aOverlays = document.getElementById("view-a-overlay-wrap");
    const bOverlays = document.getElementById("view-b-overlay-wrap");
    const neuralOverlays = document.getElementById("view-neural-overlay-wrap");

    const impactedIds = state.simulationResult?.impacted_effort_ids || [];
    const activeTree = state.simulationResult?.projected_tree || state.treeView;
    const activeTri = state.simulationResult?.projected_tree
      ? {
          ...state.triView,
          capability_tree: state.simulationResult.projected_tree,
          pool_balances: state.simulationResult.pool_balances || state.triView?.pool_balances,
        }
      : state.triView;

    if (state.canvasMode === "B") {
      aOverlays?.classList.add("hidden");
      bOverlays?.classList.remove("hidden");
      neuralOverlays?.classList.add("hidden");
      global.BijouViewB.renderViewBTripartite({
        triView: activeTri,
        svgEl,
        domEl,
        worldEl,
        showIndirect: state.showIndirect,
        showPartners: state.showPartners,
        focusNodeKey: state.focusNodeKey,
        impactedIds,
        onSelectEntity: (kind, id) => puckController.open(kind, id, buildViewParams()),
      });
    } else if (state.canvasMode === "NEURAL") {
      aOverlays?.classList.add("hidden");
      bOverlays?.classList.add("hidden");
      neuralOverlays?.classList.remove("hidden");
      global.BijouViewNeural.renderGlobalNeuralGraph({
        triView: activeTri,
        svgEl,
        domEl,
        worldEl,
        showStructural: state.neuralShowStructural,
        showIndirect: state.neuralShowIndirect,
        showOrgs: state.neuralShowOrgs,
        showEfforts: state.neuralShowEfforts,
        showInterests: state.neuralShowInterests,
        filterOrgIds: state.neuralFilterOrgIds,
        filterInterestIds: state.neuralFilterInterestIds,
        focusNodeKey: state.focusNodeKey,
        impactedIds,
        zoom: state.zoom,
        onSelectEntity: (kind, id) => puckController.open(kind, id, buildViewParams()),
      });
    } else {
      aOverlays?.classList.remove("hidden");
      bOverlays?.classList.add("hidden");
      neuralOverlays?.classList.add("hidden");
      global.BijouViewA.renderViewADag({
        treeView: activeTree,
        svgEl,
        domEl,
        worldEl,
        clusterBy: state.clusterBy,
        focusNodeKey: state.focusNodeKey,
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

      const orgs = tri.capability_tree?.organizations || tree.organizations || [];
      const interests = tri.capability_tree?.interests || tree.interests || [];

      // Populate top Org Scope filter in View A
      const orgFilterSel = document.getElementById("view-a-org-filter");
      if (orgFilterSel) {
        const { escapeHtml } = global.BijouApi;
        const prev = state.orgFilter;
        orgFilterSel.innerHTML =
          `<option value="">All Organizations</option>` +
          orgs.map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)}</option>`).join("");
        orgFilterSel.value = prev;
        briefingController.setOrganizations(orgs);
      }

      populateFilterPopovers(orgs, interests);
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
      if (e.button !== 0) return;
      if (e.target.closest(".effort-card, .tri-node, .neural-node, .node-connect-port, button, input, select")) return;
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

  function setupWheelZoom() {
    const viewport = document.getElementById("canvas-viewport");
    if (!viewport) return;
    viewport.addEventListener(
      "wheel",
      (ev) => {
        if (ev.target.closest(".filter-popover-menu, .graph-context-menu")) return;
        ev.preventDefault();
        const oldZoom = state.zoom;
        const factor = ev.deltaY < 0 ? 1.1 : 1 / 1.1;
        const nextZoom = Math.min(2.0, Math.max(0.35, Number((oldZoom * factor).toFixed(3))));
        if (Math.abs(nextZoom - oldZoom) < 0.001) return;

        const rect = viewport.getBoundingClientRect();
        const cursorX = ev.clientX - rect.left;
        const cursorY = ev.clientY - rect.top;
        const worldX = (viewport.scrollLeft + cursorX) / oldZoom;
        const worldY = (viewport.scrollTop + cursorY) / oldZoom;

        state.zoom = nextZoom;
        applyZoom();

        viewport.scrollLeft = Math.max(0, worldX * nextZoom - cursorX);
        viewport.scrollTop = Math.max(0, worldY * nextZoom - cursorY);
      },
      { passive: false }
    );
  }

  async function boot() {
    filterHistory = [{ label: "Full Graph", snapshot: captureFilterSnapshot() }];
    historyIndex = 0;

    dockController = new global.BillOfEffortsDock({
      notify,
      onSimulationUpdated: (simRes) => {
        state.simulationResult = simRes;
        renderCanvasStage();
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

    graphEditor = new global.BijouGraphEditor({
      notify,
      getSnapshot: () => ({
        treeView: state.treeView,
        triView: state.triView,
        zoom: state.zoom,
        canvasMode: state.canvasMode,
      }),
      onGraphMutated: async () => {
        await initPerspectiveDropdown();
        await refreshAllData();
      },
      onInspectEntity: (kind, id) => puckController.open(kind, id, buildViewParams()),
      onFocusNode: (entity) => {
        const prefix = entity.kind === "organization" ? "org" : entity.kind;
        state.focusNodeKey = `${prefix}:${entity.id}`;
        state.focusLabel = entity.label || entity.id;
        pushFilterHistory(`Isolate: ${state.focusLabel}`);
        renderCanvasStage();
      },
      onResetGraph: () => resetAllFilters(),
      isFiltered: () => isGraphFiltered(),
      onStageSlip: (effortId, days) => {
        switchLens("canvas");
        dockController.stageSlipShock(effortId, days);
      },
      onOpenCart: () => dockController.setOpen(true),
      onOpenStudio: async (tab, id) => {
        switchLens("studio");
        await studioController.refresh();
        if (tab === "efforts") studioController.openEffortForEdit(id);
      },
    });

    // Wire Lens Navigation
    document.querySelectorAll(".lens-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchLens(btn.dataset.lens));
    });

    // Wire Canvas View Switcher
    document.querySelectorAll(".abc-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchCanvasMode(btn.dataset.mode));
    });

    // Wire Breadcrumb Back & Reset Controls
    document.getElementById("btn-breadcrumb-back")?.addEventListener("click", () => stepBackFilter());
    document.getElementById("btn-breadcrumb-reset")?.addEventListener("click", () => resetAllFilters());

    // Wire Filter Popover Toggles
    const orgMenu = document.getElementById("neural-org-filter-menu");
    const intrMenu = document.getElementById("neural-intr-filter-menu");
    document.getElementById("btn-neural-org-filter")?.addEventListener("click", (ev) => {
      ev.stopPropagation();
      intrMenu?.classList.add("hidden");
      orgMenu?.classList.toggle("hidden");
    });
    document.getElementById("btn-neural-intr-filter")?.addEventListener("click", (ev) => {
      ev.stopPropagation();
      orgMenu?.classList.add("hidden");
      intrMenu?.classList.toggle("hidden");
    });
    document.addEventListener("click", (ev) => {
      if (!ev.target.closest("#neural-org-filter-wrap")) orgMenu?.classList.add("hidden");
      if (!ev.target.closest("#neural-intr-filter-wrap")) intrMenu?.classList.add("hidden");
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
      const selectedName = ev.target.options[ev.target.selectedIndex]?.text || "All Organizations";
      pushFilterHistory(state.orgFilter ? `Org: ${selectedName}` : "All Orgs");
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

    document.getElementById("neural-toggle-orgs")?.addEventListener("change", (ev) => {
      state.neuralShowOrgs = Boolean(ev.target.checked);
      pushFilterHistory(state.neuralShowOrgs ? "Show Orgs" : "Hide Orgs");
      renderCanvasStage();
    });

    document.getElementById("neural-toggle-efforts")?.addEventListener("change", (ev) => {
      state.neuralShowEfforts = Boolean(ev.target.checked);
      pushFilterHistory(state.neuralShowEfforts ? "Show Efforts" : "Hide Efforts");
      renderCanvasStage();
    });

    document.getElementById("neural-toggle-interests")?.addEventListener("change", (ev) => {
      state.neuralShowInterests = Boolean(ev.target.checked);
      pushFilterHistory(state.neuralShowInterests ? "Show Interests" : "Hide Interests");
      renderCanvasStage();
    });

    document.getElementById("view-neural-show-structural")?.addEventListener("change", (ev) => {
      state.neuralShowStructural = Boolean(ev.target.checked);
      renderCanvasStage();
    });

    document.getElementById("view-neural-show-indirect")?.addEventListener("change", (ev) => {
      state.neuralShowIndirect = Boolean(ev.target.checked);
      renderCanvasStage();
    });

    document.getElementById("btn-neural-relayout")?.addEventListener("click", () => {
      global.BijouViewNeural.resetLayout();
      renderCanvasStage();
      notify("Recomputed non-overlapping Global Neural Graph layout.", "info");
    });

    // Dock Toggle & Zoom
    document.getElementById("btn-toggle-dock")?.addEventListener("click", () => {
      dockController.setOpen(!dockController.isOpen());
    });
    document.getElementById("btn-close-dock")?.addEventListener("click", () => {
      dockController.setOpen(false);
    });

    document.getElementById("btn-zoom-in")?.addEventListener("click", () => {
      state.zoom = Math.min(2.0, state.zoom + 0.15);
      applyZoom();
    });
    document.getElementById("btn-zoom-out")?.addEventListener("click", () => {
      state.zoom = Math.max(0.35, state.zoom - 0.15);
      applyZoom();
    });
    document.getElementById("btn-zoom-reset")?.addEventListener("click", () => {
      state.zoom = 1.0;
      applyZoom();
    });

    setupPanning();
    setupWheelZoom();
    await initPerspectiveDropdown();
    await refreshAllData();
  }

  document.addEventListener("DOMContentLoaded", boot);
})(window);
