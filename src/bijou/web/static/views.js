/**
 * Bijou View Renderers:
 * - Multi-Perspective 1-Slide Briefing (4 quadrants + window.print)
 * - Single-Thing Focal Dashboard & Trade-Off Matrix
 * - Admin CRUD & JSON Manifest Import/Export Studio
 */

const ViewsManager = {
  // --- 1. Multi-Perspective 1-Slide Briefing ---
  async initBriefing() {
    const orgSelect = document.getElementById("briefing-subject-org");
    const perspSelect = document.getElementById("briefing-perspective-org");
    const descendantsCheckbox = document.getElementById("briefing-descendants-toggle");
    const refreshBtn = document.getElementById("briefing-refresh-btn");
    const printBtn = document.getElementById("briefing-print-btn");

    if (printBtn) {
      printBtn.addEventListener("click", () => window.print());
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.refreshBriefing());
    }

    if (orgSelect) {
      orgSelect.addEventListener("change", () => this.refreshBriefing());
    }

    if (perspSelect) {
      perspSelect.addEventListener("change", () => this.refreshBriefing());
    }

    if (descendantsCheckbox) {
      descendantsCheckbox.addEventListener("change", () => this.refreshBriefing());
    }
  },

  async refreshBriefing() {
    const orgSelect = document.getElementById("briefing-subject-org");
    if (!orgSelect || !orgSelect.value) return;

    const subjectOrgId = orgSelect.value;
    const perspSelect = document.getElementById("briefing-perspective-org");
    const perspectiveOrgId = perspSelect && perspSelect.value ? perspSelect.value : null;
    const descendantsCheckbox = document.getElementById("briefing-descendants-toggle");
    const includeDescendants = descendantsCheckbox ? descendantsCheckbox.checked : true;

    try {
      const data = await BijouAPI.getPerspectiveBriefing(subjectOrgId, perspectiveOrgId, includeDescendants);
      this.renderBriefing(data);
    } catch (err) {
      console.error("Failed to load briefing:", err);
      const container = document.getElementById("briefing-slide-target");
      if (container) {
        container.innerHTML = `<div style="color: var(--color-blocked); padding: 20px;">Failed to load briefing: ${err.message}</div>`;
      }
    }
  },

  renderBriefing(briefing) {
    const container = document.getElementById("briefing-slide-target");
    if (!container) return;

    const subjectOrg = briefing.subject_org_name || briefing.subject_org_id;
    const perspectiveOrg = briefing.perspective_org_name || "Self (Direct Sovereign)";
    const asOf = briefing.as_of_date || new Date().toISOString().split("T")[0];

    // Build 4 quadrants HTML
    container.innerHTML = `
      <div class="briefing-slide">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border-subtle); padding-bottom: 12px;">
          <div>
            <h2 style="font-size: 1.4rem; color: var(--accent-cyan); font-weight: 700;">Executive Perspective Briefing: ${subjectOrg}</h2>
            <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
              Observed through: <strong>${perspectiveOrg}</strong> | As of: ${asOf}
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-family: var(--font-mono);">Portfolio ROI Score</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: var(--color-achieved);">${briefing.roi_breakdown.portfolio_roi_score}</div>
          </div>
        </div>

        <div class="briefing-quadrants">
          <!-- Quadrant 1: Strategic Alignment -->
          <div class="quadrant-card">
            <h3>1. Strategic Alignment (${briefing.strategic_alignment.length} Concerns)</h3>
            <div style="max-height: 220px; overflow-y: auto;">
              ${briefing.strategic_alignment.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">No strategic concerns aligned.</div>' : `
                <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                  <thead>
                    <tr style="text-align: left; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
                      <th style="padding: 4px 0;">Concern</th>
                      <th>Priority</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${briefing.strategic_alignment.map(c => `
                      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 6px 0; font-weight: 600;">${c.title}</td>
                        <td><span style="font-size: 0.75rem; color: ${c.priority === 'CRITICAL' ? 'var(--color-blocked)' : 'var(--color-ready)'}">${c.priority}</span></td>
                        <td><span class="badge-pill" style="font-size: 0.7rem;">${c.status}</span></td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              `}
            </div>
          </div>

          <!-- Quadrant 2: Funded Things -->
          <div class="quadrant-card">
            <h3>2. Funded Things (${briefing.funded_things.length} Assets)</h3>
            <div style="max-height: 220px; overflow-y: auto;">
              ${briefing.funded_things.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">No things funded under this lens.</div>' : `
                <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                  <thead>
                    <tr style="text-align: left; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
                      <th style="padding: 4px 0;">Thing</th>
                      <th>Tier</th>
                      <th>Cost</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${briefing.funded_things.map(t => `
                      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 6px 0; font-weight: 600;">${t.title}</td>
                        <td style="font-family: var(--font-mono);">${t.tier}</td>
                        <td style="font-family: var(--font-mono);">$${(t.cost_estimate / 1000).toFixed(0)}k</td>
                        <td><span class="badge-pill" style="font-size: 0.7rem;">${t.lifecycle_status}</span></td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              `}
            </div>
          </div>

          <!-- Quadrant 3: Cross-Org Dependencies -->
          <div class="quadrant-card">
            <h3>3. Cross-Org Dependencies (${briefing.cross_org_dependencies.length})</h3>
            <div style="max-height: 220px; overflow-y: auto;">
              ${briefing.cross_org_dependencies.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">Zero cross-organization dependencies detected.</div>' : `
                <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                  <thead>
                    <tr style="text-align: left; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
                      <th style="padding: 4px 0;">Source</th>
                      <th>Target</th>
                      <th>Type</th>
                      <th>Criticality</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${briefing.cross_org_dependencies.map(d => `
                      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 6px 0;">${d.source_name}</td>
                        <td>${d.target_name}</td>
                        <td style="font-family: var(--font-mono); font-size: 0.7rem;">${d.dependency_type}</td>
                        <td><span style="font-size: 0.75rem; color: ${d.is_critical ? 'var(--color-blocked)' : 'var(--text-muted)'}">${d.is_critical ? 'CRITICAL' : 'Standard'}</span></td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              `}
            </div>
          </div>

          <!-- Quadrant 4: ROI Breakdown & Executive Takeaway -->
          <div class="quadrant-card">
            <h3>4. Financial ROI & Narrative</h3>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-family: var(--font-mono); font-size: 0.85rem;">
                <div style="background: var(--bg-primary); padding: 8px; border-radius: 4px;">
                  <span style="color: var(--text-muted);">Total Spend:</span><br/>
                  <strong>$${(briefing.roi_breakdown.total_spend / 1000).toFixed(0)}k</strong>
                </div>
                <div style="background: var(--bg-primary); padding: 8px; border-radius: 4px;">
                  <span style="color: var(--text-muted);">Realized Value:</span><br/>
                  <strong>$${(briefing.roi_breakdown.total_realized_value / 1000).toFixed(0)}k</strong>
                </div>
              </div>
              <div style="background: var(--bg-secondary); border-left: 3px solid var(--accent-cyan); padding: 10px; font-size: 0.82rem; line-height: 1.4; color: var(--text-main); font-style: italic;">
                "${briefing.executive_takeaway || 'Autonomous reasoning engine has synthesized portfolio status without unmitigated critical bottlenecks.'}"
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  // --- 2. Single-Thing Focal Dashboard & Trade-Off ---
  async initFocal() {
    const thingSelect = document.getElementById("focal-thing-select");
    const refreshBtn = document.getElementById("focal-refresh-btn");
    const runTradeoffBtn = document.getElementById("run-tradeoff-btn");

    if (thingSelect) {
      thingSelect.addEventListener("change", () => this.refreshFocal());
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.refreshFocal());
    }

    if (runTradeoffBtn) {
      runTradeoffBtn.addEventListener("click", () => this.executeTradeoff());
    }
  },

  async refreshFocal() {
    const thingSelect = document.getElementById("focal-thing-select");
    if (!thingSelect || !thingSelect.value) return;

    try {
      const data = await BijouAPI.getThingFocalDashboard(thingSelect.value);
      this.renderFocal(data);
    } catch (err) {
      console.error("Failed to load focal dashboard:", err);
      const target = document.getElementById("focal-dashboard-target");
      if (target) {
        target.innerHTML = `<div style="color: var(--color-blocked); padding: 20px;">Failed to load focal dashboard: ${err.message}</div>`;
      }
    }
  },

  renderFocal(focal) {
    const target = document.getElementById("focal-dashboard-target");
    if (!target) return;

    target.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 1.3rem; color: var(--accent-cyan); font-weight: 700;">${focal.thing.title}</h2>
              <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">
                ${focal.thing.description || 'No description provided.'}
              </div>
            </div>
            <div style="text-align: right; font-family: var(--font-mono);">
              <span class="badge-pill">${focal.thing.lifecycle_status}</span>
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 6px;">
                Tier: ${focal.thing.tier} | Cost: $${(focal.thing.cost_estimate / 1000).toFixed(0)}k
              </div>
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="quadrant-card">
            <h3>Milestone Progression (${focal.milestones.length})</h3>
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
              ${focal.milestones.map(m => `
                <div style="background: var(--bg-primary); padding: 10px; border-radius: 4px; border-left: 3px solid ${m.state === 'ACHIEVED' ? 'var(--color-achieved)' : m.state === 'ACTIVE' ? 'var(--color-active)' : 'var(--color-locked)'}">
                  <div style="display: flex; justify-content: space-between;">
                    <strong>${m.title}</strong>
                    <span style="font-family: var(--font-mono); font-size: 0.75rem;">TRL ${m.trl}</span>
                  </div>
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; display: flex; justify-content: space-between;">
                    <span>Target: ${m.target_date || 'TBD'}</span>
                    <span>$${(m.cost_estimate / 1000).toFixed(0)}k</span>
                    <span>${m.state}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <div class="quadrant-card">
            <h3>Direct Causal Linkages</h3>
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
              <div>
                <strong style="font-size: 0.85rem; color: var(--accent-blue);">Upstream Predecessors (${focal.upstream_dependencies.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${focal.upstream_dependencies.length === 0 ? '<li style="color: var(--text-dim);">No upstream dependencies.</li>' : focal.upstream_dependencies.map(u => `<li>${u.title} (${u.thing_name})</li>`).join('')}
                </ul>
              </div>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--color-ready);">Downstream Unlocks (${focal.downstream_unlocks.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${focal.downstream_unlocks.length === 0 ? '<li style="color: var(--text-dim);">No downstream dependencies.</li>' : focal.downstream_unlocks.map(d => `<li>${d.title} (${d.thing_name})</li>`).join('')}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  async executeTradeoff() {
    const checkboxes = document.querySelectorAll(".tradeoff-candidate-checkbox:checked");
    const thingIds = Array.from(checkboxes).map(c => c.value);
    const target = document.getElementById("tradeoff-results-target");
    if (!target) return;

    if (thingIds.length === 0) {
      target.innerHTML = `<div style="color: var(--color-ready); padding: 10px;">Please select at least one candidate thing to evaluate trade-offs.</div>`;
      return;
    }

    try {
      const resp = await BijouAPI.evaluateTradeoff(thingIds);
      target.innerHTML = `
        <div style="margin-top: 16px; background: var(--bg-card); border-radius: 6px; padding: 14px;">
          <h4 style="color: var(--accent-cyan); margin-bottom: 8px;">Trade-Off Evaluation Results</h4>
          <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
            <thead>
              <tr style="text-align: left; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
                <th style="padding: 6px 0;">Rank</th>
                <th>Thing ID</th>
                <th>Cost</th>
                <th>Value</th>
                <th>Portfolio ROI Score</th>
              </tr>
            </thead>
            <tbody>
              ${resp.evaluated_candidates.map((c, i) => `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                  <td style="padding: 6px 0; font-weight: 700; color: var(--accent-cyan); font-family: var(--font-mono);">#${i + 1}</td>
                  <td>${c.thing_id}</td>
                  <td style="font-family: var(--font-mono);">$${(c.total_cost / 1000).toFixed(0)}k</td>
                  <td style="font-family: var(--font-mono);">$${(c.total_value / 1000).toFixed(0)}k</td>
                  <td style="font-family: var(--font-mono); font-weight: 700; color: var(--color-achieved);">${c.portfolio_roi_score}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } catch (err) {
      target.innerHTML = `<div style="color: var(--color-blocked); padding: 10px;">Trade-off evaluation failed: ${err.message}</div>`;
    }
  },

  // --- 3. Admin CRUD & JSON Manifest Import/Export ---
  async initCrud() {
    const exportBtn = document.getElementById("crud-export-btn");
    const importBtn = document.getElementById("crud-import-btn");
    const jsonArea = document.getElementById("crud-manifest-json");

    if (exportBtn) {
      exportBtn.addEventListener("click", async () => {
        try {
          const manifest = await BijouAPI.exportManifest();
          if (jsonArea) jsonArea.value = JSON.stringify(manifest, null, 2);
        } catch (err) {
          alert("Export failed: " + err.message);
        }
      });
    }

    if (importBtn) {
      importBtn.addEventListener("click", async () => {
        if (!jsonArea || !jsonArea.value) {
          alert("Please paste valid JSON manifest into the editor.");
          return;
        }
        const replaceAll = document.getElementById("crud-replace-all-checkbox")?.checked || false;
        try {
          const manifestData = JSON.parse(jsonArea.value);
          const res = await BijouAPI.importManifest(manifestData, replaceAll);
          alert(`Manifest imported successfully! (Imported: ${res.total_entities_imported || 'OK'})`);
          window.location.reload();
        } catch (err) {
          alert("Import failed: " + err.message);
        }
      });
    }

    // Quick Entity Creation Form
    const createOrgBtn = document.getElementById("crud-create-org-btn");
    if (createOrgBtn) {
      createOrgBtn.addEventListener("click", async () => {
        const id = document.getElementById("crud-org-id")?.value;
        const name = document.getElementById("crud-org-name")?.value;
        const echelon = document.getElementById("crud-org-echelon")?.value || "TACTICAL";
        if (!id || !name) {
          alert("Organization ID and Name are required.");
          return;
        }
        try {
          await BijouAPI.post("/api/v1/organizations", {
            id,
            name,
            echelon,
            sovereignty_domain: "CROSS_DOMAIN"
          });
          alert(`Organization ${name} created!`);
          window.location.reload();
        } catch (err) {
          alert("Create organization failed: " + err.message);
        }
      });
    }
  }
};
