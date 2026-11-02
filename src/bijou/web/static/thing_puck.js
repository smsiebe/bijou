/**
 * Bijou "Thing" Detail Puck - Floating Contextual HUD & Analytical Tool Dispatcher.
 * Features:
 * - Floating, draggable, and pinnable HUD
 * - A/B Test Aesthetic Tabs:
 *   1. Compact Tactical (Look A - Dense Cybernetic HUD)
 *   2. Relational & Stakeholders (Look B - Upstream/Downstream Graph Traversal)
 *   3. Operational Telemetry & SLA (Look C - DuckDB Metrics & Provenance)
 *   4. Modular Analytical Tools Hub (Pluggable Dispatcher)
 * - Interactive clickable relation chips for immediate node jumping
 * - Offline-first, relative paths, zero CDN dependencies.
 */

const ThingPuck = {
  currentThing: null,
  currentFocalData: null,
  orgsCache: null,
  toolsCache: null,
  isPinned: false,
  isDragging: false,
  dragOffsetX: 0,
  dragOffsetY: 0,
  activeTab: "tactical",

  async init() {
    this.bindControls();
    try {
      this.orgsCache = await BijouAPI.getOrganizations().catch(() => []);
      this.toolsCache = await BijouAPI.getTools().catch(() => []);
    } catch (e) {
      console.warn("ThingPuck: Could not pre-cache orgs/tools:", e);
    }
  },

  bindControls() {
    const puck = document.getElementById("thing-detail-puck");
    if (!puck) return;

    const header = puck.querySelector(".thing-puck-header");
    const closeBtn = document.getElementById("puck-close-btn");
    const pinBtn = document.getElementById("puck-pin-btn");

    if (closeBtn) {
      closeBtn.addEventListener("click", () => this.close());
    }

    if (pinBtn) {
      pinBtn.addEventListener("click", () => {
        this.isPinned = !this.isPinned;
        puck.classList.toggle("pinned", this.isPinned);
        pinBtn.classList.toggle("active", this.isPinned);
        pinBtn.title = this.isPinned ? "Unpin HUD" : "Pin HUD in place";
      });
    }

    // Draggable HUD functionality
    if (header) {
      header.addEventListener("mousedown", (e) => {
        if (e.target.closest("button") || e.target.closest(".puck-tab-btn")) return;
        this.isDragging = true;
        const rect = puck.getBoundingClientRect();
        this.dragOffsetX = e.clientX - rect.left;
        this.dragOffsetY = e.clientY - rect.top;
        puck.classList.add("dragging");
        header.style.cursor = "grabbing";
      });

      window.addEventListener("mousemove", (e) => {
        if (!this.isDragging) return;
        e.preventDefault();
        const puckEl = document.getElementById("thing-detail-puck");
        if (!puckEl) return;

        let newX = e.clientX - this.dragOffsetX;
        let newY = e.clientY - this.dragOffsetY;

        // Clamp to viewport
        const maxX = window.innerWidth - puckEl.offsetWidth - 10;
        const maxY = window.innerHeight - puckEl.offsetHeight - 10;
        newX = Math.max(10, Math.min(newX, maxX));
        newY = Math.max(10, Math.min(newY, maxY));

        puckEl.style.left = `${newX}px`;
        puckEl.style.top = `${newY}px`;
        puckEl.style.bottom = "auto";
        puckEl.style.right = "auto";
      });

      window.addEventListener("mouseup", () => {
        if (this.isDragging) {
          this.isDragging = false;
          const puckEl = document.getElementById("thing-detail-puck");
          if (puckEl) puckEl.classList.remove("dragging");
          header.style.cursor = "grab";
        }
      });
    }

    // Tab switching
    const tabBtns = puck.querySelectorAll(".puck-tab-btn");
    tabBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const tabKey = btn.dataset.puckTab;
        if (tabKey) this.switchTab(tabKey);
      });
    });
  },

  switchTab(tabKey) {
    this.activeTab = tabKey;
    const puck = document.getElementById("thing-detail-puck");
    if (!puck) return;

    puck.querySelectorAll(".puck-tab-btn").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.puckTab === tabKey);
    });

    puck.querySelectorAll(".puck-tab-panel").forEach(panel => {
      panel.classList.toggle("active", panel.dataset.puckTab === tabKey);
    });

    if (this.currentThing && this.currentFocalData) {
      this.renderActiveTab();
    }
  },

  async open(nodeOrThing, event = null) {
    const puck = document.getElementById("thing-detail-puck");
    if (!puck) return;

    const thingId = typeof nodeOrThing === "string" ? nodeOrThing : (nodeOrThing.thing_id || nodeOrThing.id);
    if (!thingId) return;

    // Position puck near event if not pinned and event exists
    if (!this.isPinned && event && event.clientX) {
      const puckWidth = 440;
      const puckHeight = 520;
      let targetX = event.clientX + 24;
      let targetY = event.clientY - 60;

      if (targetX + puckWidth > window.innerWidth - 20) {
        targetX = event.clientX - puckWidth - 24;
      }
      if (targetY + puckHeight > window.innerHeight - 20) {
        targetY = window.innerHeight - puckHeight - 20;
      }
      targetX = Math.max(16, targetX);
      targetY = Math.max(16, targetY);

      puck.style.left = `${targetX}px`;
      puck.style.top = `${targetY}px`;
      puck.style.right = "auto";
      puck.style.bottom = "auto";
    }

    puck.classList.add("visible");
    this.renderLoadingState(thingId);

    try {
      if (!this.orgsCache) {
        this.orgsCache = await BijouAPI.getOrganizations().catch(() => []);
      }
      if (!this.toolsCache) {
        this.toolsCache = await BijouAPI.getTools().catch(() => []);
      }

      const focalData = await BijouAPI.getThingFocalDashboard(thingId);
      this.currentFocalData = focalData;
      this.currentThing = focalData.thing;
      this.renderHeader();
      this.renderActiveTab();
    } catch (err) {
      this.renderErrorState(err.message);
    }
  },

  async openByThingId(thingId) {
    return this.open(thingId, null);
  },

  close() {
    const puck = document.getElementById("thing-detail-puck");
    if (puck) {
      puck.classList.remove("visible");
    }
  },

  renderLoadingState(thingId) {
    const titleEl = document.getElementById("puck-thing-title");
    const subEl = document.getElementById("puck-thing-subtitle");
    if (titleEl) titleEl.textContent = `Loading ${thingId}...`;
    if (subEl) subEl.textContent = "Querying causal graph & telemetry rollups...";

    const contentPanels = document.querySelectorAll(".puck-tab-panel");
    contentPanels.forEach(p => {
      p.innerHTML = `<div class="puck-loading-spinner"><div class="spinner-dot"></div> Resolving telemetry & dependencies...</div>`;
    });
  },

  renderErrorState(msg) {
    const activePanel = document.querySelector(".puck-tab-panel.active");
    if (activePanel) {
      activePanel.innerHTML = `
        <div style="padding: 24px; text-align: center; color: var(--color-blocked);">
          <div style="font-weight: 700; margin-bottom: 6px;">Failed to load Thing details</div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${msg}</div>
        </div>
      `;
    }
  },

  renderHeader() {
    const t = this.currentThing;
    if (!t) return;

    const titleEl = document.getElementById("puck-thing-title");
    const subEl = document.getElementById("puck-thing-subtitle");
    const badgeEl = document.getElementById("puck-lifecycle-badge");

    if (titleEl) titleEl.textContent = t.name;
    if (subEl) {
      const org = (this.orgsCache || []).find(o => o.id === t.owner_org_id);
      const orgName = org ? org.name : t.owner_org_id;
      subEl.textContent = `${t.id} • ${orgName}`;
    }
    if (badgeEl) {
      badgeEl.className = `badge-pill state-${t.lifecycle.toLowerCase().replace('_', '-')}`;
      badgeEl.textContent = t.lifecycle;
    }
  },

  renderActiveTab() {
    switch (this.activeTab) {
      case "tactical":
        this.renderTacticalTab();
        break;
      case "relational":
        this.renderRelationalTab();
        break;
      case "telemetry":
        this.renderTelemetryTab();
        break;
      case "tools":
        this.renderToolsTab();
        break;
    }
  },

  // --- TAB 1: Compact Tactical (Look A) ---
  renderTacticalTab() {
    const panel = document.getElementById("puck-panel-tactical");
    if (!panel || !this.currentThing || !this.currentFocalData) return;

    const t = this.currentThing;
    const focal = this.currentFocalData;
    const org = (this.orgsCache || []).find(o => o.id === t.owner_org_id);

    const costStr = t.estimated_cost >= 1000000
      ? `$${(t.estimated_cost / 1000000).toFixed(2)}M`
      : `$${(t.estimated_cost / 1000).toFixed(0)}k`;

    const trlPercent = Math.min(100, Math.round((t.trl / 9) * 100));

    const concernsHtml = focal.impacted_concerns && focal.impacted_concerns.length > 0
      ? focal.impacted_concerns.map(c => `
          <div class="puck-concern-chip">
            <span class="chip-name">${c.concern_name || c.concern_id}</span>
            <span class="chip-score">+${(c.coverage_score * 100).toFixed(0)}%</span>
          </div>
        `).join("")
      : `<span style="font-size: 0.75rem; color: var(--text-dim); font-style: italic;">No strategic concerns linked</span>`;

    panel.innerHTML = `
      <div class="tactical-grid">
        <div class="tactical-metric-card">
          <div class="metric-label">TRL MATURITY</div>
          <div class="metric-value">TRL ${t.trl}<span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;"> / 9</span></div>
          <div class="trl-progress-track">
            <div class="trl-progress-bar" style="width: ${trlPercent}%;"></div>
          </div>
        </div>

        <div class="tactical-metric-card">
          <div class="metric-label">ESTIMATED COST</div>
          <div class="metric-value" style="color: var(--accent-amber);">${costStr}</div>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">Direct ROI: ${focal.direct_roi.toFixed(2)}x</div>
        </div>

        <div class="tactical-metric-card">
          <div class="metric-label">RISK FACTOR</div>
          <div class="metric-value" style="color: ${t.risk_factor > 1.2 ? '#ef4444' : '#10b981'};">${t.risk_factor.toFixed(2)}</div>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">Multiplier</div>
        </div>

        <div class="tactical-metric-card">
          <div class="metric-label">ECHELON TIER</div>
          <div class="metric-value" style="color: var(--accent-cyan);">Level ${org ? org.echelon_level : 1}</div>
          <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">${org ? org.name : t.owner_org_id}</div>
        </div>
      </div>

      <div class="puck-section-divider"></div>

      <div class="puck-section">
        <div class="puck-section-title">DESCRIPTION & SCOPE</div>
        <div class="puck-description-text">${t.description || "No operational description provided."}</div>
      </div>

      <div class="puck-section">
        <div class="puck-section-title">STRATEGIC CONCERNS SERVICED</div>
        <div class="puck-chip-container">
          ${concernsHtml}
        </div>
      </div>

      <div class="puck-section-divider"></div>

      <div class="puck-quick-actions">
        <button class="puck-action-btn primary" id="puck-quick-slip-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          Slip Simulator
        </button>
        <button class="puck-action-btn" id="puck-quick-spheres-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          Spheres View
        </button>
        <button class="puck-action-btn" id="puck-quick-focal-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3"/></svg>
          Focal Ego Lens
        </button>
      </div>
    `;

    // Wire up quick actions
    const slipBtn = panel.querySelector("#puck-quick-slip-btn");
    if (slipBtn) {
      slipBtn.addEventListener("click", () => this.launchSlipSimulator());
    }

    const spheresBtn = panel.querySelector("#puck-quick-spheres-btn");
    if (spheresBtn) {
      spheresBtn.addEventListener("click", () => this.launchSpheresView());
    }

    const focalBtn = panel.querySelector("#puck-quick-focal-btn");
    if (focalBtn) {
      focalBtn.addEventListener("click", () => this.launchFocalView());
    }
  },

  // --- TAB 2: Relational & Stakeholders (Look B) ---
  renderRelationalTab() {
    const panel = document.getElementById("puck-panel-relational");
    if (!panel || !this.currentThing || !this.currentFocalData) return;

    const t = this.currentThing;
    const focal = this.currentFocalData;
    const org = (this.orgsCache || []).find(o => o.id === t.owner_org_id);

    // Cross-org partners detection
    const partnerOrgIds = new Set();
    const upThings = focal.upstream_dependencies || [];
    const downThings = focal.downstream_dependents || [];

    upThings.forEach(ut => {
      if (ut.owner_org_id && ut.owner_org_id !== t.owner_org_id) {
        partnerOrgIds.add(ut.owner_org_id);
      }
    });
    downThings.forEach(dt => {
      if (dt.owner_org_id && dt.owner_org_id !== t.owner_org_id) {
        partnerOrgIds.add(dt.owner_org_id);
      }
    });

    const isCrossOrg = partnerOrgIds.size > 0;
    const crossOrgBadges = isCrossOrg
      ? Array.from(partnerOrgIds).map(pId => {
          const pOrg = (this.orgsCache || []).find(o => o.id === pId);
          return `<span class="cross-org-partner-pill">${pOrg ? pOrg.name : pId}</span>`;
        }).join(" ")
      : `<span style="font-size: 0.75rem; color: var(--text-dim); font-style: italic;">Internal to ${org ? org.name : t.owner_org_id}</span>`;

    const upChips = upThings.length > 0
      ? upThings.map(ut => `
          <button class="relation-nav-chip upstream" data-thing-id="${ut.id}" title="Inspect upstream dependency">
            <span class="chip-direction">▲ IN</span>
            <span class="chip-title">${ut.name}</span>
            <span class="chip-trl">TRL ${ut.trl}</span>
          </button>
        `).join("")
      : `<div style="font-size: 0.75rem; color: var(--text-dim); font-style: italic;">No upstream dependencies (Foundational Root)</div>`;

    const downChips = downThings.length > 0
      ? downThings.map(dt => `
          <button class="relation-nav-chip downstream" data-thing-id="${dt.id}" title="Inspect downstream dependent">
            <span class="chip-direction">▼ OUT</span>
            <span class="chip-title">${dt.name}</span>
            <span class="chip-trl">TRL ${dt.trl}</span>
          </button>
        `).join("")
      : `<div style="font-size: 0.75rem; color: var(--text-dim); font-style: italic;">No downstream dependents (Terminal Capability)</div>`;

    const effectsHtml = focal.produced_effects && focal.produced_effects.length > 0
      ? focal.produced_effects.map(ef => `
          <div class="effect-spec-pill">
            <span class="effect-domain">${ef.domain}</span>
            <span class="effect-name">${ef.name}</span>
            <span class="effect-metric">${ef.metric_unit || "operational"}</span>
          </div>
        `).join("")
      : `<div style="font-size: 0.75rem; color: var(--text-dim); font-style: italic;">No published causal effects</div>`;

    panel.innerHTML = `
      <div class="stakeholder-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;">Lead Stakeholder / Owner</div>
            <div style="font-size: 0.95rem; font-weight: 700; color: var(--accent-cyan); margin-top: 2px;">${org ? org.name : t.owner_org_id}</div>
          </div>
          <span class="badge-pill" style="border-color: var(--accent-cyan); color: var(--accent-cyan);">Echelon ${org ? org.echelon_level : 1}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px; font-style: italic;">
          "${org && org.mission_statement ? org.mission_statement : "Sovereign architectural unit"}"
        </div>
      </div>

      <div class="puck-section">
        <div class="puck-section-title">
          <span>CROSS-CUTTING PARTNER ORGANIZATIONS</span>
          ${isCrossOrg ? `<span class="badge-pill" style="font-size: 0.65rem; color: var(--accent-amber); border-color: rgba(245,158,11,0.3);">Cross-Boundary</span>` : ''}
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
          ${crossOrgBadges}
        </div>
      </div>

      <div class="puck-section">
        <div class="puck-section-title">UPSTREAM SUPPLIERS & PREREQUISITES (${upThings.length})</div>
        <div class="relation-chips-wrapper">
          ${upChips}
        </div>
      </div>

      <div class="puck-section">
        <div class="puck-section-title">DOWNSTREAM CONSUMERS & BENEFICIARIES (${downThings.length})</div>
        <div class="relation-chips-wrapper">
          ${downChips}
        </div>
      </div>

      <div class="puck-section">
        <div class="puck-section-title">PRODUCED CAUSAL EFFECTS (${(focal.produced_effects || []).length})</div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
          ${effectsHtml}
        </div>
      </div>
    `;

    // Wire up interactive clickable chips for instant puck node traversal
    panel.querySelectorAll(".relation-nav-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const nextId = chip.dataset.thingId;
        if (nextId) this.openByThingId(nextId);
      });
    });
  },

  // --- TAB 3: Operational Telemetry & SLA (Look C) ---
  renderTelemetryTab() {
    const panel = document.getElementById("puck-panel-telemetry");
    if (!panel || !this.currentThing || !this.currentFocalData) return;

    const focal = this.currentFocalData;
    const rollups = focal.telemetry_rollups || [];

    let totalEvents = 0;
    let avgDwell = 0;
    let minDwell = 0;
    let maxDwell = 0;

    if (rollups.length > 0) {
      totalEvents = rollups.reduce((acc, r) => acc + (r.event_count || 0), 0);
      const dwRollups = rollups.filter(r => r.mean_dwell_days !== undefined);
      if (dwRollups.length > 0) {
        avgDwell = dwRollups.reduce((acc, r) => acc + r.mean_dwell_days, 0) / dwRollups.length;
        minDwell = Math.min(...dwRollups.map(r => r.min_dwell_days || 0));
        maxDwell = Math.max(...dwRollups.map(r => r.max_dwell_days || 0));
      }
    }

    const slaStatus = totalEvents > 5 ? "HEALTHY" : totalEvents > 0 ? "OPTIMAL" : "DORMANT";
    const slaColor = slaStatus === "HEALTHY" || slaStatus === "OPTIMAL" ? "var(--color-ready)" : "var(--text-dim)";

    const rollupsHtml = rollups.length > 0
      ? rollups.map(r => `
          <div class="telemetry-rollup-row">
            <div>
              <div style="font-weight: 600; font-size: 0.8rem; color: var(--text-main);">${r.effect_name || r.effect_id}</div>
              <div style="font-size: 0.7rem; color: var(--text-muted);">${r.domain || "general"} • ${r.event_count} events</div>
            </div>
            <div style="text-align: right;">
              <div style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-cyan);">${r.mean_dwell_days !== undefined ? r.mean_dwell_days.toFixed(1) + "d" : "-"}</div>
              <div style="font-size: 0.65rem; color: var(--text-dim);">mean dwell</div>
            </div>
          </div>
        `).join("")
      : `<div style="font-size: 0.75rem; color: var(--text-dim); text-align: center; padding: 16px 0;">No operational telemetry stream events recorded yet.</div>`;

    panel.innerHTML = `
      <div class="sla-status-banner">
        <div>
          <span style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">DuckDB SLA Telemetry Engine</span>
          <div style="font-size: 1.1rem; font-weight: 700; color: ${slaColor}; margin-top: 2px;">SLA STATUS: ${slaStatus}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-family: var(--font-mono); font-size: 1.1rem; font-weight: 700; color: var(--accent-cyan);">${totalEvents}</div>
          <div style="font-size: 0.68rem; color: var(--text-muted);">Total Events</div>
        </div>
      </div>

      <div class="tactical-grid" style="margin-top: 12px;">
        <div class="tactical-metric-card">
          <div class="metric-label">MEAN DWELL TIME</div>
          <div class="metric-value">${avgDwell.toFixed(1)}<span style="font-size: 0.75rem; color: var(--text-muted);"> days</span></div>
        </div>

        <div class="tactical-metric-card">
          <div class="metric-label">MIN / MAX DWELL</div>
          <div class="metric-value">${minDwell.toFixed(0)} - ${maxDwell.toFixed(0)}<span style="font-size: 0.75rem; color: var(--text-muted);"> d</span></div>
        </div>
      </div>

      <div class="puck-section" style="margin-top: 14px;">
        <div class="puck-section-title">EFFECT STREAM PROVENANCE</div>
        <div class="telemetry-rollups-list">
          ${rollupsHtml}
        </div>
      </div>
    `;
  },

  // --- TAB 4: Pluggable Modular Tools Hub ---
  renderToolsTab() {
    const panel = document.getElementById("puck-panel-tools");
    if (!panel || !this.currentThing) return;

    const t = this.currentThing;
    const tools = this.toolsCache || [
      {
        tool_id: "what_if_slip_simulator",
        title: "What-If Slip Simulator",
        icon: "zap",
        category: "simulation",
        description: "Simulate schedule slip or full cancellation and trace cascading deadline breaches."
      },
      {
        tool_id: "clustered_spheres_of_ownership",
        title: "Spheres of Ownership",
        icon: "globe",
        category: "graph_projection",
        description: "Visualize cross-cutting dependencies across organizational boundaries."
      },
      {
        tool_id: "focal_ego_network",
        title: "Focal Ego Dashboard",
        icon: "target",
        category: "workbench",
        description: "2-hop ego-network visualization with direct trade-off evaluations."
      },
      {
        tool_id: "decision_provenance_ledger",
        title: "Strategic Decision Ledger",
        icon: "history",
        category: "audit",
        description: "Review provenance audit trail and commit new strategic decision logs."
      }
    ];

    panel.innerHTML = `
      <div style="margin-bottom: 12px;">
        <div style="font-size: 0.8rem; color: var(--text-muted);">Analytical tool suite for <strong style="color: var(--accent-cyan);">${t.name}</strong>:</div>
      </div>

      <div class="tools-grid">
        ${tools.map(tool => `
          <div class="tool-card" data-tool-id="${tool.tool_id}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div style="font-weight: 700; font-size: 0.88rem; color: var(--text-main);">${tool.title}</div>
              <span class="badge-pill" style="font-size: 0.65rem;">${tool.category}</span>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin: 6px 0 10px 0; line-height: 1.35;">
              ${tool.description}
            </div>
            <button class="puck-action-btn primary launch-tool-btn" data-tool-id="${tool.tool_id}" style="width: 100%; justify-content: center;">
              Launch ${tool.title}
            </button>
          </div>
        `).join("")}
      </div>
    `;

    panel.querySelectorAll(".launch-tool-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const toolId = btn.dataset.toolId;
        this.dispatchTool(toolId);
      });
    });
  },

  dispatchTool(toolId) {
    if (!this.currentThing) return;

    switch (toolId) {
      case "what_if_slip_simulator":
        this.launchSlipSimulator();
        break;
      case "clustered_spheres_of_ownership":
        this.launchSpheresView();
        break;
      case "focal_ego_network":
        this.launchFocalView();
        break;
      case "portfolio_tradeoff_matrix":
        this.launchTradeoffView();
        break;
      case "decision_provenance_ledger":
        this.launchDecisionLedger();
        break;
      default:
        console.info(`Dispatched analytical tool: ${toolId} for ${this.currentThing.id}`);
        break;
    }
  },

  launchSlipSimulator() {
    if (!this.currentThing) return;
    const t = this.currentThing;

    // Use current tech tree selected node or construct adapter node
    const dummyNode = {
      thing_id: t.id,
      thing_name: t.name,
      milestone_id: `ms-${t.id}-initial`,
      title: `${t.name} Deployment`,
      state: t.lifecycle === "OPERATIONAL" ? "COMPLETED" : "IN_PROGRESS",
      trl: t.trl,
      cost_estimate: t.estimated_cost
    };

    if (window.TechTreeManager && typeof window.TechTreeManager.openSlipDrawer === "function") {
      window.TechTreeManager.openSlipDrawer(dummyNode);
    }
  },

  launchSpheresView() {
    if (!this.currentThing) return;
    const orgId = this.currentThing.owner_org_id;

    // If SpheresManager exists, switch and focus
    if (window.SpheresManager) {
      window.SpheresManager.show({ focusThingId: this.currentThing.id, focusOrgId: orgId });
    }
  },

  launchFocalView() {
    if (!this.currentThing) return;
    const thingId = this.currentThing.id;

    const lensBtn = document.querySelector('.lens-btn[data-lens="focal-dashboard"]');
    if (lensBtn) lensBtn.click();

    const focalSelect = document.getElementById("focal-thing-select");
    if (focalSelect) {
      focalSelect.value = thingId;
      if (window.ViewsManager && typeof window.ViewsManager.refreshFocal === "function") {
        window.ViewsManager.refreshFocal();
      }
    }
  },

  launchTradeoffView() {
    if (!this.currentThing) return;
    const thingId = this.currentThing.id;

    const lensBtn = document.querySelector('.lens-btn[data-lens="focal-dashboard"]');
    if (lensBtn) lensBtn.click();

    const cb = document.querySelector(`.tradeoff-candidate-checkbox[value="${thingId}"]`);
    if (cb) cb.checked = true;

    const runBtn = document.getElementById("run-tradeoff-btn");
    if (runBtn) runBtn.click();
  },

  launchDecisionLedger() {
    this.launchSlipSimulator();
    const ledger = document.getElementById("drawer-decision-logs");
    if (ledger) {
      ledger.scrollIntoView({ behavior: "smooth" });
    }
  }
};

window.ThingPuck = ThingPuck;
