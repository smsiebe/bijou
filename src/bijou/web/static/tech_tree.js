/**
 * 4X Game-Style Tech Tree Canvas & What-If Slip Simulator.
 * Features:
 * - 2D Matrix Grid (X: Tiers, Y: Swimlanes)
 * - Infinite Canvas Pan & Zoom
 * - SPOF & CPM Slack Topological Badges & Outlines
 * - Upstream Critical Path Spine Highlighting
 */

const TechTreeManager = {
  currentViewData: null,
  selectedMilestoneId: null,
  panX: 0,
  panY: 0,
  scale: 1.0,
  isPanning: false,
  panStartX: 0,
  panStartY: 0,

  async init() {
    this.bindControls();
    this.initCanvasInteractions();
    await this.refresh();
  },

  bindControls() {
    const modeSelect = document.getElementById("stratification-mode-select");
    if (modeSelect) {
      modeSelect.addEventListener("change", () => this.refresh());
    }

    const orgFilterSelect = document.getElementById("tech-tree-org-filter");
    if (orgFilterSelect) {
      orgFilterSelect.addEventListener("change", () => this.refresh());
    }

    const applySlipBtn = document.getElementById("apply-slip-btn");
    if (applySlipBtn) {
      applySlipBtn.addEventListener("click", () => this.executeSlipSimulation());
    }

    const cancelDrawerBtn = document.getElementById("close-drawer-btn");
    if (cancelDrawerBtn) {
      cancelDrawerBtn.addEventListener("click", () => {
        document.getElementById("slip-drawer").classList.remove("open");
      });
    }

    const resetCanvasBtn = document.getElementById("reset-canvas-btn");
    if (resetCanvasBtn) {
      resetCanvasBtn.addEventListener("click", () => {
        this.panX = 0;
        this.panY = 0;
        this.scale = 1.0;
        this.applyTransform();
      });
    }

    const commitDecisionBtn = document.getElementById("commit-decision-btn");
    if (commitDecisionBtn) {
      commitDecisionBtn.addEventListener("click", () => this.commitDecisionLog());
    }
  },

  initCanvasInteractions() {
    const wrapper = document.querySelector(".tech-tree-canvas-wrapper");
    if (!wrapper || wrapper.dataset.panZoomBound) return;
    wrapper.dataset.panZoomBound = "true";

    wrapper.addEventListener("mousedown", (e) => {
      // Don't pan if clicking an interactive node card or control
      if (e.target.closest(".node-card") || e.target.closest("button") || e.target.closest("select")) {
        return;
      }
      this.isPanning = true;
      this.panStartX = e.clientX - this.panX;
      this.panStartY = e.clientY - this.panY;
      wrapper.style.cursor = "grabbing";
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isPanning) return;
      this.panX = e.clientX - this.panStartX;
      this.panY = e.clientY - this.panStartY;
      this.applyTransform();
    });

    window.addEventListener("mouseup", () => {
      if (this.isPanning) {
        this.isPanning = false;
        wrapper.style.cursor = "grab";
      }
    });

    wrapper.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomDelta = e.deltaY < 0 ? 1.08 : 0.92;
      this.scale = Math.min(Math.max(this.scale * zoomDelta, 0.4), 2.5);
      this.applyTransform();
    }, { passive: false });
  },

  applyTransform() {
    const grid = document.getElementById("tech-tree-grid-target");
    if (grid) {
      grid.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
    }
  },

  async refresh() {
    const modeSelect = document.getElementById("stratification-mode-select");
    const mode = modeSelect ? modeSelect.value : "TRL_TIERS";
    const orgFilterSelect = document.getElementById("tech-tree-org-filter");
    const orgFilter = orgFilterSelect && orgFilterSelect.value ? orgFilterSelect.value : null;

    try {
      this.currentViewData = await BijouAPI.getTechTree(mode, null, orgFilter);
      this.render();
    } catch (err) {
      console.error("Error loading tech tree:", err);
    }
  },

  render() {
    const canvas = document.getElementById("tech-tree-grid-target");
    if (!canvas || !this.currentViewData) return;
    canvas.innerHTML = "";

    const { tiers, nodes, edges, lanes } = this.currentViewData;

    // Collect swimlanes
    const laneList = (lanes && lanes.length > 0)
      ? lanes
      : Array.from(new Set(nodes.map(n => n.lane_id))).sort().map(l => ({ lane_id: l, lane_name: l }));

    // Container for 2D Matrix (X: Tiers, Y: Lanes)
    const gridEl = document.createElement("div");
    gridEl.className = "matrix-2d-canvas";
    gridEl.style.display = "flex";
    gridEl.style.flexDirection = "column";
    gridEl.style.gap = "18px";
    gridEl.style.position = "relative";
    gridEl.style.minWidth = "max-content";

    // Header Row: Lane placeholder + Tier Columns
    const headerRow = document.createElement("div");
    headerRow.className = "matrix-header-row";
    headerRow.style.gridTemplateColumns = `160px repeat(${tiers.length}, minmax(260px, 1fr))`;

    const cornerCell = document.createElement("div");
    cornerCell.className = "lane-header-cell";
    cornerCell.style.background = "transparent";
    cornerCell.style.border = "none";
    cornerCell.innerHTML = `<span style="color: var(--text-dim); font-size: 0.75rem;">SWIMLANE \\ TIER</span>`;
    headerRow.appendChild(cornerCell);

    tiers.forEach(tier => {
      const tierH = document.createElement("div");
      tierH.className = "column-header";
      tierH.textContent = tier.tier_name || `Tier ${tier.order}`;
      headerRow.appendChild(tierH);
    });
    gridEl.appendChild(headerRow);

    // Group nodes by (lane_id, tier_order)
    const nodeMatrix = {};
    laneList.forEach(l => {
      nodeMatrix[l.lane_id] = {};
      tiers.forEach(t => {
        nodeMatrix[l.lane_id][t.order] = [];
      });
    });

    nodes.forEach(n => {
      const laneKey = n.lane_id || "Default";
      if (!nodeMatrix[laneKey]) {
        nodeMatrix[laneKey] = {};
        tiers.forEach(t => { nodeMatrix[laneKey][t.order] = []; });
      }
      if (nodeMatrix[laneKey][n.tier_order]) {
        nodeMatrix[laneKey][n.tier_order].push(n);
      }
    });

    // Render each swimlane as a 2D matrix row
    laneList.forEach(lane => {
      const row = document.createElement("div");
      row.className = "matrix-lane-row";
      row.style.gridTemplateColumns = `160px repeat(${tiers.length}, minmax(260px, 1fr))`;

      const laneLabel = document.createElement("div");
      laneLabel.className = "lane-header-cell";
      laneLabel.innerHTML = `<span>${lane.lane_name || lane.lane_id}</span>`;
      row.appendChild(laneLabel);

      tiers.forEach(tier => {
        const cell = document.createElement("div");
        cell.className = "matrix-cell";
        cell.dataset.laneId = lane.lane_id;
        cell.dataset.tierOrder = tier.order;

        const cellNodes = (nodeMatrix[lane.lane_id] && nodeMatrix[lane.lane_id][tier.order]) || [];
        cellNodes.forEach(node => {
          const card = document.createElement("div");
          const stateClass = `state-${node.state.toLowerCase().replace('_', '-')}`;
          const spofClass = node.is_spof ? "node-spof" : "";
          const slackClass = node.slack_days === 0 ? "slack-zero" : "";
          card.className = `node-card ${stateClass} ${spofClass} ${slackClass}`.trim();
          card.dataset.nodeId = node.node_id;
          card.dataset.milestoneId = node.milestone_id;

          const spofBadge = node.is_spof ? `<span class="spof-badge">[SPOF]</span>` : "";
          const slackStyle = node.slack_days === 0 ? "slack-critical" : "slack-safe";
          const slackBadge = `<span class="slack-badge ${slackStyle}">Slack: ${node.slack_days}d</span>`;

          card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div class="node-title">${node.title}</div>
              ${spofBadge}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 2px;">${node.thing_name}</div>
            <div class="node-meta" style="margin-top: 8px;">
              <span>TRL ${node.trl}</span>
              <span>$${(node.cost_estimate / 1000).toFixed(0)}k</span>
              ${slackBadge}
              <span>${node.state}</span>
            </div>
          `;

          card.addEventListener("click", (e) => {
            e.stopPropagation();
            if (window.ThingPuck) {
              window.ThingPuck.open(node, e);
            } else {
              this.openSlipDrawer(node);
            }
          });
          card.addEventListener("contextmenu", (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (window.ThingPuck) {
              window.ThingPuck.open(node, e);
            } else {
              this.showContextMenu(node, e);
            }
          });
          card.addEventListener("mouseenter", () => this.highlightSpine(node.node_id));
          card.addEventListener("mouseleave", () => this.clearSpineHighlight());

          cell.appendChild(card);
        });

        row.appendChild(cell);
      });

      gridEl.appendChild(row);
    });

    canvas.appendChild(gridEl);

    // Render SVG overlay connecting dependency edges
    this.renderEdges(gridEl, edges || []);
  },

  renderEdges(canvas, edges) {
    const existingSvg = canvas.querySelector(".tech-tree-svg-overlay");
    if (existingSvg) existingSvg.remove();

    if (!edges || edges.length === 0) return;

    const canvasRect = canvas.getBoundingClientRect();
    const svgNS = "http://www.w3.org/2000/svg";
    const svgEl = document.createElementNS(svgNS, "svg");
    svgEl.setAttribute("class", "tech-tree-svg-overlay");
    svgEl.setAttribute("style", "position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;");

    edges.forEach(edge => {
      const sEl = canvas.querySelector(`[data-node-id="${edge.source_node_id}"]`);
      const tEl = canvas.querySelector(`[data-node-id="${edge.target_node_id}"]`);
      if (!sEl || !tEl) return;

      const sRect = sEl.getBoundingClientRect();
      const tRect = tEl.getBoundingClientRect();

      const scale = this.scale || 1.0;
      const x1 = (sRect.right - canvasRect.left) / scale;
      const y1 = (sRect.top + sRect.height / 2 - canvasRect.top) / scale;
      const x2 = (tRect.left - canvasRect.left) / scale;
      const y2 = (tRect.top + tRect.height / 2 - canvasRect.top) / scale;

      const midX = (x1 + x2) / 2;
      const d = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;
      const strokeColor = edge.is_satisfied ? "#10b981" : "#475569";
      const strokeWidth = edge.is_critical_path ? "3px" : "2px";

      const pathEl = document.createElementNS(svgNS, "path");
      pathEl.setAttribute("d", d);
      pathEl.setAttribute("class", "tech-tree-edge-path");
      pathEl.setAttribute("data-source-node-id", edge.source_node_id);
      pathEl.setAttribute("data-target-node-id", edge.target_node_id);
      pathEl.setAttribute("data-edge-id", edge.edge_id);
      pathEl.setAttribute("data-default-stroke", strokeColor);
      pathEl.setAttribute("data-default-width", strokeWidth);
      pathEl.setAttribute("stroke", strokeColor);
      pathEl.setAttribute("stroke-width", strokeWidth);
      pathEl.setAttribute("fill", "none");
      pathEl.setAttribute("opacity", "0.6");

      svgEl.appendChild(pathEl);
    });

    canvas.appendChild(svgEl);
  },

  openSlipDrawer(node) {
    this.selectedMilestoneId = node.milestone_id;
    const drawer = document.getElementById("slip-drawer");
    const titleEl = document.getElementById("drawer-milestone-title");
    const thingEl = document.getElementById("drawer-thing-name");
    const stateEl = document.getElementById("drawer-current-state");

    if (titleEl) titleEl.textContent = node.title;
    if (thingEl) thingEl.textContent = node.thing_name;
    if (stateEl) stateEl.textContent = node.state;

    const resultBox = document.getElementById("slip-simulation-results");
    if (resultBox) resultBox.innerHTML = "";

    drawer.classList.add("open");
    this.loadDecisionLogs(node.milestone_id);
  },

  async loadDecisionLogs(milestoneId) {
    const logsContainer = document.getElementById("drawer-decision-logs");
    if (!logsContainer) return;
    logsContainer.innerHTML = `<div style="color: var(--text-dim); font-size: 0.75rem;">Loading decision provenance...</div>`;
    try {
      const logs = await BijouAPI.getDecisionLogs(milestoneId);
      if (!logs || logs.length === 0) {
        logsContainer.innerHTML = `<div style="color: var(--text-dim); font-size: 0.75rem;">No strategic decisions logged for this milestone.</div>`;
        return;
      }
      logsContainer.innerHTML = logs.map(l => `
        <div style="background: var(--bg-card); border-left: 2px solid var(--accent-cyan); padding: 6px 8px; border-radius: 3px; font-size: 0.75rem;">
          <div style="display: flex; justify-content: space-between; color: var(--text-muted); font-size: 0.7rem;">
            <strong>${l.author}</strong>
            <span style="font-family: var(--font-mono);">${new Date(l.timestamp).toLocaleDateString()}</span>
          </div>
          <div style="color: var(--text-main); margin-top: 3px; font-style: italic;">"${l.justification}"</div>
        </div>
      `).join("");
    } catch (err) {
      logsContainer.innerHTML = `<div style="color: var(--color-blocked); font-size: 0.75rem;">Error loading decision logs: ${err.message}</div>`;
    }
  },

  async commitDecisionLog() {
    if (!this.selectedMilestoneId) {
      alert("No milestone currently selected.");
      return;
    }
    const authorInput = document.getElementById("decision-author");
    const justInput = document.getElementById("decision-justification");
    const author = authorInput ? authorInput.value.trim() : "";
    const justification = justInput ? justInput.value.trim() : "";

    if (!author || !justification) {
      alert("Both Author and Strategic Justification are required to record a decision.");
      return;
    }

    try {
      await BijouAPI.createDecisionLog({
        target_milestone_id: this.selectedMilestoneId,
        author,
        justification
      });
      if (justInput) justInput.value = "";
      await this.loadDecisionLogs(this.selectedMilestoneId);
    } catch (err) {
      alert("Failed to commit decision: " + err.message);
    }
  },

  async executeSlipSimulation() {
    if (!this.selectedMilestoneId) return;

    const daysInput = document.getElementById("slip-days-slider");
    const cancelCheckbox = document.getElementById("simulate-cancellation-checkbox");
    const slipDays = parseInt(daysInput ? daysInput.value : "60", 10);
    const cancel = cancelCheckbox ? cancelCheckbox.checked : false;

    try {
      const resp = await BijouAPI.simulateSlip(this.selectedMilestoneId, slipDays, cancel);
      const resultBox = document.getElementById("slip-simulation-results");
      if (resultBox) {
        resultBox.innerHTML = `
          <div style="margin-top: 16px; padding: 12px; background: var(--bg-card); border-radius: 6px;">
            <div style="font-weight: 700; color: ${resp.roi_delta < 0 ? 'var(--color-blocked)' : 'var(--color-achieved)'};">
              ROI Delta: ${resp.roi_delta}
            </div>
            <div style="font-size: 0.8rem; margin-top: 8px;">
              <strong>Impacted Nodes:</strong> ${Object.keys(resp.impacted_node_states).length}
            </div>
            <div style="font-size: 0.8rem;">
              <strong>Degraded Effects:</strong> ${resp.degraded_effect_ids.join(', ') || 'None'}
            </div>
            <div style="font-size: 0.8rem;">
              <strong>Broken Concerns:</strong> ${resp.broken_concern_ids.join(', ') || 'None'}
            </div>
          </div>
        `;
      }
    } catch (err) {
      alert("Slip simulation failed: " + err.message);
    }
  },

  highlightSpine(nodeId) {
    if (!this.currentViewData || !this.currentViewData.edges) return;

    // Collect all upstream ancestor nodes recursively
    const ancestorIds = new Set([nodeId]);
    const queue = [nodeId];

    while (queue.length > 0) {
      const currentId = queue.shift();
      for (const edge of this.currentViewData.edges) {
        if (edge.target_node_id === currentId) {
          if (!ancestorIds.has(edge.source_node_id)) {
            ancestorIds.add(edge.source_node_id);
            queue.push(edge.source_node_id);
          }
        }
      }
    }

    // Highlight ancestor nodes and dim non-ancestors
    const cards = document.querySelectorAll(".node-card");
    cards.forEach(card => {
      const cardNodeId = card.dataset.nodeId;
      if (ancestorIds.has(cardNodeId)) {
        card.style.opacity = "1.0";
        card.style.filter = "drop-shadow(0 0 8px rgba(56, 189, 248, 0.6))";
      } else {
        card.style.opacity = "0.2";
        card.style.filter = "none";
      }
    });

    // Highlight connecting SVG paths
    const paths = document.querySelectorAll(".tech-tree-edge-path");
    paths.forEach(p => {
      const sId = p.dataset.sourceNodeId;
      const tId = p.dataset.targetNodeId;
      if (ancestorIds.has(sId) && ancestorIds.has(tId)) {
        p.style.opacity = "1.0";
        p.style.stroke = "var(--accent-cyan)";
        p.style.strokeWidth = "3px";
      } else {
        p.style.opacity = "0.1";
      }
    });
  },

  clearSpineHighlight() {
    const cards = document.querySelectorAll(".node-card");
    cards.forEach(card => {
      card.style.opacity = "1.0";
      card.style.filter = "none";
    });

    const paths = document.querySelectorAll(".tech-tree-edge-path");
    paths.forEach(p => {
      p.style.opacity = "0.6";
      p.style.stroke = p.dataset.defaultStroke || "#475569";
      p.style.strokeWidth = p.dataset.defaultWidth || "2px";
    });
  }

  showContextMenu(node, e) {
    let menu = document.getElementById("node-context-menu");
    if (!menu) {
      menu = document.createElement("div");
      menu.id = "node-context-menu";
      menu.className = "context-menu";
      document.body.appendChild(menu);

      document.addEventListener("click", () => {
        menu.classList.remove("open");
      });
    }

    menu.innerHTML = `
      <div class="context-menu-header">${node.thing_name || node.title}</div>
      <button class="context-menu-item" id="ctx-open-puck">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>
        Inspect Detail Puck (HUD)
      </button>
      <button class="context-menu-item" id="ctx-open-slip">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        What-If Slip Simulator
      </button>
      <button class="context-menu-item" id="ctx-open-spheres">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        Spheres of Ownership Lens
      </button>
      <button class="context-menu-item" id="ctx-open-spheres-modal">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="5"/></svg>
        Spheres In-Canvas Modal
      </button>
      <button class="context-menu-item" id="ctx-open-focal">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3"/></svg>
        Focal Ego Dashboard
      </button>
    `;

    menu.style.left = `${Math.min(e.clientX, window.innerWidth - 220)}px`;
    menu.style.top = `${Math.min(e.clientY, window.innerHeight - 200)}px`;
    menu.classList.add("open");

    const btnPuck = menu.querySelector("#ctx-open-puck");
    if (btnPuck) {
      btnPuck.addEventListener("click", () => {
        menu.classList.remove("open");
        if (window.ThingPuck) window.ThingPuck.open(node, e);
      });
    }

    const btnSlip = menu.querySelector("#ctx-open-slip");
    if (btnSlip) {
      btnSlip.addEventListener("click", () => {
        menu.classList.remove("open");
        this.openSlipDrawer(node);
      });
    }

    const btnSpheres = menu.querySelector("#ctx-open-spheres");
    if (btnSpheres) {
      btnSpheres.addEventListener("click", () => {
        menu.classList.remove("open");
        if (window.SpheresManager) window.SpheresManager.show({ focusThingId: node.thing_id });
      });
    }

    const btnModal = menu.querySelector("#ctx-open-spheres-modal");
    if (btnModal) {
      btnModal.addEventListener("click", () => {
        menu.classList.remove("open");
        if (window.SpheresManager) window.SpheresManager.show({ focusThingId: node.thing_id, asModal: true });
      });
    }

    const btnFocal = menu.querySelector("#ctx-open-focal");
    if (btnFocal) {
      btnFocal.addEventListener("click", () => {
        menu.classList.remove("open");
        const lensBtn = document.querySelector('.lens-btn[data-lens="focal-dashboard"]');
        if (lensBtn) lensBtn.click();
        const focalSelect = document.getElementById("focal-thing-select");
        if (focalSelect && node.thing_id) {
          focalSelect.value = node.thing_id;
          if (window.ViewsManager) window.ViewsManager.refreshFocal();
        }
      });
    }
  }
};

window.TechTreeManager = TechTreeManager;
