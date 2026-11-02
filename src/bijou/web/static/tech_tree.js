/**
 * 4X Game-Style Tech Tree Canvas & What-If Slip Simulator.
 */

const TechTreeManager = {
  currentViewData: null,
  selectedMilestoneId: null,

  async init() {
    this.bindControls();
    await this.refresh();
  },

  bindControls() {
    const modeSelect = document.getElementById("stratification-mode-select");
    if (modeSelect) {
      modeSelect.addEventListener("change", () => this.refresh());
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
  },

  async refresh() {
    const modeSelect = document.getElementById("stratification-mode-select");
    const mode = modeSelect ? modeSelect.value : "TRL_TIERS";
    try {
      this.currentViewData = await BijouAPI.getTechTree(mode);
      this.render();
    } catch (err) {
      console.error("Error loading tech tree:", err);
    }
  },

  render() {
    const canvas = document.getElementById("tech-tree-grid-target");
    if (!canvas || !this.currentViewData) return;
    canvas.innerHTML = "";

    const { tiers, nodes, edges } = this.currentViewData;

    // Group nodes by tier_order
    const nodesByTier = {};
    tiers.forEach(t => { nodesByTier[t.order] = []; });
    nodes.forEach(n => {
      if (!nodesByTier[n.tier_order]) nodesByTier[n.tier_order] = [];
      nodesByTier[n.tier_order].push(n);
    });

    // Render columns
    tiers.forEach(tier => {
      const col = document.createElement("div");
      col.className = "tech-tree-column";

      const header = document.createElement("div");
      header.className = "column-header";
      header.textContent = tier.tier_name || `Tier ${tier.order}`;
      col.appendChild(header);

      const colNodes = nodesByTier[tier.order] || [];
      colNodes.forEach(node => {
        const card = document.createElement("div");
        const stateClass = `state-${node.state.toLowerCase().replace('_', '-')}`;
        card.className = `node-card ${stateClass}`;
        card.dataset.nodeId = node.node_id;
        card.dataset.milestoneId = node.milestone_id;

        card.innerHTML = `
          <div class="node-title">${node.title}</div>
          <div style="font-size: 0.8rem; color: var(--text-muted);">${node.thing_name}</div>
          <div class="node-meta">
            <span>TRL ${node.trl}</span>
            <span>$${(node.cost_estimate / 1000).toFixed(0)}k</span>
            <span>${node.state}</span>
          </div>
        `;

        card.addEventListener("click", () => this.openSlipDrawer(node));
        card.addEventListener("mouseenter", () => this.highlightSpine(node.node_id));
        card.addEventListener("mouseleave", () => this.clearSpineHighlight());

        col.appendChild(card);
      });

      canvas.appendChild(col);
    });
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
    if (!this.currentViewData) return;
    const cards = document.querySelectorAll(".node-card");
    cards.forEach(c => c.style.opacity = "0.3");

    const targetCard = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (targetCard) targetCard.style.opacity = "1.0";
  },

  clearSpineHighlight() {
    const cards = document.querySelectorAll(".node-card");
    cards.forEach(c => c.style.opacity = "1.0");
  }
};
