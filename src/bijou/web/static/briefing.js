/* ==========================================================================
   Bijou v2 Lens 2: Templatable 1-Slide Executive Briefing Engine
   Supports Organization & Effort scopes, declarative product templates,
   and pure-SVG multi-hop relationship & distant-investor linkage maps.
   ========================================================================== */

(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  function trunc(text, max = 26) {
    const s = String(text || "");
    return s.length > max ? `${s.slice(0, max - 1)}…` : s;
  }

  function svgEl(tag, attrs = {}, textContent = null) {
    const el = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, String(v)));
    if (textContent !== null) el.textContent = String(textContent);
    return el;
  }

  /* ------------------------------------------------------------------------
     Declarative Executive Briefing Product Template Registry
     ------------------------------------------------------------------------ */
  const TEMPLATE_REGISTRY = {
    EXECUTION_IMPACT: {
      id: "EXECUTION_IMPACT",
      label: "Active Execution, Impact & Players",
      badge: "ACTIVE EXECUTION",
      accent: "#06b6d4",
      subtitle: "What we are actively executing, strategic Interest impact, and invested players",
      effortSections: ["players", "interests", "distant", "risks"],
      orgSections: ["efforts", "interests", "indirect", "risks_pools"],
    },
    INVESTMENT_OPPORTUNITY: {
      id: "INVESTMENT_OPPORTUNITY",
      label: "Resourcing Proposal (\"If You Resource This\")",
      badge: "RESOURCING PROPOSAL",
      accent: "#f59e0b",
      subtitle: "What this capability unlocks if resourced, unmet requirements, and downstream beneficiaries",
      effortSections: ["gaps", "distant", "interests", "players"],
      orgSections: ["risks_pools", "indirect", "efforts", "interests"],
    },
    RISK_MITIGATION_ASK: {
      id: "RISK_MITIGATION_ASK",
      label: "Risk & Mitigation Resourcing Ask",
      badge: "RISK & MITIGATION ASK",
      accent: "#ef4444",
      subtitle: "Active delivery risks, downstream blast radius, and unresourced mitigators",
      effortSections: ["risks", "distant", "gaps", "players"],
      orgSections: ["risks_pools", "efforts", "indirect", "interests"],
    },
    DEPENDENCY_ECOSYSTEM: {
      id: "DEPENDENCY_ECOSYSTEM",
      label: "Value-Chain & Distant Players",
      badge: "VALUE-CHAIN LINKAGES",
      accent: "#818cf8",
      subtitle: "Multi-hop Effort-to-Effort dependency chain, Interest alignment, and distant-end investors",
      effortSections: ["distant", "interests", "players", "risks"],
      orgSections: ["indirect", "efforts", "interests", "risks_pools"],
    },
    PARTNERSHIP_ALIGNMENT: {
      id: "PARTNERSHIP_ALIGNMENT",
      label: "Cross-Org Co-Investment & Partnerships",
      badge: "PARTNERSHIP ALIGNMENT",
      accent: "#a855f7",
      subtitle: "Co-investing organizations, indirect shared-interest beneficiaries, and joint leverage",
      effortSections: ["players", "distant", "interests", "gaps"],
      orgSections: ["indirect", "interests", "efforts", "risks_pools"],
    },
  };

  function registerTemplate(id, definition) {
    if (!id || !definition) return;
    TEMPLATE_REGISTRY[id] = { ...definition, id };
  }

  function resolveAutoOrgTemplate(b) {
    if ((b.active_risks || []).length > 0) return "RISK_MITIGATION_ASK";
    if ((b.directly_resourced_efforts || []).length === 0) return "INVESTMENT_OPPORTUNITY";
    if ((b.partnership_opportunities || []).length >= 2) return "PARTNERSHIP_ALIGNMENT";
    return "EXECUTION_IMPACT";
  }

  /* ------------------------------------------------------------------------
     SVG Linkage Visualizer: Effort -> Interest & Effort -> Effort -> Distant Orgs
     ------------------------------------------------------------------------ */
  function buildEffortLinkageSvg(b) {
    const svg = svgEl("svg", {
      class: "briefing-linkage-svg",
      viewBox: "0 0 980 265",
      preserveAspectRatio: "xMidYMid meet",
      role: "img",
      "aria-label": "Effort relationship and distant investor linkage diagram",
    });

    const defs = svgEl("defs");
    defs.appendChild(
      svgEl("marker", { id: "br-arrow-solid", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" })
    ).appendChild(svgEl("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#38bdf8" }));
    defs.appendChild(
      svgEl("marker", { id: "br-arrow-dash", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" })
    ).appendChild(svgEl("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#94a3b8" }));
    defs.appendChild(
      svgEl("marker", { id: "br-arrow-intr", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" })
    ).appendChild(svgEl("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#10b981" }));
    svg.appendChild(defs);

    const orgNameById = {};
    (b.organizations || []).forEach((o) => {
      orgNameById[o.id] = o.name;
    });

    function drawBox(x, y, w, h, title, sub, stroke, fill = "#161e2c", titleColor = "#e2e8f0") {
      const g = svgEl("g", { class: "br-svg-node" });
      g.appendChild(svgEl("rect", { x, y, width: w, height: h, rx: 6, fill, stroke, "stroke-width": 1.6 }));
      g.appendChild(
        svgEl("text", { x: x + 8, y: y + 16, fill: titleColor, "font-size": 11, "font-weight": 700 }, trunc(title, Math.floor((w - 14) / 6.3)))
      );
      if (sub) {
        g.appendChild(
          svgEl("text", { x: x + 8, y: y + 30, fill: "#94a3b8", "font-size": 9.5 }, trunc(sub, Math.floor((w - 14) / 5.4)))
        );
      }
      svg.appendChild(g);
    }

    function drawCurve(x1, y1, x2, y2, stroke, dashed = false, marker = "url(#br-arrow-solid)") {
      const mx = (x1 + x2) / 2;
      const attrs = {
        d: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
        fill: "none",
        stroke,
        "stroke-width": dashed ? 1.4 : 1.9,
        "marker-end": marker,
      };
      if (dashed) attrs["stroke-dasharray"] = "5 4";
      svg.appendChild(svgEl("path", attrs));
    }

    // Column headers
    svg.appendChild(svgEl("text", { x: 16, y: 15, fill: "#94a3b8", "font-size": 10, "font-weight": 700 }, "DIRECT PLAYERS (ORGS)"));
    svg.appendChild(svgEl("text", { x: 255, y: 15, fill: "#38bdf8", "font-size": 10, "font-weight": 700 }, "FOCAL EFFORT & INTEREST IMPACT"));
    svg.appendChild(svgEl("text", { x: 545, y: 15, fill: "#c084fc", "font-size": 10, "font-weight": 700 }, "EFFORT -> EFFORT CHAIN & DISTANT INVESTORS"));

    // 1. Direct Resourcing Orgs (Left column, max 4)
    const directEdges = b.direct_resourcing_edges || [];
    const orgAgg = {};
    directEdges.forEach((oe) => {
      if (!orgAgg[oe.org_id]) orgAgg[oe.org_id] = { usd: 0, types: new Set() };
      orgAgg[oe.org_id].types.add(oe.resourcing_type);
      if (oe.resourcing_type === "MONEY" || (oe.allocation_unit || "").toUpperCase() === "USD") {
        orgAgg[oe.org_id].usd += Number(oe.allocation_amount || 0);
      }
    });
    const directOrgList = Object.entries(orgAgg).slice(0, 4);

    // Focal box coordinates
    const fx = 255;
    const fy = 42;
    const fw = 225;
    const fh = 64;

    if (directOrgList.length === 0) {
      drawBox(16, 52, 185, 42, "No Direct Resourcing", "Candidate for Investment", "#f59e0b", "#1b2434", "#fbbf24");
      drawCurve(201, 73, fx, fy + fh / 2, "#f59e0b", true, "url(#br-arrow-dash)");
    } else {
      directOrgList.forEach(([oid, info], idx) => {
        const oy = 32 + idx * 54;
        const sub = info.usd > 0 ? `$${Math.round(info.usd).toLocaleString()} · ${[...info.types].join("/")}` : [...info.types].join(", ");
        drawBox(16, oy, 185, 42, orgNameById[oid] || oid, sub, "#38bdf8");
        drawCurve(201, oy + 21, fx, fy + fh / 2, "#38bdf8", false, "url(#br-arrow-solid)");
      });
    }

    // 2. Focal Effort box (Center)
    const eff = b.forecast.effort;
    const stateColor = eff.state === "COMPLETED" ? "#10b981" : eff.state === "IN_WORK" ? "#06b6d4" : "#f59e0b";
    const riskNote = (b.active_risks || []).length ? ` · ${b.active_risks.length} Risk(s)` : "";
    drawBox(fx, fy, fw, fh, eff.name, `${eff.state} · ${Math.round((b.forecast.resourcing_coverage_ratio || 0) * 100)}% funded${riskNote}`, stateColor, "#1b2434");

    // 3. Aligned Interests below Focal Effort (Effort -> Interest)
    const interests = (b.aligned_interests || []).slice(0, 3);
    if (interests.length === 0) {
      drawBox(fx, 152, fw, 38, "No Direct Interests", "Link an Interest to anchor value", "#64748b");
      drawCurve(fx + fw / 2, fy + fh, fx + fw / 2, 152, "#64748b", true, "url(#br-arrow-dash)");
    } else {
      interests.forEach((intr, idx) => {
        const iy = 132 + idx * 44;
        const rel = (b.effort_interest_edges || []).find((e) => e.interest_id === intr.id)?.relation_type || "ALIGNS";
        drawBox(fx, iy, fw, 38, intr.name, `${intr.kind} · ${rel}`, "#10b981");
        drawCurve(fx + 28, fy + fh, fx + 12, iy + 19, "#10b981", false, "url(#br-arrow-intr)");
      });
    }

    // 4. Multi-hop Downstream Efforts + Distant End Investors (Right)
    const distant = (b.distant_effort_investors || []).slice(0, 5);
    if (distant.length === 0) {
      drawBox(550, 52, 230, 46, "Terminal / End Effort", "No further downstream efforts", "#818cf8");
      drawCurve(fx + fw, fy + fh / 2, 550, 75, "#94a3b8", true, "url(#br-arrow-dash)");
    } else {
      distant.forEach((d, idx) => {
        const hopColX = d.hop_distance === 1 ? 545 : 755;
        const rowY = 30 + idx * 46;
        const w = 210;
        const investors = [...(d.investing_org_names || []), ...(d.stakeholder_org_names || [])];
        const uniqueInv = [...new Set(investors)];
        const invLabel = uniqueInv.length
          ? `Orgs: ${uniqueInv.slice(0, 2).join(", ")}${uniqueInv.length > 2 ? ` +${uniqueInv.length - 2}` : ""}`
          : "No downstream org links";
        const border = d.is_terminal_end ? "#c084fc" : "#818cf8";
        drawBox(hopColX, rowY, w, 38, `${d.is_terminal_end ? "★ " : ""}${d.effort_name}`, `Hop ${d.hop_distance} (${d.effort_state}) · ${invLabel}`, border);

        const isBlocking = (d.path_relation_types || []).includes("BLOCKING");
        if (d.hop_distance === 1) {
          drawCurve(fx + fw, fy + fh / 2, hopColX, rowY + 19, isBlocking ? "#38bdf8" : "#94a3b8", !isBlocking, isBlocking ? "url(#br-arrow-solid)" : "url(#br-arrow-dash)");
        } else {
          const parentId = d.path_effort_ids?.[d.path_effort_ids.length - 2];
          const pIdx = distant.findIndex((x) => x.effort_id === parentId);
          const startX = pIdx >= 0 && distant[pIdx].hop_distance === 1 ? 545 + 210 : fx + fw;
          const startY = pIdx >= 0 && distant[pIdx].hop_distance === 1 ? 30 + pIdx * 46 + 19 : fy + fh / 2;
          drawCurve(startX, startY, hopColX, rowY + 19, isBlocking ? "#c084fc" : "#94a3b8", !isBlocking, isBlocking ? "url(#br-arrow-solid)" : "url(#br-arrow-dash)");
        }
      });
    }

    return svg.outerHTML;
  }

  /* ------------------------------------------------------------------------
     SVG Linkage Visualizer: Org Portfolio -> Efforts -> Interests & Partners
     ------------------------------------------------------------------------ */
  function buildOrgLinkageSvg(b, orgNameMap) {
    const svg = svgEl("svg", {
      class: "briefing-linkage-svg",
      viewBox: "0 0 980 230",
      preserveAspectRatio: "xMidYMid meet",
      role: "img",
      "aria-label": "Organization portfolio linkage diagram",
    });

    const defs = svgEl("defs");
    defs.appendChild(
      svgEl("marker", { id: "br-org-arr", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" })
    ).appendChild(svgEl("path", { d: "M 0 1 L 9 5 L 0 9 z", fill: "#38bdf8" }));
    svg.appendChild(defs);

    function drawBox(x, y, w, h, title, sub, stroke) {
      const g = svgEl("g");
      g.appendChild(svgEl("rect", { x, y, width: w, height: h, rx: 6, fill: "#161e2c", stroke, "stroke-width": 1.6 }));
      g.appendChild(svgEl("text", { x: x + 8, y: y + 16, fill: "#e2e8f0", "font-size": 11, "font-weight": 700 }, trunc(title, Math.floor((w - 14) / 6.3))));
      if (sub) g.appendChild(svgEl("text", { x: x + 8, y: y + 30, fill: "#94a3b8", "font-size": 9.5 }, trunc(sub, Math.floor((w - 14) / 5.4))));
      svg.appendChild(g);
    }

    function drawCurve(x1, y1, x2, y2, stroke, dashed = false) {
      const mx = (x1 + x2) / 2;
      const attrs = { d: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`, fill: "none", stroke, "stroke-width": 1.6, "marker-end": "url(#br-org-arr)" };
      if (dashed) attrs["stroke-dasharray"] = "5 4";
      svg.appendChild(svgEl("path", attrs));
    }

    svg.appendChild(svgEl("text", { x: 16, y: 15, fill: "#94a3b8", "font-size": 10, "font-weight": 700 }, "SUBJECT ORG & POOLS"));
    svg.appendChild(svgEl("text", { x: 325, y: 15, fill: "#38bdf8", "font-size": 10, "font-weight": 700 }, "RESOURCED & INDIRECT EFFORTS"));
    svg.appendChild(svgEl("text", { x: 675, y: 15, fill: "#10b981", "font-size": 10, "font-weight": 700 }, "INTERESTS & PARTNERS"));

    const orgLabel = orgNameMap[b.subject_org_id] || b.subject_org_id;
    drawBox(16, 42, 220, 56, orgLabel, `${(b.pool_balances || []).length} pool(s) · $${Math.round(b.total_allocated_usd || 0).toLocaleString()}`, "#38bdf8");

    const efforts = (b.directly_resourced_efforts || []).slice(0, 4);
    efforts.forEach((n, idx) => {
      const y = 32 + idx * 46;
      drawBox(325, y, 250, 38, n.effort.name, `${n.effort.state} · ${Math.round((n.resourcing_coverage_ratio || 0) * 100)}% funded`, n.effort.state === "COMPLETED" ? "#10b981" : "#06b6d4");
      drawCurve(236, 70, 325, y + 19, "#38bdf8", false);
    });

    const interests = (b.priority_interests || []).slice(0, 3);
    interests.forEach((pi, idx) => {
      const y = 32 + idx * 46;
      drawBox(675, y, 280, 38, pi.interest_id, `Priority ${Math.round(Number(pi.effective_priority) * 100)}%`, "#10b981");
      if (efforts.length) drawCurve(575, 51, 675, y + 19, "#10b981", true);
    });

    const partners = (b.partnership_opportunities || []).slice(0, 1);
    partners.forEach((p) => {
      const other = p.org_a_id === b.subject_org_id ? p.org_b_id : p.org_a_id;
      drawBox(675, 174, 280, 38, `Partner: ${orgNameMap[other] || other}`, `Shared: ${p.shared_interest_ids.slice(0, 2).join(", ")}`, "#a855f7");
      drawCurve(236, 80, 675, 193, "#a855f7", true);
    });

    return svg.outerHTML;
  }

  /* ------------------------------------------------------------------------
     BriefingController
     ------------------------------------------------------------------------ */
  class BriefingController {
    constructor(opts) {
      this.notify = opts.notify;
      this.scopeSelect = document.getElementById("briefing-scope-select");
      this.orgGroup = document.getElementById("briefing-org-group");
      this.effortGroup = document.getElementById("briefing-effort-group");
      this.orgSelect = document.getElementById("briefing-org-select");
      this.effortSelect = document.getElementById("briefing-effort-select");
      this.templateSelect = document.getElementById("briefing-template-select");
      this.slideEl = document.getElementById("briefing-slide-content");
      this.orgNameMap = {};
      this.lastQueryParams = {};

      document.getElementById("btn-print-briefing")?.addEventListener("click", () => window.print());
      this.scopeSelect?.addEventListener("change", () => {
        this._syncScopeVisibility();
        this.refresh(this.lastQueryParams);
      });
      this.orgSelect?.addEventListener("change", () => this.refresh(this.lastQueryParams));
      this.effortSelect?.addEventListener("change", () => this.refresh(this.lastQueryParams));
      this.templateSelect?.addEventListener("change", () => this.refresh(this.lastQueryParams));
    }

    _syncScopeVisibility() {
      const scope = this.scopeSelect?.value || "org";
      this.orgGroup?.classList.toggle("hidden", scope !== "org");
      this.effortGroup?.classList.toggle("hidden", scope !== "effort");
    }

    setOrganizations(orgs) {
      this.setCatalog(orgs, null);
    }

    setCatalog(orgs, efforts) {
      const { escapeHtml } = global.BijouApi;
      if (orgs) {
        this.orgNameMap = {};
        orgs.forEach((o) => {
          this.orgNameMap[o.id] = o.name;
        });
        if (this.orgSelect) {
          const prev = this.orgSelect.value;
          this.orgSelect.innerHTML = orgs
            .map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)} ${o.is_managed ? "(Managed)" : ""}</option>`)
            .join("");
          if (prev && orgs.some((o) => o.id === prev)) this.orgSelect.value = prev;
        }
      }
      if (efforts && this.effortSelect) {
        const prevEff = this.effortSelect.value;
        this.effortSelect.innerHTML = efforts
          .map((e) => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)} (${escapeHtml(e.state)})</option>`)
          .join("");
        if (prevEff && efforts.some((e) => e.id === prevEff)) this.effortSelect.value = prevEff;
      }
      this._syncScopeVisibility();
    }

    selectTarget(scope, targetId, templateId) {
      if (this.scopeSelect && (scope === "org" || scope === "effort")) {
        this.scopeSelect.value = scope;
        this._syncScopeVisibility();
      }
      if (scope === "effort" && this.effortSelect && targetId) {
        this.effortSelect.value = targetId;
      } else if (scope === "org" && this.orgSelect && targetId) {
        this.orgSelect.value = targetId;
      }
      if (templateId && this.templateSelect && TEMPLATE_REGISTRY[templateId]) {
        this.templateSelect.value = templateId;
      }
    }

    async refresh(queryParams = {}) {
      this.lastQueryParams = queryParams || {};
      const scope = this.scopeSelect?.value || "org";
      const chosenTemplate = this.templateSelect?.value || "AUTO";

      if (scope === "effort") {
        await this._refreshEffort(queryParams, chosenTemplate);
      } else {
        await this._refreshOrg(queryParams, chosenTemplate);
      }
    }

    async _refreshEffort(queryParams, chosenTemplate) {
      const effortId = this.effortSelect?.value;
      if (!effortId) {
        this.slideEl.innerHTML = '<div class="empty-state">Select an Effort to render Effort-Level Executive Briefing.</div>';
        return;
      }
      const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
      try {
        const b = await global.BijouApi.getEffortBriefing({
          effort_id: effortId,
          include_hierarchy_inheritance: queryParams.include_hierarchy_priorities ?? true,
          as_of_date: queryParams.as_of_date || undefined,
        });

        const resolvedId = chosenTemplate === "AUTO" ? (b.recommended_template || "EXECUTION_IMPACT") : chosenTemplate;
        const tpl = TEMPLATE_REGISTRY[resolvedId] || TEMPLATE_REGISTRY.EXECUTION_IMPACT;
        const eff = b.forecast.effort;

        const orgNames = {};
        (b.organizations || []).forEach((o) => {
          orgNames[o.id] = o.name;
        });

        const totalShortfallUsd = (b.resource_gaps || [])
          .filter((g) => g.category === "MONEY" || (g.unit || "").toUpperCase() === "USD")
          .reduce((acc, g) => acc + Number(g.shortfall_amount || 0), 0);

        const sectionsMap = {
          players: `
            <div class="quadrant-box">
              <h3>Direct Players &amp; Resourcing (${(b.direct_resourcing_edges || []).length})</h3>
              ${(b.direct_resourcing_edges || []).map((oe) => `
                <div class="staged-item mt-2">
                  <span><strong>${escapeHtml(orgNames[oe.org_id] || oe.org_id)}</strong> (${escapeHtml(oe.resourcing_type)})</span>
                  <span class="mono-text">${oe.allocation_amount} ${escapeHtml(oe.allocation_unit)} · ${escapeHtml(oe.confidence)}</span>
                </div>
              `).join("") || '<div class="mono-text">No direct organization resourcing assigned yet.</div>'}
              ${(b.indirect_beneficiaries || []).length ? `<div class="mono-text mt-2">Indirect Shared-Interest Beneficiaries: ${b.indirect_beneficiaries.map((ib) => escapeHtml(orgNames[ib.beneficiary_org_id] || ib.beneficiary_org_id)).join(", ")}</div>` : ""}
            </div>
          `,
          interests: `
            <div class="quadrant-box">
              <h3>Strategic Impact: Effort → Interests (${(b.aligned_interests || []).length})</h3>
              <div class="chip-row mt-2">
                ${(b.aligned_interests || []).map((i) => `<span class="mini-chip">${escapeHtml(i.name)} (${escapeHtml(i.kind)})</span>`).join("") || '<span class="mono-text">No direct aligned interests.</span>'}
              </div>
              ${(b.ancestor_interest_categories || []).length ? `<div class="chip-row mt-2">${b.ancestor_interest_categories.map((a) => `<span class="mini-chip indirect">Parent Goal: ${escapeHtml(a.name)}</span>`).join("")}</div>` : ""}
            </div>
          `,
          distant: `
            <div class="quadrant-box">
              <h3>Downstream Chain &amp; Distant-End Investors (${(b.distant_effort_investors || []).length})</h3>
              ${(b.distant_effort_investors || []).map((d) => {
                const players = [...new Set([...(d.investing_org_names || []), ...(d.stakeholder_org_names || [])])];
                return `
                  <div class="staged-item mt-2">
                    <span>${d.is_terminal_end ? "★ " : ""}<strong>${escapeHtml(d.effort_name)}</strong> <em class="mono-text">(Hop ${d.hop_distance} · ${escapeHtml(d.effort_state)})</em></span>
                    <span class="mono-text">${players.length ? escapeHtml(players.join(", ")) : "No org stake"}</span>
                  </div>
                `;
              }).join("") || '<div class="mono-text">Terminal capability — no downstream effort dependencies.</div>'}
            </div>
          `,
          gaps: `
            <div class="quadrant-box">
              <h3>Unmet Requirements &amp; Resourcing Ask (${(b.resource_gaps || []).length})</h3>
              ${(b.resource_gaps || []).map((g) => `
                <div class="staged-item mt-2">
                  <span><strong>${escapeHtml(g.category)}</strong>${g.required_skill ? ` (${escapeHtml(g.required_skill)})` : ""}</span>
                  <span class="mono-text">${g.shortfall_amount > 0 ? `<strong style="color:#fbbf24">Need +${g.shortfall_amount} ${escapeHtml(g.unit)}</strong>` : `Covered (${g.allocated_amount}/${g.required_amount} ${escapeHtml(g.unit)})`}</span>
                </div>
              `).join("") || '<div class="mono-text">No formal resource requirements registered.</div>'}
            </div>
          `,
          risks: `
            <div class="quadrant-box">
              <h3>Active Risks (${(b.active_risks || []).length}) &amp; Unresourced Mitigators (${(b.unexercised_mitigators || []).length})</h3>
              ${(b.active_risks || []).map((r) => `
                <div class="mono-text mt-2" style="color:#fca5a5">• [${escapeHtml(r.severity)}] <strong>${escapeHtml(r.title)}</strong> (+${r.potential_slip_days}d exposure)</div>
              `).join("") || '<div class="mono-text">No active delivery risks.</div>'}
              ${(b.unexercised_mitigators || []).map((m) => {
                const mCost = (m.additional_requirements || []).reduce((acc, r) => acc + Number(r.estimated_cost_usd ?? (r.category === "MONEY" || (r.unit || "").toUpperCase() === "USD" ? r.quantity : 0) ?? 0), 0);
                return `
                  <div class="staged-item mt-2">
                    <span>Mitigator: <strong>${escapeHtml(m.name)}</strong> (-${m.slip_reduction_days}d)</span>
                    <span class="mono-text" style="color:#fbbf24">Ask: ${mCost > 0 ? fmtUsd(mCost) : "Resource Needed"}</span>
                  </div>
                `;
              }).join("")}
            </div>
          `,
        };

        this.slideEl.innerHTML = `
          <div class="briefing-slide-header">
            <div>
              <span class="briefing-template-badge" style="border-color:${tpl.accent};color:${tpl.accent}">${escapeHtml(tpl.badge)}${chosenTemplate === "AUTO" ? " · AUTO" : ""}</span>
              <h2>${escapeHtml(eff.name)}</h2>
              <div class="mono-text">Effort Scope · State: ${escapeHtml(eff.state)} · ${escapeHtml(fmtForecast(b.forecast))} · As-Of ${escapeHtml(b.as_of_date)}</div>
            </div>
            <div class="briefing-kpi-row">
              <div class="briefing-kpi">
                <div class="briefing-kpi-val">${fmtUsd(b.total_direct_allocated_usd)}</div>
                <div class="mono-text">Direct Funded</div>
              </div>
              <div class="briefing-kpi">
                <div class="briefing-kpi-val" style="color:${totalShortfallUsd > 0 ? "#fbbf24" : "#10b981"}">${fmtUsd(totalShortfallUsd)}</div>
                <div class="mono-text">Resource Gap</div>
              </div>
              <div class="briefing-kpi">
                <div class="briefing-kpi-val" style="color:${b.total_mitigation_ask_usd > 0 ? "#f87171" : "#94a3b8"}">${fmtUsd(b.total_mitigation_ask_usd)}</div>
                <div class="mono-text">Mitigation Ask</div>
              </div>
            </div>
          </div>

          <div class="puck-card">
            <h4>${escapeHtml(tpl.label)} — ${escapeHtml(tpl.subtitle)}</h4>
            <p>${escapeHtml(b.executive_summary_narrative || "")}</p>
            ${(b.key_decision_asks || []).length ? `<ul class="briefing-ask-list mt-2">${b.key_decision_asks.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>` : ""}
          </div>

          <div class="briefing-svg-panel">
            ${buildEffortLinkageSvg(b)}
          </div>

          <div class="briefing-quadrants">
            ${tpl.effortSections.map((key) => sectionsMap[key] || "").join("")}
          </div>
        `;
      } catch (err) {
        this.slideEl.innerHTML = `<div class="hint-banner warn">${escapeHtml(err.message)}</div>`;
      }
    }

    async _refreshOrg(queryParams, chosenTemplate) {
      const orgId = this.orgSelect?.value;
      if (!orgId) {
        this.slideEl.innerHTML = '<div class="empty-state">Select an Organization to render Briefing.</div>';
        return;
      }
      const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;

      try {
        const b = await global.BijouApi.getBriefing({
          subject_org_id: orgId,
          include_hierarchy_inheritance: queryParams.include_hierarchy_priorities ?? true,
          as_of_date: queryParams.as_of_date || undefined,
        });

        const resolvedId = chosenTemplate === "AUTO" ? resolveAutoOrgTemplate(b) : chosenTemplate;
        const tpl = TEMPLATE_REGISTRY[resolvedId] || TEMPLATE_REGISTRY.EXECUTION_IMPACT;
        const orgLabel = this.orgNameMap[b.subject_org_id] || b.subject_org_id;

        const sectionsMap = {
          efforts: `
            <div class="quadrant-box">
              <h3>Directly Resourced Efforts (${(b.directly_resourced_efforts || []).length})</h3>
              ${(b.directly_resourced_efforts || []).map((n) => `
                <div class="staged-item mt-2">
                  <span><strong>${escapeHtml(n.effort.name)}</strong> (${escapeHtml(n.effort.state)})</span>
                  <span class="mono-text">${escapeHtml(fmtForecast(n))}</span>
                </div>
              `).join("") || '<div class="mono-text">No direct resourcing links.</div>'}
            </div>
          `,
          indirect: `
            <div class="quadrant-box">
              <h3>Indirect Benefits &amp; Partnerships (${(b.indirect_benefits || []).length})</h3>
              ${(b.indirect_benefits || []).map((ib) => `
                <div class="mono-text mt-2">• Effort <strong>${escapeHtml(ib.effort_id)}</strong> supports shared Interest <strong>${escapeHtml(ib.via_interest_id)}</strong> (${escapeHtml(ib.confidence)})</div>
              `).join("") || '<div class="mono-text">No indirect benefit paths detected.</div>'}
              ${(b.partnership_opportunities || []).slice(0, 3).map((p) => `
                <div class="mono-text mt-2" style="color:#d8b4fe">• Partner Opportunity: ${escapeHtml(p.org_a_id)} ↔ ${escapeHtml(p.org_b_id)} (${escapeHtml(p.shared_interest_ids.join(", "))})</div>
              `).join("")}
            </div>
          `,
          interests: `
            <div class="quadrant-box">
              <h3>Priority Interests (${(b.priority_interests || []).length})</h3>
              ${(b.priority_interests || []).map((pi) => `
                <div class="staged-item mt-2">
                  <span>${escapeHtml(pi.interest_id)}${pi.inherited_from_org_id ? ` <em class="mono-text">(inherited from ${escapeHtml(pi.inherited_from_org_id)})</em>` : ""}</span>
                  <span class="mono-text">Priority ${(Number(pi.effective_priority) * 100).toFixed(0)}%</span>
                </div>
              `).join("") || '<div class="mono-text">No prioritized interests.</div>'}
            </div>
          `,
          risks_pools: `
            <div class="quadrant-box">
              <h3>Pools (${(b.pool_balances || []).length}) &amp; Active Risks (${(b.active_risks || []).length})</h3>
              ${(b.pool_balances || []).map((pb) => `
                <div class="mono-text mt-2">• Pool <strong>${escapeHtml(pb.pool.name)}</strong>: ${pb.remaining_amount} / ${pb.pool.capacity} ${escapeHtml(pb.pool.unit)} remaining</div>
              `).join("")}
              ${(b.active_risks || []).slice(0, 4).map((r) => `
                <div class="mono-text mt-2" style="color:#fca5a5">• [${escapeHtml(r.severity)}] ${escapeHtml(r.title)} (+${r.potential_slip_days}d)</div>
              `).join("")}
            </div>
          `,
        };

        this.slideEl.innerHTML = `
          <div class="briefing-slide-header">
            <div>
              <span class="briefing-template-badge" style="border-color:${tpl.accent};color:${tpl.accent}">${escapeHtml(tpl.badge)}${chosenTemplate === "AUTO" ? " · AUTO" : ""}</span>
              <h2>Executive Portfolio Briefing: ${escapeHtml(orgLabel)}</h2>
              <div class="mono-text">Perspective: ${escapeHtml(b.active_access_mode)} · As-Of ${escapeHtml(b.as_of_date)} · Hierarchy Rollup: ${b.include_hierarchy_inheritance ? "ON" : "OFF"}</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:1.25rem;font-weight:800;color:var(--accent-cyan)">${fmtUsd(b.total_allocated_usd)}</div>
              <div class="mono-text">Direct Portfolio Allocation</div>
            </div>
          </div>

          <div class="puck-card">
            <h4>${escapeHtml(tpl.label)} — ${escapeHtml(tpl.subtitle)}</h4>
            <p>${escapeHtml(b.executive_summary_narrative || "Deterministic portfolio synthesis active.")}</p>
            ${(b.strategic_gaps || []).length ? `<div class="chip-row mt-2">${b.strategic_gaps.map((g) => `<span class="mini-chip risk">${escapeHtml(g)}</span>`).join("")}</div>` : ""}
          </div>

          <div class="briefing-svg-panel">
            ${buildOrgLinkageSvg(b, this.orgNameMap)}
          </div>

          <div class="briefing-quadrants">
            ${tpl.orgSections.map((key) => sectionsMap[key] || "").join("")}
          </div>
        `;
      } catch (err) {
        this.slideEl.innerHTML = `<div class="hint-banner warn">${escapeHtml(err.message)}</div>`;
      }
    }
  }

  global.BijouBriefingTemplates = {
    registry: TEMPLATE_REGISTRY,
    registerTemplate,
  };
  global.BriefingController = BriefingController;
})(window);
