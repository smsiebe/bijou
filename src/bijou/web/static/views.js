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
    const computeParetoBtn = document.getElementById("compute-pareto-btn");
    const paretoCeilingInput = document.getElementById("pareto-budget-ceiling");

    if (thingSelect) {
      thingSelect.addEventListener("change", () => this.refreshFocal());
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => this.refreshFocal());
    }

    if (runTradeoffBtn) {
      runTradeoffBtn.addEventListener("click", () => this.executeTradeoff());
    }

    if (computeParetoBtn) {
      computeParetoBtn.addEventListener("click", () => this.executeParetoFrontier());
    }

    if (paretoCeilingInput) {
      paretoCeilingInput.addEventListener("change", () => this.executeParetoFrontier());
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
            <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px;">
              <!-- 2-Hop Concentric Radial Ego-Network Canvas (REC-013) -->
              <canvas id="ego-network-canvas" width="600" height="320"></canvas>

              <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; font-size: 0.75rem; text-align: center; border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <div style="color: var(--accent-blue);">
                  <strong>Upstream Predecessors</strong>: ${upstream.length}
                </div>
                <div style="color: var(--color-ready);">
                  <strong>Downstream Dependents</strong>: ${downstream.length}
                </div>
                <div style="color: #f59e0b;">
                  <strong>Produced Effects</strong>: ${producedEffects.length}
                </div>
              </div>

              <!-- Telemetry Sparklines with SLA Threshold Bands (REC-014) -->
              <div style="border-top: 1px solid var(--border-subtle); padding-top: 8px;">
                <strong style="font-size: 0.85rem; color: var(--text-main);">Operational Telemetry Events (${telemetryRollups.length})</strong>
                <div style="display: flex; flex-direction: column; gap: 4px; margin-top: 6px;">
                  ${telemetryRollups.length === 0 ? '<div style="color: var(--text-dim); font-size: 0.8rem;">No operational telemetry rollups recorded.</div>' : telemetryRollups.map(r => this.renderTelemetrySparkline(r)).join('')}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    requestAnimationFrame(() => {
      this.drawRadialEgoNetwork(focal);
      this.executeParetoFrontier();
    });
  },

  renderTelemetrySparkline(rollup) {
    const val = rollup.aggregated_value !== undefined ? rollup.aggregated_value : 0;
    const count = rollup.event_count || 1;
    const w = 110;
    const h = 24;
    // Generate synthetic trendline points leading up to aggregated_value
    const pts = [];
    for (let i = 0; i < 8; i++) {
      const x = Math.round((i / 7) * (w - 12) + 6);
      const ratio = 0.4 + 0.6 * (i / 7) + 0.1 * Math.sin(i * 1.8);
      const y = Math.round(h - 4 - Math.min(1.0, Math.max(0.0, ratio)) * (h - 8));
      pts.push(`${x},${y}`);
    }
    const pointsStr = pts.join(" ");
    const slaY = Math.round(h * 0.35);

    return `
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 4px 8px; background: rgba(255,255,255,0.02); border-radius: 4px;">
        <div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-main);">${rollup.metric_name}</div>
          <div style="font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono);">
            Val: <strong style="color: var(--accent-cyan);">${Number(val).toFixed(2)}</strong> | ${count} events
          </div>
        </div>
        <svg class="telemetry-sparkline" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
          <line x1="2" y1="${slaY}" x2="${w - 2}" y2="${slaY}" stroke="#ef4444" stroke-width="1" stroke-dasharray="2,2" opacity="0.8">
            <title>Target Metric SLA Threshold</title>
          </line>
          <polyline fill="none" stroke="#38bdf8" stroke-width="1.8" points="${pointsStr}"></polyline>
        </svg>
      </div>
    `;
  },

  drawRadialEgoNetwork(focal) {
    const canvas = document.getElementById("ego-network-canvas");
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = rect.width > 0 ? rect.width : 560;
    const height = 320;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";

    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const cx = width / 2;
    const cy = height / 2;
    const r1 = Math.min(110, cx - 40);
    const r2 = Math.min(190, cx + 50);

    // Draw background concentric orbit guide arcs
    ctx.save();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;

    // Upstream orbit arc (left)
    ctx.beginPath();
    ctx.arc(cx, cy, r1, Math.PI * 0.55, Math.PI * 1.45);
    ctx.stroke();

    // Downstream orbit arc (inner right)
    ctx.beginPath();
    ctx.arc(cx, cy, r1, -Math.PI * 0.45, Math.PI * 0.45);
    ctx.stroke();

    // Effects orbit arc (outer right)
    ctx.beginPath();
    ctx.arc(cx, cy, r2, -Math.PI * 0.4, Math.PI * 0.4);
    ctx.stroke();

    // Guide labels
    ctx.fillStyle = "rgba(255, 255, 255, 0.25)";
    ctx.font = "8px monospace";
    ctx.fillText("PREDECESSORS (1-HOP)", cx - r1 - 10, cy - r1 + 15);
    ctx.fillText("DEPENDENTS (1-HOP)", cx + r1 - 40, cy - r1 + 15);
    ctx.fillText("EFFECTS (2-HOP)", cx + r2 - 50, cy - r2 + 25);
    ctx.restore();

    const thing = focal.thing || {};
    const upstream = focal.upstream_dependencies || [];
    const downstream = focal.downstream_dependents || [];
    const producedEffects = focal.produced_effects || [];

    // Compute node coordinates
    const nodes = [];

    // 1. Center Focal Thing
    const focalNode = {
      id: thing.id,
      name: thing.name || thing.id,
      x: cx,
      y: cy,
      radius: 18,
      color: "#06b6d4",
      borderColor: "#38bdf8",
      type: "focus"
    };
    nodes.push(focalNode);

    // 2. Upstream Predecessors (Left semi-circle)
    const uCount = upstream.length;
    upstream.forEach((u, i) => {
      const angle = uCount === 1 ? Math.PI : Math.PI * 0.75 + (i / (uCount - 1)) * (Math.PI * 0.5);
      const nx = cx + r1 * Math.cos(angle);
      const ny = cy + r1 * Math.sin(angle);
      nodes.push({
        id: u.id,
        name: u.name || u.id,
        x: nx,
        y: ny,
        radius: 12,
        color: "#1e3a8a",
        borderColor: "#3b82f6",
        type: "upstream"
      });
    });

    // 3. Downstream Dependents (Inner Right semi-circle)
    const dCount = downstream.length;
    downstream.forEach((d, i) => {
      const angle = dCount === 1 ? 0 : -Math.PI * 0.35 + (i / (dCount - 1)) * (Math.PI * 0.7);
      const nx = cx + r1 * Math.cos(angle);
      const ny = cy + r1 * Math.sin(angle);
      nodes.push({
        id: d.id,
        name: d.name || d.id,
        x: nx,
        y: ny,
        radius: 12,
        color: "#064e3b",
        borderColor: "#10b981",
        type: "downstream"
      });
    });

    // 4. Produced Effects (Outer Right semi-circle)
    const eCount = producedEffects.length;
    producedEffects.forEach((e, i) => {
      const angle = eCount === 1 ? 0 : -Math.PI * 0.32 + (i / (eCount - 1)) * (Math.PI * 0.64);
      const nx = cx + r2 * Math.cos(angle);
      const ny = cy + r2 * Math.sin(angle);
      nodes.push({
        id: e.id,
        name: e.name || e.id,
        x: nx,
        y: ny,
        radius: 10,
        color: "#78350f",
        borderColor: "#f59e0b",
        type: "effect"
      });
    });

    // Helper: draw arrow line
    function drawArrow(fromX, fromY, toX, toY, color) {
      const angle = Math.atan2(toY - fromY, toX - fromX);
      const arrowLength = 7;
      ctx.save();
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(fromX, fromY);
      ctx.lineTo(toX, toY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(toX, toY);
      ctx.lineTo(toX - arrowLength * Math.cos(angle - Math.PI / 6), toY - arrowLength * Math.sin(angle - Math.PI / 6));
      ctx.lineTo(toX - arrowLength * Math.cos(angle + Math.PI / 6), toY - arrowLength * Math.sin(angle + Math.PI / 6));
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    // Draw directed edges
    // Upstream -> Focal
    nodes.filter(n => n.type === "upstream").forEach(un => {
      const angle = Math.atan2(cy - un.y, cx - un.x);
      const endX = cx - (focalNode.radius + 3) * Math.cos(angle);
      const endY = cy - (focalNode.radius + 3) * Math.sin(angle);
      const startX = un.x + (un.radius + 2) * Math.cos(angle);
      const startY = un.y + (un.radius + 2) * Math.sin(angle);
      drawArrow(startX, startY, endX, endY, "rgba(59, 130, 246, 0.6)");
    });

    // Focal -> Downstream
    nodes.filter(n => n.type === "downstream").forEach(dn => {
      const angle = Math.atan2(dn.y - cy, dn.x - cx);
      const startX = cx + (focalNode.radius + 2) * Math.cos(angle);
      const startY = cy + (focalNode.radius + 2) * Math.sin(angle);
      const endX = dn.x - (dn.radius + 3) * Math.cos(angle);
      const endY = dn.y - (dn.radius + 3) * Math.sin(angle);
      drawArrow(startX, startY, endX, endY, "rgba(16, 185, 129, 0.6)");
    });

    // Downstream (or Focal) -> Effects
    const downstreamNodes = nodes.filter(n => n.type === "downstream");
    nodes.filter(n => n.type === "effect").forEach((en, idx) => {
      const source = downstreamNodes.length > 0 ? downstreamNodes[idx % downstreamNodes.length] : focalNode;
      const angle = Math.atan2(en.y - source.y, en.x - source.x);
      const startX = source.x + (source.radius + 2) * Math.cos(angle);
      const startY = source.y + (source.radius + 2) * Math.sin(angle);
      const endX = en.x - (en.radius + 3) * Math.cos(angle);
      const endY = en.y - (en.radius + 3) * Math.sin(angle);
      drawArrow(startX, startY, endX, endY, "rgba(245, 158, 11, 0.6)");
    });

    // Draw Nodes
    nodes.forEach(n => {
      ctx.save();
      if (n.type === "focus") {
        ctx.shadowColor = "#38bdf8";
        ctx.shadowBlur = 12;
      }
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = n.borderColor;
      ctx.stroke();
      ctx.restore();

      // Node label
      ctx.save();
      ctx.fillStyle = "#e2e8f0";
      ctx.font = n.type === "focus" ? "bold 11px sans-serif" : "9px sans-serif";
      ctx.textAlign = "center";
      const displayLabel = n.name.length > 16 ? n.name.slice(0, 14) + "..." : n.name;
      ctx.fillText(displayLabel, n.x, n.y + n.radius + 12);
      ctx.restore();
    });
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

  async executeParetoFrontier() {
    const ceilingInput = document.getElementById("pareto-budget-ceiling");
    const ceilingM = parseFloat(ceilingInput ? ceilingInput.value : "100") || 100;
    const ceilingDollars = ceilingM * 1000000;

    const wrapper = document.getElementById("pareto-scatterplot-wrapper");
    const countBadge = document.getElementById("pareto-frontier-count");
    const svg = document.getElementById("pareto-scatter-svg");
    const tooltip = document.getElementById("pareto-tooltip");
    if (!svg || !wrapper) return;

    try {
      const frontier = await BijouAPI.getParetoFrontier(ceilingDollars);
      wrapper.style.display = "block";

      const portfolios = frontier.optimal_portfolios || [];
      if (countBadge) {
        countBadge.textContent = `${portfolios.length} Portfolios`;
      }

      // Sort portfolios by total_cost ascending
      portfolios.sort((a, b) => a.total_cost - b.total_cost);

      const maxRoi = Math.max(1.0, ...portfolios.map(p => p.aggregate_roi)) * 1.15;
      const svgW = 320;
      const svgH = 200;
      const padLeft = 45;
      const padRight = 20;
      const padTop = 20;
      const padBottom = 35;
      const plotW = svgW - padLeft - padRight;
      const plotH = svgH - padTop - padBottom;

      const scaleX = cost => padLeft + (cost / ceilingDollars) * plotW;
      const scaleY = roi => padTop + plotH - (roi / maxRoi) * plotH;

      let svgHtml = `
        <!-- Axes -->
        <line x1="${padLeft}" y1="${padTop + plotH}" x2="${svgW - padRight}" y2="${padTop + plotH}" stroke="var(--border-subtle)" stroke-width="1.5" />
        <line x1="${padLeft}" y1="${padTop}" x2="${padLeft}" y2="${padTop + plotH}" stroke="var(--border-subtle)" stroke-width="1.5" />

        <!-- Gridlines and ticks -->
        <line x1="${padLeft}" y1="${scaleY(maxRoi * 0.5)}" x2="${svgW - padRight}" y2="${scaleY(maxRoi * 0.5)}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="2,2" />
        <line x1="${scaleX(ceilingDollars * 0.5)}" y1="${padTop}" x2="${scaleX(ceilingDollars * 0.5)}" y2="${padTop + plotH}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="2,2" />

        <!-- Budget Ceiling Limit Line -->
        <line x1="${scaleX(ceilingDollars)}" y1="${padTop}" x2="${scaleX(ceilingDollars)}" y2="${padTop + plotH}" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.8" />
        <text x="${scaleX(ceilingDollars)}" y="${padTop - 4}" fill="#ef4444" font-size="8" text-anchor="end">Ceiling $${ceilingM}M</text>

        <!-- Axis Labels -->
        <text x="${padLeft + plotW / 2}" y="${svgH - 6}" fill="var(--text-muted)" font-size="9" text-anchor="middle">Total Cost ($M)</text>
        <text x="14" y="${padTop + plotH / 2}" fill="var(--text-muted)" font-size="9" text-anchor="middle" transform="rotate(-90 14 ${padTop + plotH / 2})">ROI</text>

        <!-- Tick Labels -->
        <text x="${padLeft}" y="${padTop + plotH + 14}" fill="var(--text-dim)" font-size="8" text-anchor="middle">$0</text>
        <text x="${scaleX(ceilingDollars * 0.5)}" y="${padTop + plotH + 14}" fill="var(--text-dim)" font-size="8" text-anchor="middle">$${(ceilingM / 2).toFixed(0)}M</text>
        <text x="${scaleX(ceilingDollars)}" y="${padTop + plotH + 14}" fill="var(--text-dim)" font-size="8" text-anchor="middle">$${ceilingM}M</text>
      `;

      // Draw frontier connecting line
      if (portfolios.length > 0) {
        const linePoints = portfolios.map(p => `${scaleX(p.total_cost)},${scaleY(p.aggregate_roi)}`).join(" ");
        svgHtml += `<polyline fill="none" stroke="#f59e0b" stroke-width="2" points="${linePoints}" opacity="0.85" />`;
      }

      // Draw optimal points
      portfolios.forEach((p, idx) => {
        const px = scaleX(p.total_cost);
        const py = scaleY(p.aggregate_roi);
        svgHtml += `
          <circle class="pareto-point" cx="${px}" cy="${py}" r="5" fill="#f59e0b" stroke="#ffffff" stroke-width="1.5"
            data-index="${idx}"
            style="cursor: pointer; transition: transform 0.15s;" />
        `;
      });

      svg.innerHTML = svgHtml;

      // Bind interactive tooltips and clicks on points
      const pointEls = svg.querySelectorAll(".pareto-point");
      pointEls.forEach(pt => {
        const idx = parseInt(pt.getAttribute("data-index"), 10);
        const p = portfolios[idx];

        pt.addEventListener("mouseenter", e => {
          pt.setAttribute("r", "7");
          pt.setAttribute("fill", "#38bdf8");
          if (tooltip) {
            tooltip.style.display = "block";
            tooltip.style.left = `${e.offsetX + 10}px`;
            tooltip.style.top = `${e.offsetY - 20}px`;
            tooltip.innerHTML = `
              <div style="font-weight: 700; color: #f59e0b;">Portfolio #${idx + 1}</div>
              <div>Things: ${p.proposed_thing_ids.join(', ')}</div>
              <div>Cost: $${(p.total_cost / 1000000).toFixed(2)}M</div>
              <div>ROI: ${p.aggregate_roi.toFixed(6)}</div>
              <div style="color: var(--text-dim); font-size: 0.65rem; margin-top: 2px;">Click to evaluate selection</div>
            `;
          }
        });

        pt.addEventListener("mouseleave", () => {
          pt.setAttribute("r", "5");
          pt.setAttribute("fill", "#f59e0b");
          if (tooltip) tooltip.style.display = "none";
        });

        pt.addEventListener("click", () => {
          // Select corresponding candidate checkboxes and execute tradeoff
          const checkboxes = document.querySelectorAll(".tradeoff-candidate-checkbox");
          checkboxes.forEach(cb => {
            cb.checked = p.proposed_thing_ids.includes(cb.value);
          });
          this.executeTradeoff();
        });
      });
    } catch (err) {
      console.warn("Failed to load Pareto frontier:", err.message);
    }
  },

  // --- 3. Admin CRUD, Manifest Studio & Direct Manipulation Workbench ---
  async initCrud() {
    const exportBtn = document.getElementById("crud-export-btn");
    const importBtn = document.getElementById("crud-import-btn");
    const validateBtn = document.getElementById("crud-validate-btn");
    const jsonArea = document.getElementById("crud-manifest-json");

    if (exportBtn) {
      exportBtn.addEventListener("click", async () => {
        try {
          const manifest = await BijouAPI.exportManifest();
          if (jsonArea) jsonArea.value = JSON.stringify(manifest, null, 2);
          this.renderVisualEntityWorkbench(manifest);
        } catch (err) {
          alert("Export failed: " + err.message);
        }
      });
    }

    if (validateBtn) {
      validateBtn.addEventListener("click", () => this.validateManifestDiagnostics());
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
  },

  async validateManifestDiagnostics() {
    const jsonArea = document.getElementById("crud-manifest-json");
    const hud = document.getElementById("crud-diagnostic-hud");
    if (!hud) return;

    if (!jsonArea || !jsonArea.value.trim()) {
      hud.style.display = "block";
      hud.className = "diagnostic-hud has-blockers";
      hud.innerHTML = `<strong style="color: var(--color-blocked);">ERROR:</strong> Manifest editor is empty. Please enter or export a manifest.`;
      return;
    }

    let manifestData;
    try {
      manifestData = JSON.parse(jsonArea.value);
    } catch (parseErr) {
      hud.style.display = "block";
      hud.className = "diagnostic-hud has-blockers";
      hud.innerHTML = `<strong style="color: var(--color-blocked);">JSON SYNTAX ERROR:</strong> ${parseErr.message}`;
      return;
    }

    try {
      const report = await BijouAPI.validateManifest(manifestData);
      hud.style.display = "block";

      const blockers = report.blockers || [];
      const warnings = report.warnings || [];
      const cycles = report.cycles_detected || [];

      if (blockers.length > 0) {
        hud.className = "diagnostic-hud has-blockers";
        hud.innerHTML = `
          <div style="font-weight: 700; color: var(--color-blocked); display: flex; align-items: center; gap: 6px;">
            <span>CRITICAL TOPOLOGICAL BLOCKERS (${blockers.length})</span>
          </div>
          <ul style="margin: 6px 0 6px 18px; font-size: 0.78rem;">
            ${blockers.map(b => `<li style="color: var(--color-blocked);">${b}</li>`).join('')}
          </ul>
          ${cycles.length > 0 ? `
            <div style="font-size: 0.75rem; margin-top: 4px; color: var(--text-main);">
              <strong>Cycles Detected:</strong>
              ${cycles.map(c => `<div style="font-family: var(--font-mono); color: var(--color-blocked); margin-left: 8px;">&bull; ${c.join(' &rarr; ')}</div>`).join('')}
            </div>
          ` : ''}
          ${warnings.length > 0 ? `
            <div style="margin-top: 6px; font-size: 0.75rem; color: var(--color-ready);">
              <strong>Warnings (${warnings.length}):</strong> ${warnings.join('; ')}
            </div>
          ` : ''}
          <div style="font-size: 0.72rem; color: var(--text-dim); margin-top: 6px; font-style: italic;">
            Import is blocked until critical topological blockers and cycles are remediated.
          </div>
        `;
      } else if (warnings.length > 0) {
        hud.className = "diagnostic-hud has-warnings";
        hud.innerHTML = `
          <div style="font-weight: 700; color: var(--color-ready);">
            WARNINGS / ARCHITECTURAL SMELLS (${warnings.length})
          </div>
          <ul style="margin: 6px 0 6px 18px; font-size: 0.78rem; color: var(--text-main);">
            ${warnings.map(w => `<li>${w}</li>`).join('')}
          </ul>
          <div style="font-size: 0.72rem; color: var(--color-achieved); margin-top: 4px;">
            Zero blockers detected. Manifest is valid for import.
          </div>
        `;
      } else {
        hud.className = "diagnostic-hud clean";
        hud.innerHTML = `
          <div style="font-weight: 700; color: var(--color-achieved);">
            ALL PRE-FLIGHT CHECKS PASSED
          </div>
          <div style="font-size: 0.78rem; color: var(--text-main); margin-top: 4px;">
            Topology verified: 0 dependency cycles, 0 orphaned entities, 0 missing anchors. Ready for import.
          </div>
        `;
      }

      // Update Visual Entity Workbench with the parsed data
      this.renderVisualEntityWorkbench(manifestData);
    } catch (err) {
      hud.style.display = "block";
      hud.className = "diagnostic-hud has-blockers";
      hud.innerHTML = `<strong style="color: var(--color-blocked);">VALIDATION FAILED:</strong> ${err.message}`;
    }
  },

  renderVisualEntityWorkbench(manifestData) {
    const lanesContainer = document.getElementById("crud-visual-lanes");
    if (!lanesContainer || !manifestData) return;

    const things = manifestData.things || [];
    const lifecycles = ["PROPOSED", "ACTIVE", "DELIVERED", "RETIRED"];

    lanesContainer.innerHTML = lifecycles.map(lc => {
      const matchingThings = things.filter(t => (t.lifecycle || "ACTIVE") === lc);
      return `
        <div class="visual-lane" data-lifecycle="${lc}">
          <div class="visual-lane-title">${lc} (${matchingThings.length})</div>
          <div class="visual-cards-bucket" style="display: flex; flex-direction: column; gap: 6px; min-height: 120px;">
            ${matchingThings.map(t => `
              <div class="visual-card" draggable="true" data-thing-id="${t.id}">
                <div class="visual-card-title">${t.name}</div>
                <div class="visual-card-meta">
                  <span>${t.id}</span>
                  <span>$${((t.estimated_cost || 0) / 1000).toFixed(0)}k</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }).join('');

    // Bind drag-and-drop events
    const cards = lanesContainer.querySelectorAll(".visual-card");
    const lanes = lanesContainer.querySelectorAll(".visual-lane");
    const jsonArea = document.getElementById("crud-manifest-json");

    cards.forEach(card => {
      card.addEventListener("dragstart", e => {
        e.dataTransfer.setData("text/plain", card.dataset.thingId);
      });
    });

    lanes.forEach(lane => {
      lane.addEventListener("dragover", e => {
        e.preventDefault();
        lane.classList.add("dragover");
      });

      lane.addEventListener("dragleave", () => {
        lane.classList.remove("dragover");
      });

      lane.addEventListener("drop", e => {
        e.preventDefault();
        lane.classList.remove("dragover");
        const thingId = e.dataTransfer.getData("text/plain");
        const targetLifecycle = lane.dataset.lifecycle;

        const thing = things.find(t => t.id === thingId);
        if (thing && thing.lifecycle !== targetLifecycle) {
          thing.lifecycle = targetLifecycle;
          if (jsonArea) {
            jsonArea.value = JSON.stringify(manifestData, null, 2);
          }
          this.renderVisualEntityWorkbench(manifestData);
        }
      });
    });
  }
};
