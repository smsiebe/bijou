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

    const subjectOrg = briefing.subject_org_id;
    const perspectiveOrg = briefing.perspective_org_id || "Self (Direct Sovereign)";
    const asOf = briefing.as_of_date || new Date().toISOString().split("T")[0];

    const supportedConcerns = briefing.supported_concerns || [];
    const ownedThings = briefing.owned_things || [];
    const crossOrgDeps = briefing.cross_org_dependencies || [];
    const gaps = briefing.strategic_gaps || [];

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
            <div style="font-size: 1.5rem; font-weight: 800; color: var(--color-achieved);">${briefing.portfolio_roi_score}</div>
          </div>
        </div>

        <div class="briefing-quadrants">
          <!-- Quadrants 1 & 2: Sankey Value Stream (Owned Things -> Supported Concerns) -->
          <div class="sankey-stream-container">
            <!-- Left: Owned Things -->
            <div class="sankey-column quadrant-card" style="text-align: left;">
              <h3>1. Owned Things (${ownedThings.length} Assets)</h3>
              <div style="max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                ${ownedThings.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">No things owned under this lens.</div>' : `
                  ${ownedThings.map(t => `
                    <div class="sankey-node-item sankey-thing-card" data-thing-id="${t.id}">
                      <div style="font-weight: 700; font-size: 0.85rem;">${t.name}</div>
                      <div style="display: flex; gap: 8px; font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                        <span class="badge-pill" style="font-size: 0.65rem;">${t.lifecycle}</span>
                        <span style="font-family: var(--font-mono);">$${(t.estimated_cost / 1000).toFixed(0)}k</span>
                      </div>
                    </div>
                  `).join('')}
                `}
              </div>
            </div>

            <!-- SVG layer for Bezier curves -->
            <svg class="sankey-svg-layer" id="sankey-connections-svg"></svg>

            <!-- Right: Supported Concerns -->
            <div class="sankey-column quadrant-card" style="text-align: right;">
              <h3>2. Supported Concerns (${supportedConcerns.length} Objectives)</h3>
              <div style="max-height: 240px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
                ${supportedConcerns.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">No supported concerns aligned.</div>' : `
                  ${supportedConcerns.map(c => `
                    <div class="sankey-node-item sankey-concern-card" data-concern-id="${c.concern_id}" data-contributors="${(c.contributing_thing_ids || []).join(',')}">
                      <div style="font-weight: 700; font-size: 0.85rem;">${c.concern_name}</div>
                      <div style="display: flex; justify-content: flex-end; gap: 8px; font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">
                        <span style="font-size: 0.75rem; color: ${c.priority >= 0.8 ? 'var(--color-blocked)' : 'var(--color-ready)'}">P: ${c.priority}</span>
                        <span class="badge-pill" style="font-size: 0.65rem;">${(c.coverage_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  `).join('')}
                `}
              </div>
            </div>
          </div>

          <!-- Quadrant 3: Cross-Org Dependencies -->
          <div class="quadrant-card">
            <h3>3. Cross-Org Dependencies (${crossOrgDeps.length})</h3>
            <div style="max-height: 220px; overflow-y: auto;">
              ${crossOrgDeps.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.85rem;">Zero cross-organization dependencies detected.</div>' : `
                <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse;">
                  <thead>
                    <tr style="text-align: left; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);">
                      <th style="padding: 4px 0;">Source</th>
                      <th>Target</th>
                      <th>Relationship</th>
                      <th>Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${crossOrgDeps.map(d => `
                      <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 6px 0;">${d.source_id}</td>
                        <td>${d.target_id}</td>
                        <td style="font-family: var(--font-mono); font-size: 0.7rem;">${d.relationship}</td>
                        <td style="font-family: var(--font-mono); font-size: 0.75rem;">${d.weight}</td>
                      </tr>
                    `).join('')}
                  </tbody>
                </table>
              `}
            </div>
          </div>

          <!-- Quadrant 4: Total Committed Cost & Narrative -->
          <div class="quadrant-card">
            <h3>4. Committed Cost & Executive Narrative</h3>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              <div style="font-family: var(--font-mono); font-size: 0.85rem;">
                <div style="background: var(--bg-primary); padding: 8px; border-radius: 4px;">
                  <span style="color: var(--text-muted);">Total Committed Cost:</span><br/>
                  <strong style="font-size: 1.1rem; color: var(--accent-cyan);">$${(briefing.total_committed_cost / 1000).toFixed(0)}k</strong>
                </div>
              </div>
              <div style="background: var(--bg-secondary); border-left: 3px solid var(--accent-cyan); padding: 10px; font-size: 0.82rem; line-height: 1.4; color: var(--text-main); font-style: italic;">
                "${briefing.executive_summary_narrative || 'Autonomous reasoning engine has synthesized portfolio status without unmitigated critical bottlenecks.'}"
              </div>
              ${gaps.length > 0 ? `
                <div style="font-size: 0.78rem; color: var(--color-blocked);">
                  <strong>Strategic Gaps:</strong> ${gaps.join("; ")}
                </div>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `;

    // Render Sankey Bezier value streams and bind coordinated brushing (REC-009, REC-011)
    requestAnimationFrame(() => {
      this.drawSankeyPaths(container, briefing);
      this.bindSankeyBrushing(container);
    });
  },

  drawSankeyPaths(container, briefing) {
    const svg = container.querySelector("#sankey-connections-svg");
    const streamContainer = container.querySelector(".sankey-stream-container");
    if (!svg || !streamContainer) return;

    const streamRect = streamContainer.getBoundingClientRect();
    if (streamRect.width === 0 || streamRect.height === 0) return;

    svg.setAttribute("width", streamRect.width);
    svg.setAttribute("height", streamRect.height);
    svg.setAttribute("viewBox", `0 0 ${streamRect.width} ${streamRect.height}`);

    const thingCards = streamContainer.querySelectorAll(".sankey-thing-card");
    const concernCards = streamContainer.querySelectorAll(".sankey-concern-card");

    const thingCoords = new Map();
    thingCards.forEach(card => {
      const id = card.dataset.thingId;
      if (id) {
        const r = card.getBoundingClientRect();
        thingCoords.set(id, {
          x: r.right - streamRect.left,
          y: r.top + r.height / 2 - streamRect.top,
        });
      }
    });

    let pathsHtml = "";
    concernCards.forEach(card => {
      const concernId = card.dataset.concernId;
      const contributors = (card.dataset.contributors || "").split(",").filter(Boolean);
      const r = card.getBoundingClientRect();
      const x2 = r.left - streamRect.left;
      const y2 = r.top + r.height / 2 - streamRect.top;

      contributors.forEach(thingId => {
        const pt1 = thingCoords.get(thingId);
        if (pt1) {
          const x1 = pt1.x;
          const y1 = pt1.y;
          const dx = Math.max(30, (x2 - x1) * 0.5);
          const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
          pathsHtml += `<path class="sankey-stream-path" d="${d}" data-thing-id="${thingId}" data-concern-id="${concernId}"></path>`;
        }
      });
    });

    svg.innerHTML = pathsHtml;
  },

  bindSankeyBrushing(container) {
    const streamContainer = container.querySelector(".sankey-stream-container");
    if (!streamContainer) return;

    const thingCards = streamContainer.querySelectorAll(".sankey-thing-card");
    const concernCards = streamContainer.querySelectorAll(".sankey-concern-card");
    const paths = streamContainer.querySelectorAll(".sankey-stream-path");

    // Coordinated Brushing on Concerns
    concernCards.forEach(card => {
      const concernId = card.dataset.concernId;
      const contributors = (card.dataset.contributors || "").split(",").filter(Boolean);

      card.addEventListener("mouseenter", () => {
        paths.forEach(p => {
          if (p.dataset.concernId === concernId) {
            p.style.opacity = "1";
            p.style.stroke = "var(--accent-cyan)";
            p.style.strokeWidth = "3.5px";
          } else {
            p.style.opacity = "0.15";
          }
        });
        thingCards.forEach(tc => {
          if (contributors.includes(tc.dataset.thingId)) {
            tc.style.borderColor = "var(--accent-cyan)";
            tc.style.boxShadow = "0 0 10px rgba(56, 189, 248, 0.4)";
            tc.style.opacity = "1";
          } else {
            tc.style.opacity = "0.35";
          }
        });
      });

      card.addEventListener("mouseleave", () => {
        paths.forEach(p => {
          p.style.opacity = "";
          p.style.stroke = "";
          p.style.strokeWidth = "";
        });
        thingCards.forEach(tc => {
          tc.style.borderColor = "";
          tc.style.boxShadow = "";
          tc.style.opacity = "";
        });
      });
    });

    // Coordinated Brushing on Things
    thingCards.forEach(card => {
      const thingId = card.dataset.thingId;

      card.addEventListener("mouseenter", () => {
        const activeConcerns = new Set();
        paths.forEach(p => {
          if (p.dataset.thingId === thingId) {
            p.style.opacity = "1";
            p.style.stroke = "var(--color-achieved)";
            p.style.strokeWidth = "3.5px";
            activeConcerns.add(p.dataset.concernId);
          } else {
            p.style.opacity = "0.15";
          }
        });
        concernCards.forEach(cc => {
          if (activeConcerns.has(cc.dataset.concernId)) {
            cc.style.borderColor = "var(--color-achieved)";
            cc.style.boxShadow = "0 0 10px rgba(16, 185, 129, 0.4)";
            cc.style.opacity = "1";
          } else {
            cc.style.opacity = "0.35";
          }
        });
      });

      card.addEventListener("mouseleave", () => {
        paths.forEach(p => {
          p.style.opacity = "";
          p.style.stroke = "";
          p.style.strokeWidth = "";
        });
        concernCards.forEach(cc => {
          cc.style.borderColor = "";
          cc.style.boxShadow = "";
          cc.style.opacity = "";
        });
      });
    });
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

    const thing = focal.thing || {};
    const milestones = thing.milestones || [];
    const upstream = focal.upstream_dependencies || [];
    const downstream = focal.downstream_dependents || [];
    const producedEffects = focal.produced_effects || [];
    const telemetryRollups = focal.telemetry_rollups || [];

    target.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <div style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <h2 style="font-size: 1.3rem; color: var(--accent-cyan); font-weight: 700;">${thing.name}</h2>
              <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">
                ${thing.description || 'No description provided.'}
              </div>
            </div>
            <div style="text-align: right; font-family: var(--font-mono);">
              <span class="badge-pill">${thing.lifecycle}</span>
              <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 6px;">
                Cost: $${((thing.estimated_cost || 0) / 1000).toFixed(0)}k | ROI: ${focal.direct_roi}
              </div>
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
          <div class="quadrant-card">
            <h3>Milestone Progression (${milestones.length})</h3>
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
              ${milestones.map(m => `
                <div style="background: var(--bg-primary); padding: 10px; border-radius: 4px; border-left: 3px solid ${m.status === 'ACHIEVED' ? 'var(--color-achieved)' : m.status === 'IN_PROGRESS' ? 'var(--color-active)' : 'var(--color-locked)'}">
                  <div style="display: flex; justify-content: space-between;">
                    <strong>${m.name}</strong>
                    <span style="font-family: var(--font-mono); font-size: 0.75rem;">TRL ${m.trl}</span>
                  </div>
                  <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; display: flex; justify-content: space-between;">
                    <span>Target: ${m.target_date || 'TBD'}</span>
                    <span>Cost Delta: $${((m.cost_delta || 0) / 1000).toFixed(0)}k</span>
                    <span>${m.status}</span>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>

          <div class="quadrant-card">
            <h3>Direct Causal Linkages</h3>
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px;">
              <div>
                <strong style="font-size: 0.85rem; color: var(--accent-blue);">Upstream Predecessors (${upstream.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${upstream.length === 0 ? '<li style="color: var(--text-dim);">No upstream dependencies.</li>' : upstream.map(u => `<li>${u.name} (${u.id})</li>`).join('')}
                </ul>
              </div>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--color-ready);">Downstream Dependents (${downstream.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${downstream.length === 0 ? '<li style="color: var(--text-dim);">No downstream dependents.</li>' : downstream.map(d => `<li>${d.name} (${d.id})</li>`).join('')}
                </ul>
              </div>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--accent-cyan);">Produced Effects (${producedEffects.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${producedEffects.length === 0 ? '<li style="color: var(--text-dim);">No produced effects.</li>' : producedEffects.map(e => `<li>${e.name} (${e.id}) [Observed: ${e.observed_value !== null ? e.observed_value : 'N/A'}]</li>`).join('')}
                </ul>
              </div>
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--text-main);">Telemetry Rollups (${telemetryRollups.length})</strong>
                <ul style="font-size: 0.8rem; margin-top: 4px; padding-left: 20px;">
                  ${telemetryRollups.length === 0 ? '<li style="color: var(--text-dim);">No operational telemetry events.</li>' : telemetryRollups.map(r => `<li>${r.metric_name}: ${r.aggregated_value} (${r.event_count} events)</li>`).join('')}
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
      const deltas = resp.concern_coverage_deltas || {};
      const deltaEntries = Object.entries(deltas);
      const unlocked = resp.unlocked_effect_ids || [];

      target.innerHTML = `
        <div style="margin-top: 16px; background: var(--bg-card); border-radius: 6px; padding: 14px;">
          <h4 style="color: var(--accent-cyan); margin-bottom: 8px;">Trade-Off Evaluation Results</h4>
          <div style="font-family: var(--font-mono); font-size: 0.85rem; display: flex; flex-direction: column; gap: 6px;">
            <div><strong>Proposed Things:</strong> ${resp.proposed_thing_ids.join(', ')}</div>
            <div><strong>Total Cost:</strong> $${((resp.total_cost || 0) / 1000).toFixed(0)}k</div>
            <div><strong>Aggregate ROI:</strong> <span style="color: var(--color-achieved); font-weight: 700;">${resp.aggregate_roi}</span></div>
            <div><strong>Unlocked Effects:</strong> ${unlocked.length > 0 ? unlocked.join(', ') : 'None'}</div>
          </div>
          ${deltaEntries.length > 0 ? `
            <div style="margin-top: 10px;">
              <strong style="font-size: 0.8rem; color: var(--text-muted);">Concern Coverage Deltas:</strong>
              <table style="width: 100%; font-size: 0.8rem; border-collapse: collapse; margin-top: 4px;">
                <tbody>
                  ${deltaEntries.map(([cId, val]) => `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                      <td style="padding: 4px 0;">${cId}</td>
                      <td style="text-align: right; font-family: var(--font-mono); color: var(--color-ready);">+${(val * 100).toFixed(0)}%</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          ` : ''}
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
          const thingsCount = res.things || 0;
          const orgsCount = res.organizations || 0;
          alert(`Manifest imported successfully! (Imported: ${thingsCount} things, ${orgsCount} organizations)`);
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
        const echelonInput = document.getElementById("crud-org-echelon")?.value || "1";
        const mission = document.getElementById("crud-org-mission")?.value || "";
        if (!id || !name) {
          alert("Organization ID and Name are required.");
          return;
        }
        try {
          await BijouAPI.post("/api/v1/organizations", {
            id,
            name,
            echelon_level: parseInt(echelonInput, 10),
            mission_statement: mission
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
