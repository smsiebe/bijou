/* ==========================================================================
   Bijou v2 Lens 2: 1-Slide Executive Organization Briefing
   ========================================================================== */

(function (global) {
  "use strict";

  class BriefingController {
    constructor(opts) {
      this.notify = opts.notify;
      this.orgSelect = document.getElementById("briefing-org-select");
      this.slideEl = document.getElementById("briefing-slide-content");
      document.getElementById("btn-print-briefing")?.addEventListener("click", () => window.print());
      this.orgSelect?.addEventListener("change", () => this.refresh());
    }

    setOrganizations(orgs) {
      if (!this.orgSelect) return;
      const { escapeHtml } = global.BijouApi;
      const prev = this.orgSelect.value;
      this.orgSelect.innerHTML = (orgs || [])
        .map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)} ${o.is_managed ? "(Managed)" : ""}</option>`)
        .join("");
      if (prev && orgs.some((o) => o.id === prev)) this.orgSelect.value = prev;
    }

    async refresh(queryParams = {}) {
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

        this.slideEl.innerHTML = `
          <div class="briefing-slide-header">
            <div>
              <h2>Executive Portfolio Briefing: ${escapeHtml(b.subject_org_id)}</h2>
              <div class="mono-text">Perspective: ${escapeHtml(b.active_access_mode)} · As-Of ${escapeHtml(b.as_of_date)} · Hierarchy Rollup: ${b.include_hierarchy_inheritance ? "ON" : "OFF"}</div>
            </div>
            <div style="text-align:right">
              <div style="font-size:1.25rem;font-weight:800;color:var(--accent-cyan)">${fmtUsd(b.total_allocated_usd)}</div>
              <div class="mono-text">Direct Portfolio Allocation</div>
            </div>
          </div>

          <div class="puck-card">
            <h4>Executive Narrative &amp; Strategic Gaps</h4>
            <p>${escapeHtml(b.executive_summary_narrative || "Deterministic portfolio synthesis active.")}</p>
            ${(b.strategic_gaps || []).length ? `<div class="chip-row mt-2">${b.strategic_gaps.map((g) => `<span class="mini-chip risk">${escapeHtml(g)}</span>`).join("")}</div>` : ""}
          </div>

          <div class="briefing-quadrants">
            <div class="quadrant-box">
              <h3>1. Directly Resourced Efforts (${(b.directly_resourced_efforts || []).length})</h3>
              ${(b.directly_resourced_efforts || []).map((n) => `
                <div class="staged-item mt-2">
                  <span><strong>${escapeHtml(n.effort.name)}</strong> (${escapeHtml(n.effort.state)})</span>
                  <span class="mono-text">${escapeHtml(fmtForecast(n))}</span>
                </div>
              `).join("") || '<div class="mono-text">No direct resourcing links.</div>'}
            </div>

            <div class="quadrant-box">
              <h3>2. Indirect Benefits via Shared Interests (${(b.indirect_benefits || []).length})</h3>
              ${(b.indirect_benefits || []).map((ib) => `
                <div class="mono-text mt-2">• Effort <strong>${escapeHtml(ib.effort_id)}</strong> supports shared Interest <strong>${escapeHtml(ib.via_interest_id)}</strong> (${escapeHtml(ib.confidence)})</div>
              `).join("") || '<div class="mono-text">No indirect benefit paths detected.</div>'}
            </div>

            <div class="quadrant-box">
              <h3>3. Priority Interests (${(b.priority_interests || []).length})</h3>
              ${(b.priority_interests || []).map((pi) => `
                <div class="staged-item mt-2">
                  <span>${escapeHtml(pi.interest_id)}${pi.inherited_from_org_id ? ` <em class="mono-text">(inherited from ${escapeHtml(pi.inherited_from_org_id)})</em>` : ""}</span>
                  <span class="mono-text">Priority ${(Number(pi.effective_priority) * 100).toFixed(0)}%</span>
                </div>
              `).join("") || '<div class="mono-text">No prioritized interests.</div>'}
            </div>

            <div class="quadrant-box">
              <h3>4. Pools, Active Risks (${(b.active_risks || []).length}) &amp; Partnerships</h3>
              ${(b.pool_balances || []).map((pb) => `
                <div class="mono-text mt-2">• Pool <strong>${escapeHtml(pb.pool.name)}</strong>: ${pb.remaining_amount} / ${pb.pool.capacity} ${escapeHtml(pb.pool.unit)} remaining</div>
              `).join("")}
              ${(b.active_risks || []).slice(0, 4).map((r) => `
                <div class="mono-text mt-2" style="color:#fca5a5">• [${escapeHtml(r.severity)}] ${escapeHtml(r.title)} (+${r.potential_slip_days}d)</div>
              `).join("")}
              ${(b.partnership_opportunities || []).slice(0, 3).map((p) => `
                <div class="mono-text mt-2" style="color:#d8b4fe">• Partner Opportunity: ${escapeHtml(p.org_a_id)} ↔ ${escapeHtml(p.org_b_id)} (${escapeHtml(p.shared_interest_ids.join(", "))})</div>
              `).join("")}
            </div>
          </div>
        `;
      } catch (err) {
        this.slideEl.innerHTML = `<div class="hint-banner warn">${escapeHtml(err.message)}</div>`;
      }
    }
  }

  global.BriefingController = BriefingController;
})(window);
