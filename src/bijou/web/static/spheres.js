/**
 * Clustered "Spheres of Ownership" Graph View.
 * Visualizes Things clustered within Organization ownership boundaries (spheres),
 * with prominent glowing cross-cutting dependency vectors spanning across organizations.
 * Supports:
 * - Dedicated Top-Level Lens (Lens 5)
 * - In-Canvas Modal Overlay for Contextual Inspection
 * - View Toggle: Thing-to-Thing with Org Spheres vs Org-to-Org Macro Rollup
 * - Infinite Canvas Pan & Zoom
 * - Interactive Cross-Cutting Vector Highlighting
 * - Direct click integration with ThingPuck
 */

const SpheresManager = {
  data: null,
  viewMode: "things", // "things" or "macro_orgs"
  panX: 0,
  panY: 0,
  scale: 1.0,
  isPanning: false,
  panStartX: 0,
  panStartY: 0,
  selectedOrgId: null,
  selectedThingId: null,

  async init() {
    this.bindControls();
    this.initCanvasPanZoom();
  },

  bindControls() {
    // Top-level lens controls
    const orgSelect = document.getElementById("spheres-org-filter");
    if (orgSelect) {
      orgSelect.addEventListener("change", (e) => {
        this.selectedOrgId = e.target.value || null;
        this.refresh();
      });
    }

    const modeToggle = document.getElementById("spheres-view-mode-toggle");
    if (modeToggle) {
      modeToggle.addEventListener("change", (e) => {
        this.viewMode = e.target.value;
        this.render();
      });
    }

    const resetBtn = document.getElementById("spheres-reset-pan-zoom");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.panX = 0;
        this.panY = 0;
        this.scale = 1.0;
        this.applyTransform();
      });
    }

    // Modal controls for in-canvas overlay A/B test
    const closeModalBtn = document.getElementById("spheres-modal-close-btn");
    if (closeModalBtn) {
      closeModalBtn.addEventListener("click", () => this.closeModal());
    }
  },

  initCanvasPanZoom() {
    const wrappers = [
      document.getElementById("spheres-canvas-wrapper"),
      document.getElementById("spheres-modal-canvas-wrapper")
    ];

    wrappers.forEach(wrapper => {
      if (!wrapper || wrapper.dataset.panZoomBound) return;
      wrapper.dataset.panZoomBound = "true";

      wrapper.addEventListener("mousedown", (e) => {
        if (e.target.closest(".thing-sphere-node") || e.target.closest(".org-macro-card") || e.target.closest("button") || e.target.closest("select")) {
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
          if (wrapper) wrapper.style.cursor = "grab";
        }
      });

      wrapper.addEventListener("wheel", (e) => {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 1.08 : 0.92;
        this.scale = Math.min(Math.max(this.scale * delta, 0.35), 2.5);
        this.applyTransform();
      }, { passive: false });
    });
  },

  applyTransform() {
    const targets = [
      document.getElementById("spheres-graph-target"),
      document.getElementById("spheres-modal-graph-target")
    ];
    targets.forEach(target => {
      if (target) {
        target.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
        target.style.transformOrigin = "0 0";
      }
    });
    // Re-draw edges after transform to maintain sub-pixel SVG alignment
    this.renderEdges();
  },

  async refresh() {
    const target = document.getElementById("spheres-graph-target");
    if (target && (!this.data || !this.data.clusters)) {
      target.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 420px; color: var(--accent-cyan); font-family: var(--font-mono); gap: 14px;">
          <div style="width: 28px; height: 28px; border: 3px solid var(--accent-cyan); border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
          <span style="font-size: 0.85rem; letter-spacing: 1px;">PROJECTING CAUSAL SPHERES & CROSS-CUTTING GRAPH...</span>
        </div>
      `;
    }

    try {
      const viewData = await BijouAPI.getClusteredSpheres(null, this.selectedOrgId);
      this.data = viewData;
      this.populateOrgDropdown();
      this.render();
    } catch (err) {
      console.error("SpheresManager: refresh failed:", err);
      if (target) {
        target.innerHTML = `<div style="color: var(--color-blocked); padding: 40px; text-align: center; font-weight: 600;">Error projecting Clustered Spheres: ${err.message}</div>`;
      }
    }
  },

  populateOrgDropdown() {
    const orgSelect = document.getElementById("spheres-org-filter");
    if (!orgSelect || !this.data || !this.data.clusters) return;

    const currentVal = orgSelect.value;
    orgSelect.innerHTML = `<option value="">All Organization Spheres (${this.data.clusters.length})</option>` +
      this.data.clusters.map(c => `
        <option value="${c.org_id}" ${c.org_id === currentVal ? "selected" : ""}>
          ${c.org_name} (Echelon ${c.echelon_level} • ${c.thing_ids.length} Things)
        </option>
      `).join("");
  },

  show({ focusThingId = null, focusOrgId = null, asModal = false } = {}) {
    if (focusThingId) this.selectedThingId = focusThingId;
    if (focusOrgId) this.selectedOrgId = focusOrgId;

    if (asModal) {
      const modal = document.getElementById("spheres-modal");
      if (modal) {
        if (typeof modal.showModal === "function") {
          modal.showModal();
        } else {
          modal.setAttribute("open", "");
        }
        this.refresh();
      }
    } else {
      const lensBtn = document.querySelector('.lens-btn[data-lens="spheres-canvas-view"]');
      if (lensBtn) lensBtn.click();
      this.refresh();
    }
  },

  closeModal() {
    const modal = document.getElementById("spheres-modal");
    if (!modal) return;
    if (typeof modal.close === "function") {
      modal.close();
    } else {
      modal.removeAttribute("open");
    }
  },

  render() {
    const target = document.getElementById("spheres-graph-target");
    const modalTarget = document.getElementById("spheres-modal-graph-target");
    if (!this.data) return;

    [target, modalTarget].forEach(container => {
      if (!container) return;
      // Skip modalTarget if dialog is not open
      if (container.id === "spheres-modal-graph-target") {
        const modal = document.getElementById("spheres-modal");
        if (!modal || (!modal.open && !modal.hasAttribute("open"))) return;
      }

      container.innerHTML = "";

      if (this.viewMode === "macro_orgs") {
        this.renderMacroOrgsView(container);
      } else {
        this.renderClusteredSpheresView(container);
      }
    });

    // Draw SVG overlay edges with dual RAF/timeout passes for robust layout sync
    requestAnimationFrame(() => {
      this.renderEdges();
      setTimeout(() => this.renderEdges(), 60);
    });
  },

  // --- MODE A: Thing-to-Thing inside Clustered Org Spheres ---
  renderClusteredSpheresView(container) {
    const { clusters, nodes } = this.data;
    if (!clusters || clusters.length === 0) {
      container.innerHTML = `<div style="padding: 40px; color: var(--text-dim); text-align: center;">No organizations or things available to project.</div>`;
      return;
    }

    const spheresGrid = document.createElement("div");
    spheresGrid.className = "spheres-grid-layout";

    clusters.forEach(cluster => {
      const sphereCard = document.createElement("div");
      sphereCard.className = "org-sphere-bubble";
      sphereCard.dataset.orgId = cluster.org_id;
      sphereCard.style.borderColor = cluster.color || "var(--accent-cyan)";

      const clusterCost = cluster.total_cost >= 1000000
        ? `$${(cluster.total_cost / 1000000).toFixed(1)}M`
        : `$${(cluster.total_cost / 1000).toFixed(0)}k`;

      sphereCard.innerHTML = `
        <div class="sphere-bubble-header" style="border-bottom: 1px solid ${cluster.color || 'var(--border-subtle)'}40;">
          <div>
            <div class="sphere-org-name" style="color: ${cluster.color || 'var(--accent-cyan)'};">${cluster.org_name}</div>
            <div class="sphere-mission-text">${cluster.mission_statement || cluster.org_id}</div>
          </div>
          <div style="text-align: right;">
            <span class="badge-pill" style="border-color: ${cluster.color || 'var(--accent-cyan)'}; color: ${cluster.color || 'var(--accent-cyan)'};">
              Echelon ${cluster.echelon_level}
            </span>
            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">Cost: ${clusterCost}</div>
          </div>
        </div>

        <div class="sphere-nodes-container" data-org-id="${cluster.org_id}"></div>
      `;

      const nodesContainer = sphereCard.querySelector(".sphere-nodes-container");
      const orgNodes = nodes.filter(n => n.cluster_org_id === cluster.org_id);

      if (orgNodes.length === 0) {
        nodesContainer.innerHTML = `<div style="font-size: 0.75rem; color: var(--text-dim); font-style: italic; padding: 12px; text-align: center;">No registered Things in this organization.</div>`;
      } else {
        orgNodes.forEach(node => {
          const nodeCard = document.createElement("div");
          const isSelected = this.selectedThingId === node.thing_id;
          const crossCuttingClass = node.is_cross_cutting ? "cross-cutting-node" : "";
          nodeCard.className = `thing-sphere-node state-${node.lifecycle.toLowerCase().replace('_', '-')} ${crossCuttingClass} ${isSelected ? 'selected' : ''}`;
          nodeCard.dataset.thingId = node.thing_id;
          nodeCard.dataset.orgId = cluster.org_id;

          const crossOrgBadge = node.is_cross_cutting
            ? `<span class="cross-org-sparkle-badge" title="Cuts across organizational boundaries (Cross-Org: ${node.cross_org_partner_ids.join(', ')})">✦ Cross-Org</span>`
            : "";

          nodeCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div class="thing-node-title">${node.name}</div>
              ${crossOrgBadge}
            </div>
            <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">${node.thing_id}</div>
            <div class="thing-node-footer">
              <span class="badge-pill" style="font-size: 0.65rem;">TRL ${node.trl}</span>
              <span style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--accent-amber);">$${(node.estimated_cost / 1000).toFixed(0)}k</span>
              <span class="badge-pill state-${node.lifecycle.toLowerCase().replace('_', '-')}" style="font-size: 0.62rem;">${node.lifecycle}</span>
            </div>
          `;

          // Clicking a Thing opens the Thing Detail Puck!
          nodeCard.addEventListener("click", (e) => {
            e.stopPropagation();
            this.selectedThingId = node.thing_id;
            this.highlightThingConnections(node.thing_id);
            if (window.ThingPuck) {
              window.ThingPuck.open(node.thing_id, e);
            }
          });

          nodeCard.addEventListener("mouseenter", () => {
            this.highlightThingConnections(node.thing_id);
          });

          nodeCard.addEventListener("mouseleave", () => {
            this.clearHighlights();
          });

          nodesContainer.appendChild(nodeCard);
        });
      }

      spheresGrid.appendChild(sphereCard);
    });

    container.appendChild(spheresGrid);
  },

  // --- MODE B: Org-to-Org Macro Rollup ---
  renderMacroOrgsView(container) {
    const { clusters, macro_org_edges } = this.data;
    if (!clusters || clusters.length === 0) return;

    const macroWrapper = document.createElement("div");
    macroWrapper.className = "macro-orgs-grid-layout";

    clusters.forEach(cluster => {
      const card = document.createElement("div");
      card.className = "org-macro-card";
      card.dataset.orgId = cluster.org_id;
      card.style.borderColor = cluster.color || "var(--accent-cyan)";

      const totalCost = cluster.total_cost >= 1000000
        ? `$${(cluster.total_cost / 1000000).toFixed(2)}M`
        : `$${(cluster.total_cost / 1000).toFixed(0)}k`;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div class="macro-org-title" style="color: ${cluster.color || 'var(--accent-cyan)'};">${cluster.org_name}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">${cluster.org_id}</div>
          </div>
          <span class="badge-pill" style="border-color: ${cluster.color || 'var(--accent-cyan)'}; color: ${cluster.color || 'var(--accent-cyan)'};">
            Echelon ${cluster.echelon_level}
          </span>
        </div>
        <div style="margin: 12px 0; font-size: 0.78rem; color: var(--text-muted); font-style: italic;">
          "${cluster.mission_statement || 'Sovereign Command Unit'}"
        </div>
        <div class="macro-stat-row">
          <div>
            <div style="font-size: 0.68rem; color: var(--text-dim); text-transform: uppercase;">Owned Things</div>
            <div style="font-weight: 700; font-size: 1.1rem; color: var(--text-main);">${cluster.thing_ids.length}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.68rem; color: var(--text-dim); text-transform: uppercase;">Total Budget</div>
            <div style="font-weight: 700; font-size: 1.1rem; color: var(--accent-amber);">${totalCost}</div>
          </div>
        </div>
      `;

      card.addEventListener("mouseenter", () => {
        this.highlightOrgConnections(cluster.org_id);
      });

      card.addEventListener("mouseleave", () => {
        this.clearHighlights();
      });

      macroWrapper.appendChild(card);
    });

    container.appendChild(macroWrapper);
  },

  // --- SVG Edge Rendering with Glowing Neon Cross-Cutting Arcs ---
  renderEdges() {
    const targets = [
      document.getElementById("spheres-graph-target"),
      document.getElementById("spheres-modal-graph-target")
    ];

    targets.forEach(container => {
      if (!container || !this.data) return;
      if (container.offsetWidth === 0 && container.offsetHeight === 0) return;

      const existingSvg = container.querySelector(".spheres-svg-overlay");
      if (existingSvg) existingSvg.remove();

      const edgesToRender = this.viewMode === "macro_orgs"
        ? this.data.macro_org_edges || []
        : this.data.edges || [];

      if (edgesToRender.length === 0) return;

      const containerRect = container.getBoundingClientRect();
      const svgNS = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(svgNS, "svg");
      svg.setAttribute("class", "spheres-svg-overlay");
      svg.setAttribute("style", "position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 2; overflow: visible;");

      // Define arrowhead markers
      const defs = document.createElementNS(svgNS, "defs");

      // Internal edge marker
      const markerInternal = document.createElementNS(svgNS, "marker");
      markerInternal.setAttribute("id", "marker-internal");
      markerInternal.setAttribute("viewBox", "0 0 10 10");
      markerInternal.setAttribute("refX", "9");
      markerInternal.setAttribute("refY", "5");
      markerInternal.setAttribute("markerWidth", "6");
      markerInternal.setAttribute("markerHeight", "6");
      markerInternal.setAttribute("orient", "auto-start-reverse");
      markerInternal.innerHTML = `<path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" />`;
      defs.appendChild(markerInternal);

      // Glowing cross-cutting marker
      const markerCross = document.createElementNS(svgNS, "marker");
      markerCross.setAttribute("id", "marker-cross");
      markerCross.setAttribute("viewBox", "0 0 10 10");
      markerCross.setAttribute("refX", "9");
      markerCross.setAttribute("refY", "5");
      markerCross.setAttribute("markerWidth", "7");
      markerCross.setAttribute("markerHeight", "7");
      markerCross.setAttribute("orient", "auto-start-reverse");
      markerCross.innerHTML = `<path d="M 0 0 L 10 5 L 0 10 z" fill="#f59e0b" />`;
      defs.appendChild(markerCross);

      svg.appendChild(defs);

      const scale = this.scale || 1.0;

      if (this.viewMode === "macro_orgs") {
        // Render Macro Org-to-Org vectors
        (this.data.macro_org_edges || []).forEach(edge => {
          const sEl = container.querySelector(`.org-macro-card[data-org-id="${edge.source_org_id}"]`);
          const tEl = container.querySelector(`.org-macro-card[data-org-id="${edge.target_org_id}"]`);
          if (!sEl || !tEl) return;

          const sR = sEl.getBoundingClientRect();
          const tR = tEl.getBoundingClientRect();

          const x1 = (sR.left + sR.width / 2 - containerRect.left) / scale;
          const y1 = (sR.top + sR.height / 2 - containerRect.top) / scale;
          const x2 = (tR.left + tR.width / 2 - containerRect.left) / scale;
          const y2 = (tR.top + tR.height / 2 - containerRect.top) / scale;

          const dx = x2 - x1;
          const dy = y2 - y1;
          const cx = (x1 + x2) / 2 - dy * 0.2;
          const cy = (y1 + y2) / 2 + dx * 0.2;

          const path = document.createElementNS(svgNS, "path");
          path.setAttribute("d", `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`);
          path.setAttribute("class", "macro-org-edge-path");
          path.setAttribute("data-source-org", edge.source_org_id);
          path.setAttribute("data-target-org", edge.target_org_id);
          path.setAttribute("stroke", "#f59e0b");
          path.setAttribute("stroke-width", `${Math.min(6, 2 + edge.dependency_count)}px`);
          path.setAttribute("stroke-dasharray", "6 4");
          path.setAttribute("fill", "none");
          path.setAttribute("opacity", "0.75");
          path.setAttribute("marker-end", "url(#marker-cross)");

          svg.appendChild(path);
        });
      } else {
        // Render Thing-to-Thing edges inside & across spheres
        (this.data.edges || []).forEach(edge => {
          const sEl = container.querySelector(`.thing-sphere-node[data-thing-id="${edge.source_thing_id}"]`);
          const tEl = container.querySelector(`.thing-sphere-node[data-thing-id="${edge.target_thing_id}"]`);
          if (!sEl || !tEl) return;

          const sR = sEl.getBoundingClientRect();
          const tR = tEl.getBoundingClientRect();

          const x1 = (sR.left + sR.width / 2 - containerRect.left) / scale;
          const y1 = (sR.top + sR.height / 2 - containerRect.top) / scale;
          const x2 = (tR.left + tR.width / 2 - containerRect.left) / scale;
          const y2 = (tR.top + tR.height / 2 - containerRect.top) / scale;

          const path = document.createElementNS(svgNS, "path");
          const isCross = edge.is_cross_org;

          if (isCross) {
            // High-arc glowing cross-cutting vector
            const dx = x2 - x1;
            const dy = y2 - y1;
            const curvature = 0.25;
            const cx = (x1 + x2) / 2 - dy * curvature;
            const cy = (y1 + y2) / 2 + dx * curvature;
            path.setAttribute("d", `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`);
            path.setAttribute("class", "cross-cutting-edge-path glowing-pulse");
            path.setAttribute("stroke", "#f59e0b");
            path.setAttribute("stroke-width", "2.5px");
            path.setAttribute("stroke-dasharray", "5 3");
            path.setAttribute("opacity", "0.85");
            path.setAttribute("marker-end", "url(#marker-cross)");
          } else {
            // Subtle intra-org connection
            const midX = (x1 + x2) / 2;
            path.setAttribute("d", `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`);
            path.setAttribute("class", "internal-sphere-edge-path");
            path.setAttribute("stroke", "#475569");
            path.setAttribute("stroke-width", "1.5px");
            path.setAttribute("opacity", "0.4");
            path.setAttribute("marker-end", "url(#marker-internal)");
          }

          path.setAttribute("fill", "none");
          path.setAttribute("data-source-thing", edge.source_thing_id);
          path.setAttribute("data-target-thing", edge.target_thing_id);
          path.setAttribute("data-is-cross", isCross ? "true" : "false");

          svg.appendChild(path);
        });
      }

      container.appendChild(svg);
    });
  },

  highlightThingConnections(thingId) {
    const targets = [
      document.getElementById("spheres-graph-target"),
      document.getElementById("spheres-modal-graph-target")
    ];

    targets.forEach(container => {
      if (!container) return;
      const paths = container.querySelectorAll(".cross-cutting-edge-path, .internal-sphere-edge-path");
      const nodes = container.querySelectorAll(".thing-sphere-node");

      const connectedThingIds = new Set([thingId]);

      paths.forEach(p => {
        const s = p.dataset.sourceThing;
        const t = p.dataset.targetThing;
        if (s === thingId || t === thingId) {
          p.classList.add("edge-highlighted");
          p.style.opacity = "1.0";
          p.style.stroke = p.dataset.isCross === "true" ? "#38bdf8" : "#10b981";
          p.style.strokeWidth = "3.5px";
          if (s) connectedThingIds.add(s);
          if (t) connectedThingIds.add(t);
        } else {
          p.style.opacity = "0.1";
        }
      });

      nodes.forEach(n => {
        if (connectedThingIds.has(n.dataset.thingId)) {
          n.style.opacity = "1.0";
          n.classList.add("node-highlighted");
        } else {
          n.style.opacity = "0.3";
          n.classList.remove("node-highlighted");
        }
      });
    });
  },

  highlightOrgConnections(orgId) {
    const targets = [
      document.getElementById("spheres-graph-target"),
      document.getElementById("spheres-modal-graph-target")
    ];

    targets.forEach(container => {
      if (!container) return;
      const paths = container.querySelectorAll(".macro-org-edge-path");
      const cards = container.querySelectorAll(".org-macro-card");

      const connectedOrgIds = new Set([orgId]);

      paths.forEach(p => {
        const s = p.dataset.sourceOrg;
        const t = p.dataset.targetOrg;
        if (s === orgId || t === orgId) {
          p.style.opacity = "1.0";
          p.style.stroke = "#38bdf8";
          p.style.strokeWidth = "5px";
          if (s) connectedOrgIds.add(s);
          if (t) connectedOrgIds.add(t);
        } else {
          p.style.opacity = "0.15";
        }
      });

      cards.forEach(c => {
        if (connectedOrgIds.has(c.dataset.orgId)) {
          c.style.opacity = "1.0";
          c.classList.add("card-highlighted");
        } else {
          c.style.opacity = "0.35";
          c.classList.remove("card-highlighted");
        }
      });
    });
  },

  clearHighlights() {
    const targets = [
      document.getElementById("spheres-graph-target"),
      document.getElementById("spheres-modal-graph-target")
    ];

    targets.forEach(container => {
      if (!container) return;
      const paths = container.querySelectorAll("path");
      const nodes = container.querySelectorAll(".thing-sphere-node, .org-macro-card");

      paths.forEach(p => {
        p.style.opacity = "";
        p.style.stroke = "";
        p.style.strokeWidth = "";
        p.classList.remove("edge-highlighted");
      });

      nodes.forEach(n => {
        n.style.opacity = "";
        n.classList.remove("node-highlighted");
        n.classList.remove("card-highlighted");
      });
    });
  }
};

window.SpheresManager = SpheresManager;
