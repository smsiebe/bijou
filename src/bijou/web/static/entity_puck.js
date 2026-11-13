/* ==========================================================================
   Bijou v2 Contextual Entity Puck Inspector
   Inspects Effort, Organization, or Interest Focal Dashboards
   ========================================================================== */

(function (global) {
  "use strict";

  class EntityPuck {
    constructor(opts) {
      this.onStageMitigator = opts.onStageMitigator;
      this.onEditInStudio = opts.onEditInStudio;
      this.notify = opts.notify;

      this.backdrop = document.getElementById("puck-backdrop");
      this.kindPill = document.getElementById("puck-kind-pill");
      this.titleEl = document.getElementById("puck-title");
      this.idEl = document.getElementById("puck-id");
      this.contentEl = document.getElementById("puck-content");

      document.getElementById("btn-close-puck")?.addEventListener("click", () => this.close());
      this.backdrop?.addEventListener("click", (ev) => {
        if (ev.target === this.backdrop) this.close();
      });
    }

    close() {
      this.backdrop?.classList.add("hidden");
    }

    async open(kind, id, queryParams) {
      const { escapeHtml } = global.BijouApi;
      this.backdrop?.classList.remove("hidden");
      this.kindPill.textContent = kind.toUpperCase();
      this.titleEl.textContent = "Loading...";
      this.idEl.textContent = id;
      this.contentEl.innerHTML = '<div class="empty-state">Loading focal intelligence...</div>';

      try {
        if (kind === "effort") {
          const data = await global.BijouApi.getEffortFocal(id, queryParams);
          this.renderEffort(data);
        } else if (kind === "organization") {
          const data = await global.BijouApi.getOrgFocal(id, queryParams);
          this.renderOrg(data);
        } else if (kind === "interest") {
          const data = await global.BijouApi.getInterestFocal(id, queryParams);
          this.renderInterest(data);
        }
      } catch (err) {
        this.contentEl.innerHTML = `<div class="hint-banner warn">${escapeHtml(err.message)}</div>`;
      }
    }

    renderEffort(data) {
      const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
      const node = data.forecast;
      const eff = node.effort;
      this.titleEl.textContent = eff.name;
      this.idEl.textContent = `${eff.id} · State: ${eff.state} · Timing: ${node.timing_mode}`;

      const reqs = eff.resource_requirements || [];
      const risks = eff.risks || [];
      const mits = eff.mitigators || [];

      this.contentEl.innerHTML = `
        <div class="puck-card">
          <h4>Forecast &amp; Schedule Resolution</h4>
          <div><strong>${escapeHtml(fmtForecast(node))}</strong></div>
          <div class="mono-text mt-2">Horizon Status: ${escapeHtml(node.horizon_status)} · Topological Depth: ${node.topological_depth}${node.slack_days !== null ? ` · Slack: ${node.slack_days}d` : ""}</div>
          ${eff.description ? `<p class="mt-2">${escapeHtml(eff.description)}</p>` : ""}
          <div class="mt-2" style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn btn-secondary btn-xs" id="puck-edit-effort">Edit Effort in Studio</button>
            <button class="btn btn-primary btn-xs" id="puck-open-effort-briefing">1-Page Effort Briefing</button>
          </div>
        </div>

        <div class="puck-card">
          <h4>Resource Requirements (${reqs.length}) &amp; Coverage (${Math.round((node.resourcing_coverage_ratio || 0) * 100)}%)</h4>
          ${reqs.length ? reqs.map((r) => `
            <div class="staged-item mt-2">
              <span>${escapeHtml(r.label)} (${r.quantity} ${escapeHtml(r.unit)} · ${escapeHtml(r.category)})</span>
              <span class="mono-text">${r.required_skill ? escapeHtml(r.required_skill) : (r.is_generic ? "Generic" : "Specific")}</span>
            </div>
          `).join("") : '<div class="mono-text">No explicit requirements registered.</div>'}
          <h4 class="mt-3">Direct Org Resourcing (${(data.resourcing_edges || []).length})</h4>
          ${(data.resourcing_edges || []).map((e) => `
            <div class="mono-text mt-2">• ${escapeHtml(e.org_id)}: ${e.allocation_amount} ${escapeHtml(e.allocation_unit)} (${escapeHtml(e.resourcing_type)} · ${escapeHtml(e.confidence)})</div>
          `).join("") || '<div class="mono-text">None directly assigned.</div>'}
        </div>

        <div class="puck-card">
          <h4>Aligned Interests &amp; Indirect Beneficiaries</h4>
          <div class="chip-row">
            ${(data.aligned_interests || []).map((i) => `<span class="mini-chip">${escapeHtml(i.name)}</span>`).join("")}
            ${(data.ancestor_interest_categories || []).map((i) => `<span class="mini-chip indirect">Parent: ${escapeHtml(i.name)}</span>`).join("")}
          </div>
          <div class="mono-text mt-2">Indirect Beneficiaries (via Shared Interests): ${(data.indirect_beneficiaries || []).map((b) => escapeHtml(b.beneficiary_org_id)).join(", ") || "None"}</div>
        </div>

        <div class="puck-card">
          <h4>Risks (${risks.length}) &amp; Mitigator Options (${mits.length})</h4>
          ${risks.map((r) => `
            <div class="hint-banner warn mt-2">
              <strong>[${escapeHtml(r.severity)}] ${escapeHtml(r.title)}</strong> (${r.potential_slip_days}d slip${r.is_skill_mismatch_risk ? " · SKILL MISMATCH" : ""})
              <div class="mono-text">${escapeHtml(r.description)}</div>
            </div>
          `).join("") || '<div class="mono-text">No active risks logged.</div>'}
          ${mits.map((m) => `
            <div class="mitigator-row mt-2">
              <div>
                <strong>${escapeHtml(m.name)}</strong> (${m.is_exercised ? "Exercised" : "Available"})
                <div class="mono-text">-${m.slip_reduction_days}d slip</div>
              </div>
              <button class="btn btn-accent btn-xs puck-stage-mit" data-mit-id="${escapeHtml(m.id)}" data-next="${m.is_exercised ? "0" : "1"}">
                ${m.is_exercised ? "Stage Un-Exercise" : "Stage in Bill of Efforts"}
              </button>
            </div>
          `).join("")}
        </div>

        <div class="puck-card">
          <h4>Dependencies &amp; Dependents</h4>
          <div class="mono-text">Upstream: ${(data.upstream_dependencies || []).map((u) => escapeHtml(u.name)).join(", ") || "Root Effort"}</div>
          <div class="mono-text mt-2">Downstream: ${(data.downstream_dependents || []).map((d) => escapeHtml(d.name)).join(", ") || "Leaf Capability"}</div>
          <div class="mono-text mt-2">Telemetry Streams: ${(data.telemetry_rollups || []).length}</div>
        </div>
      `;

      document.getElementById("puck-edit-effort")?.addEventListener("click", () => {
        this.close();
        this.onEditInStudio?.("efforts", eff.id);
      });

      document.getElementById("puck-open-effort-briefing")?.addEventListener("click", () => {
        this.close();
        global.openExecutiveBriefing?.("effort", eff.id);
      });

      this.contentEl.querySelectorAll(".puck-stage-mit").forEach((btn) => {
        btn.addEventListener("click", (ev) => {
          const mid = ev.target.dataset.mitId;
          const nextVal = ev.target.dataset.next === "1";
          this.close();
          this.onStageMitigator?.(mid, nextVal);
        });
      });
    }

    renderOrg(data) {
      const { escapeHtml, fmtForecast } = global.BijouApi;
      const org = data.organization;
      this.titleEl.textContent = org.name;
      this.idEl.textContent = `${org.id} · Echelon ${org.echelon_level} · ${org.is_managed ? "Managed Owner" : "Modeled External"}`;

      this.contentEl.innerHTML = `
        <div class="puck-card">
          <h4>Mission Scope</h4>
          <p>${escapeHtml(org.description || "No description provided.")}</p>
        </div>
        <div class="puck-card">
          <h4>Resource Pools (${(data.pool_balances || []).length})</h4>
          ${(data.pool_balances || []).map((pb) => `
            <div class="pool-row mt-2">
              <div class="pool-row-top"><span>${escapeHtml(pb.pool.name)}</span><span>${pb.remaining_amount} / ${pb.pool.capacity} ${escapeHtml(pb.pool.unit)}</span></div>
              <div class="mono-text">Eligible Interests: ${(pb.eligible_interest_ids || []).length || "All Unrestricted"}</div>
            </div>
          `).join("") || '<div class="mono-text">No pools owned by this organization.</div>'}
        </div>
        <div class="puck-card">
          <h4>Directly Funded Efforts (${(data.direct_funded_efforts || []).length})</h4>
          ${(data.direct_funded_efforts || []).map((n) => `
            <div class="staged-item mt-2"><span>${escapeHtml(n.effort.name)}</span><span class="mono-text">${escapeHtml(fmtForecast(n))}</span></div>
          `).join("") || '<div class="mono-text">None</div>'}
        </div>
        <div class="puck-card">
          <h4>Indirect Benefits via Shared Interests (${(data.indirect_benefit_paths || []).length})</h4>
          ${(data.indirect_benefit_paths || []).map((b) => `
            <div class="mono-text mt-2">• Effort ${escapeHtml(b.effort_id)} advances shared interest ${escapeHtml(b.via_interest_id)}</div>
          `).join("") || '<div class="mono-text">None</div>'}
        </div>
        <div class="puck-card">
          <h4>Shared-Interest Partnership Opportunities (${(data.potential_partnerships || []).length})</h4>
          ${(data.potential_partnerships || []).map((p) => `
            <div class="mono-text mt-2">• Partner: ${escapeHtml(p.org_a_id === org.id ? p.org_b_id : p.org_a_id)} · Shared: ${escapeHtml(p.shared_interest_ids.join(", "))} (${p.has_existing_org_link ? "Linked" : "Untapped"})</div>
          `).join("") || '<div class="mono-text">None identified</div>'}
        </div>
      `;
    }

    renderInterest(data) {
      const { escapeHtml, fmtForecast } = global.BijouApi;
      const intr = data.interest;
      this.titleEl.textContent = intr.name;
      this.idEl.textContent = `${intr.id} · Kind: ${intr.interest_kind}`;

      this.contentEl.innerHTML = `
        <div class="puck-card">
          <h4>Taxonomy Lineage</h4>
          <p>${escapeHtml(intr.description || "")}</p>
          <div class="mono-text mt-2">Parent Categories: ${(data.ancestor_interests || []).map((a) => escapeHtml(a.name)).join(", ") || "Root Category"}</div>
          <div class="mono-text mt-2">Sub-Interests: ${(data.descendant_interests || []).map((d) => escapeHtml(d.name)).join(", ") || "Leaf Interest"}</div>
        </div>
        <div class="puck-card">
          <h4>Color-of-Money Eligible Resource Pools (${(data.eligible_resource_pools || []).length})</h4>
          ${(data.eligible_resource_pools || []).map((pb) => `
            <div class="staged-item mt-2"><span>${escapeHtml(pb.pool.name)} (${escapeHtml(pb.pool.org_id)})</span><span class="mono-text">${pb.remaining_amount} ${escapeHtml(pb.pool.unit)}</span></div>
          `).join("") || '<div class="mono-text">No earmarked pools cover this interest lineage.</div>'}
        </div>
        <div class="puck-card">
          <h4>Aligned Efforts (${(data.aligned_efforts || []).length})</h4>
          ${(data.aligned_efforts || []).map((n) => `
            <div class="staged-item mt-2"><span>${escapeHtml(n.effort.name)}</span><span class="mono-text">${escapeHtml(fmtForecast(n))}</span></div>
          `).join("") || '<div class="mono-text">No efforts aligned.</div>'}
        </div>
      `;
    }
  }

  global.EntityPuck = EntityPuck;
})(window);
