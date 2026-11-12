/* ==========================================================================
   Bijou v2 Lens 3: Entity & Graph Studio
   Full CRUD for Orgs, Pools, Interests, Efforts (Timing/Reqs/Risks/Mits),
   6 Typed Edges with Intelligence Pedigree, Diagnostics & Manifest JSON
   ========================================================================== */

(function (global) {
  "use strict";

  class StudioController {
    constructor(opts) {
      this.onGraphMutated = opts.onGraphMutated;
      this.notify = opts.notify;
      this.activeTab = "orgs";
      this.manifest = null;
      this.bodyEl = document.getElementById("studio-body");

      // Transient effort sub-item builders when editing/creating an Effort
      this.effortDraft = {
        reqs: [],
        risks: [],
        mits: [],
      };

      document.querySelectorAll(".studio-tab").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.activeTab = btn.dataset.tab;
          document.querySelectorAll(".studio-tab").forEach((b) => b.classList.toggle("active", b === btn));
          this.render();
        });
      });
    }

    setTab(tabName) {
      this.activeTab = tabName;
      document.querySelectorAll(".studio-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabName));
      this.render();
    }

    async refresh() {
      try {
        this.manifest = await global.BijouApi.exportManifest();
        this.render();
      } catch (err) {
        this.notify?.(`Studio failed to load manifest: ${err.message}`, "error");
      }
    }

    openEffortForEdit(effortId) {
      this.setTab("efforts");
      const eff = (this.manifest?.efforts || []).find((e) => e.id === effortId);
      if (eff) this.loadEffortIntoForm(eff);
    }

    render() {
      if (!this.bodyEl || !this.manifest) return;
      if (this.activeTab === "orgs") this.renderOrgsTab();
      else if (this.activeTab === "interests") this.renderInterestsTab();
      else if (this.activeTab === "efforts") this.renderEffortsTab();
      else if (this.activeTab === "edges") this.renderEdgesTab();
      else if (this.activeTab === "diagnostics") this.renderDiagnosticsTab();
    }

    renderOrgsTab() {
      const { escapeHtml } = global.BijouApi;
      const orgs = this.manifest.organizations || [];
      const pools = this.manifest.resource_pools || [];
      const interests = this.manifest.interests || [];

      this.bodyEl.innerHTML = `
        <div class="studio-split">
          <div class="stack-sm">
            <div class="studio-panel">
              <h3>Create / Update Organization</h3>
              <form id="st-org-form" class="studio-form">
                <label>ID <input type="text" id="st-org-id" placeholder="org-custom-01" required /></label>
                <label>Name <input type="text" id="st-org-name" required /></label>
                <label>Description <textarea id="st-org-desc"></textarea></label>
                <div class="form-row-2">
                  <label>Echelon Level <input type="number" min="0" value="1" id="st-org-echelon" /></label>
                  <label style="flex-direction:row;align-items:center;gap:8px;padding-top:14px">
                    <input type="checkbox" id="st-org-managed" /> Managed Org Owner
                  </label>
                </div>
                <label>Tags (comma-separated) <input type="text" id="st-org-tags" placeholder="managed, space" /></label>
                <button type="submit" class="btn btn-primary btn-sm">Save Organization</button>
              </form>
            </div>

            <div class="studio-panel">
              <h3>Create / Update Resource Pool (Color-of-Money)</h3>
              <form id="st-pool-form" class="studio-form">
                <label>Pool ID <input type="text" id="st-pool-id" placeholder="pool-fy27-01" required /></label>
                <label>Owning Org
                  <select id="st-pool-org" required>
                    ${orgs.map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)}</option>`).join("")}
                  </select>
                </label>
                <label>Name <input type="text" id="st-pool-name" required /></label>
                <div class="form-row-3">
                  <label>Category
                    <select id="st-pool-cat">
                      <option value="MONEY">MONEY</option>
                      <option value="STAFF">STAFF</option>
                      <option value="COMPUTE">COMPUTE</option>
                      <option value="MATERIAL">MATERIAL</option>
                    </select>
                  </label>
                  <label>Capacity <input type="number" step="any" min="0" value="100000" id="st-pool-cap" required /></label>
                  <label>Unit <input type="text" value="USD" id="st-pool-unit" required /></label>
                </div>
                <label>Skill / Compute Tag (Optional) <input type="text" id="st-pool-skill" placeholder="TS/SCI RF DSP Engineer" /></label>
                <label>Color-of-Money Restricted Interests (Hold Ctrl for multi; blank = Unrestricted)
                  <select id="st-pool-interests" multiple style="min-height:74px">
                    ${interests.map((i) => `<option value="${escapeHtml(i.id)}">${escapeHtml(i.name)} (${escapeHtml(i.id)})</option>`).join("")}
                  </select>
                </label>
                <button type="submit" class="btn btn-primary btn-sm">Save Resource Pool</button>
              </form>
            </div>
          </div>

          <div class="stack-sm">
            <div class="studio-panel">
              <h3>Organizations (${orgs.length})</h3>
              <table class="data-table">
                <thead><tr><th>ID / Name</th><th>Mode</th><th>Echelon</th><th>Actions</th></tr></thead>
                <tbody>
                  ${orgs.map((o) => `
                    <tr>
                      <td><strong>${escapeHtml(o.name)}</strong><div class="mono-text">${escapeHtml(o.id)}</div></td>
                      <td>${o.is_managed ? '<span class="mini-chip">Managed</span>' : "Modeled"}</td>
                      <td>${o.echelon_level}</td>
                      <td>
                        <button class="btn btn-secondary btn-xs st-edit-org" data-id="${escapeHtml(o.id)}">Edit</button>
                        <button class="btn btn-danger-outline btn-xs st-del-org" data-id="${escapeHtml(o.id)}">Del</button>
                      </td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>

            <div class="studio-panel">
              <h3>Resource Pools (${pools.length})</h3>
              <table class="data-table">
                <thead><tr><th>Pool</th><th>Org</th><th>Capacity</th><th>Earmarks</th><th>Actions</th></tr></thead>
                <tbody>
                  ${pools.map((p) => `
                    <tr>
                      <td><strong>${escapeHtml(p.name)}</strong><div class="mono-text">${escapeHtml(p.id)} · ${escapeHtml(p.skill_tag || "General")}</div></td>
                      <td class="mono-text">${escapeHtml(p.org_id)}</td>
                      <td>${p.capacity} ${escapeHtml(p.unit)}</td>
                      <td class="mono-text">${(p.restricted_interest_ids || []).join(", ") || "Unrestricted"}</td>
                      <td><button class="btn btn-danger-outline btn-xs st-del-pool" data-id="${escapeHtml(p.id)}">Del</button></td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;

      document.getElementById("st-org-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await global.BijouApi.upsertOrganization({
            id: document.getElementById("st-org-id").value.trim(),
            name: document.getElementById("st-org-name").value.trim(),
            description: document.getElementById("st-org-desc").value.trim(),
            echelon_level: parseInt(document.getElementById("st-org-echelon").value || "1", 10),
            is_managed: document.getElementById("st-org-managed").checked,
            tags: document.getElementById("st-org-tags").value.split(",").map((s) => s.trim()).filter(Boolean),
          });
          this.notify?.("Organization saved.", "success");
          await this.refresh();
          this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(err.message, "error");
        }
      });

      document.getElementById("st-pool-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const selOpts = Array.from(document.getElementById("st-pool-interests").selectedOptions).map((o) => o.value);
        try {
          await global.BijouApi.upsertResourcePool({
            id: document.getElementById("st-pool-id").value.trim(),
            org_id: document.getElementById("st-pool-org").value,
            name: document.getElementById("st-pool-name").value.trim(),
            category: document.getElementById("st-pool-cat").value,
            capacity: parseFloat(document.getElementById("st-pool-cap").value || "0"),
            unit: document.getElementById("st-pool-unit").value.trim(),
            skill_tag: document.getElementById("st-pool-skill").value.trim() || null,
            restricted_interest_ids: selOpts,
            description: "",
          });
          this.notify?.("Resource pool saved.", "success");
          await this.refresh();
          this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(err.message, "error");
        }
      });

      this.bodyEl.querySelectorAll(".st-edit-org").forEach((b) => {
        b.addEventListener("click", (ev) => {
          const o = orgs.find((x) => x.id === ev.target.dataset.id);
          if (!o) return;
          document.getElementById("st-org-id").value = o.id;
          document.getElementById("st-org-name").value = o.name;
          document.getElementById("st-org-desc").value = o.description || "";
          document.getElementById("st-org-echelon").value = String(o.echelon_level);
          document.getElementById("st-org-managed").checked = Boolean(o.is_managed);
          document.getElementById("st-org-tags").value = (o.tags || []).join(", ");
        });
      });

      this.bodyEl.querySelectorAll(".st-del-org").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          await global.BijouApi.deleteOrganization(ev.target.dataset.id);
          this.notify?.("Organization deleted.", "info");
          await this.refresh();
          this.onGraphMutated?.();
        });
      });

      this.bodyEl.querySelectorAll(".st-del-pool").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          await global.BijouApi.deleteResourcePool(ev.target.dataset.id);
          this.notify?.("Pool deleted.", "info");
          await this.refresh();
          this.onGraphMutated?.();
        });
      });
    }

    renderInterestsTab() {
      const { escapeHtml } = global.BijouApi;
      const interests = this.manifest.interests || [];
      const taxEdges = this.manifest.interest_interest_edges || [];

      this.bodyEl.innerHTML = `
        <div class="studio-split">
          <div class="studio-panel">
            <h3>Create / Update Interest</h3>
            <form id="st-intr-form" class="studio-form">
              <label>ID <input type="text" id="st-intr-id" placeholder="intr-new-priority" required /></label>
              <label>Name <input type="text" id="st-intr-name" required /></label>
              <label>Kind
                <select id="st-intr-kind">
                  <option value="STRATEGIC_CONCEPT">STRATEGIC_CONCEPT</option>
                  <option value="CAPABILITY_AREA">CAPABILITY_AREA</option>
                  <option value="MISSION_GOAL">MISSION_GOAL</option>
                  <option value="NIPF_PRIORITY">NIPF_PRIORITY</option>
                  <option value="INTELLIGENCE_GAP">INTELLIGENCE_GAP</option>
                  <option value="THREAT_VECTOR">THREAT_VECTOR</option>
                  <option value="CUSTOMER">CUSTOMER</option>
                  <option value="INVESTMENT">INVESTMENT</option>
                  <option value="COUNTRY">COUNTRY</option>
                  <option value="OTHER">OTHER</option>
                </select>
              </label>
              <label>Description <textarea id="st-intr-desc"></textarea></label>
              <div class="form-row-2">
                <label>Start Date (Optional) <input type="date" id="st-intr-start" /></label>
                <label>End Date (Optional) <input type="date" id="st-intr-end" /></label>
              </div>
              <button type="submit" class="btn btn-primary btn-sm">Save Interest</button>
            </form>
          </div>

          <div class="studio-panel">
            <h3>Interests (${interests.length}) &amp; Taxonomy Edges (${taxEdges.length})</h3>
            <table class="data-table">
              <thead><tr><th>Interest</th><th>Kind</th><th>Dates</th><th>Actions</th></tr></thead>
              <tbody>
                ${interests.map((i) => `
                  <tr>
                    <td><strong>${escapeHtml(i.name)}</strong><div class="mono-text">${escapeHtml(i.id)}</div></td>
                    <td>${escapeHtml(i.interest_kind)}</td>
                    <td class="mono-text">${escapeHtml(i.start_date || "∞")} → ${escapeHtml(i.end_date || "∞")}</td>
                    <td><button class="btn btn-danger-outline btn-xs st-del-intr" data-id="${escapeHtml(i.id)}">Del</button></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;

      document.getElementById("st-intr-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await global.BijouApi.upsertInterest({
            id: document.getElementById("st-intr-id").value.trim(),
            name: document.getElementById("st-intr-name").value.trim(),
            description: document.getElementById("st-intr-desc").value.trim(),
            interest_kind: document.getElementById("st-intr-kind").value,
            start_date: document.getElementById("st-intr-start").value || null,
            end_date: document.getElementById("st-intr-end").value || null,
          });
          this.notify?.("Interest saved.", "success");
          await this.refresh();
          this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(err.message, "error");
        }
      });

      this.bodyEl.querySelectorAll(".st-del-intr").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          await global.BijouApi.deleteInterest(ev.target.dataset.id);
          this.notify?.("Interest deleted.", "info");
          await this.refresh();
          this.onGraphMutated?.();
        });
      });
    }

    renderEffortsTab() {
      const { escapeHtml } = global.BijouApi;
      const efforts = this.manifest.efforts || [];

      this.bodyEl.innerHTML = `
        <div class="studio-split">
          <div class="studio-panel">
            <h3>Create / Update Effort</h3>
            <form id="st-eff-form" class="studio-form">
              <label>Effort ID <input type="text" id="st-eff-id" placeholder="eff-new-program" required /></label>
              <label>Name <input type="text" id="st-eff-name" required /></label>
              <label>State
                <select id="st-eff-state">
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="IN_WORK">IN_WORK</option>
                  <option value="BACKLOGGED">BACKLOGGED</option>
                  <option value="PLANNED" selected>PLANNED</option>
                  <option value="DISCOVERY_PENDING">DISCOVERY_PENDING</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </label>
              <label>Description <textarea id="st-eff-desc"></textarea></label>
              <div class="form-row-3">
                <label>Start Date <input type="date" id="st-eff-start" /></label>
                <label>End Date <input type="date" id="st-eff-end" /></label>
                <label>Est. Days <input type="number" min="1" id="st-eff-days" placeholder="Unknown" /></label>
              </div>

              <div class="sublist-box">
                <div class="card-top-row">
                  <strong>Resource Requirements (<span id="st-req-cnt">${this.effortDraft.reqs.length}</span>)</strong>
                  <button type="button" class="btn btn-secondary btn-xs" id="st-add-req">+ Req</button>
                </div>
                <div id="st-req-items" class="stack-xs"></div>
              </div>

              <div class="sublist-box">
                <div class="card-top-row">
                  <strong>Delivery Risks (<span id="st-risk-cnt">${this.effortDraft.risks.length}</span>)</strong>
                  <button type="button" class="btn btn-secondary btn-xs" id="st-add-risk">+ Risk</button>
                </div>
                <div id="st-risk-items" class="stack-xs"></div>
              </div>

              <div class="sublist-box">
                <div class="card-top-row">
                  <strong>Mitigator Options (<span id="st-mit-cnt">${this.effortDraft.mits.length}</span>)</strong>
                  <button type="button" class="btn btn-secondary btn-xs" id="st-add-mit">+ Mitigator</button>
                </div>
                <div id="st-mit-items" class="stack-xs"></div>
              </div>

              <button type="submit" class="btn btn-primary btn-sm">Save Effort</button>
            </form>
          </div>

          <div class="studio-panel">
            <h3>Efforts (${efforts.length})</h3>
            <table class="data-table">
              <thead><tr><th>Effort</th><th>State</th><th>Timing</th><th>Reqs / Risks / Mits</th><th>Actions</th></tr></thead>
              <tbody>
                ${efforts.map((ef) => `
                  <tr>
                    <td><strong>${escapeHtml(ef.name)}</strong><div class="mono-text">${escapeHtml(ef.id)}</div></td>
                    <td><span class="state-pill ${escapeHtml(ef.state)}">${escapeHtml(ef.state)}</span></td>
                    <td class="mono-text">${escapeHtml(ef.start_date || "null")} → ${escapeHtml(ef.end_date || "null")}${ef.estimated_duration_days ? ` (~${ef.estimated_duration_days}d)` : ""}</td>
                    <td class="mono-text">${(ef.resource_requirements || []).length}R / ${(ef.risks || []).length}K / ${(ef.mitigators || []).length}M</td>
                    <td>
                      <button class="btn btn-secondary btn-xs st-edit-eff" data-id="${escapeHtml(ef.id)}">Edit</button>
                      <button class="btn btn-danger-outline btn-xs st-del-eff" data-id="${escapeHtml(ef.id)}">Del</button>
                    </td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;

      this.renderEffortDraftLists();

      document.getElementById("st-add-req")?.addEventListener("click", () => {
        const eid = document.getElementById("st-eff-id").value.trim() || "eff";
        this.effortDraft.reqs.push({
          id: `req-${Date.now().toString(36).slice(-5)}`,
          category: "STAFF",
          label: `Requirement (${eid})`,
          quantity: 1,
          unit: "FTE",
          required_skill: null,
          estimated_cost_usd: 150000,
          is_generic: false,
        });
        this.renderEffortDraftLists();
      });

      document.getElementById("st-add-risk")?.addEventListener("click", () => {
        const eid = document.getElementById("st-eff-id").value.trim() || "eff";
        this.effortDraft.risks.push({
          id: `risk-${Date.now().toString(36).slice(-5)}`,
          effort_id: eid,
          title: "Schedule Slip Risk",
          description: "Key dependency or skill constraint risk",
          severity: "MEDIUM",
          likelihood: 0.5,
          potential_slip_days: 30,
          is_skill_mismatch_risk: false,
          status: "ACTIVE",
        });
        this.renderEffortDraftLists();
      });

      document.getElementById("st-add-mit")?.addEventListener("click", () => {
        const eid = document.getElementById("st-eff-id").value.trim() || "eff";
        this.effortDraft.mits.push({
          id: `mit-${Date.now().toString(36).slice(-5)}`,
          effort_id: eid,
          name: "Parallel Acceleration Option",
          description: "Additional staffing or contractor surge",
          is_exercised: false,
          slip_reduction_days: 25,
          risk_reduction_factor: 0.5,
          additional_requirements: [],
        });
        this.renderEffortDraftLists();
      });

      document.getElementById("st-eff-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const eid = document.getElementById("st-eff-id").value.trim();
        const daysRaw = document.getElementById("st-eff-days").value.trim();
        try {
          await global.BijouApi.upsertEffort({
            id: eid,
            name: document.getElementById("st-eff-name").value.trim(),
            description: document.getElementById("st-eff-desc").value.trim(),
            state: document.getElementById("st-eff-state").value,
            start_date: document.getElementById("st-eff-start").value || null,
            end_date: document.getElementById("st-eff-end").value || null,
            estimated_duration_days: daysRaw ? parseInt(daysRaw, 10) : null,
            resource_requirements: this.effortDraft.reqs,
            risks: this.effortDraft.risks.map((r) => ({ ...r, effort_id: eid })),
            mitigators: this.effortDraft.mits.map((m) => ({ ...m, effort_id: eid })),
          });
          this.notify?.("Effort saved.", "success");
          this.effortDraft = { reqs: [], risks: [], mits: [] };
          await this.refresh();
          this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(err.message, "error");
        }
      });

      this.bodyEl.querySelectorAll(".st-edit-eff").forEach((b) => {
        b.addEventListener("click", (ev) => {
          const ef = efforts.find((x) => x.id === ev.target.dataset.id);
          if (ef) this.loadEffortIntoForm(ef);
        });
      });

      this.bodyEl.querySelectorAll(".st-del-eff").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          await global.BijouApi.deleteEffort(ev.target.dataset.id);
          this.notify?.("Effort deleted.", "info");
          await this.refresh();
          this.onGraphMutated?.();
        });
      });
    }

    loadEffortIntoForm(ef) {
      document.getElementById("st-eff-id").value = ef.id;
      document.getElementById("st-eff-name").value = ef.name;
      document.getElementById("st-eff-state").value = ef.state;
      document.getElementById("st-eff-desc").value = ef.description || "";
      document.getElementById("st-eff-start").value = ef.start_date || "";
      document.getElementById("st-eff-end").value = ef.end_date || "";
      document.getElementById("st-eff-days").value = ef.estimated_duration_days || "";
      this.effortDraft = {
        reqs: JSON.parse(JSON.stringify(ef.resource_requirements || [])),
        risks: JSON.parse(JSON.stringify(ef.risks || [])),
        mits: JSON.parse(JSON.stringify(ef.mitigators || [])),
      };
      this.renderEffortDraftLists();
    }

    renderEffortDraftLists() {
      const { escapeHtml } = global.BijouApi;
      const reqEl = document.getElementById("st-req-items");
      const riskEl = document.getElementById("st-risk-items");
      const mitEl = document.getElementById("st-mit-items");
      if (!reqEl) return;

      document.getElementById("st-req-cnt").textContent = String(this.effortDraft.reqs.length);
      document.getElementById("st-risk-cnt").textContent = String(this.effortDraft.risks.length);
      document.getElementById("st-mit-cnt").textContent = String(this.effortDraft.mits.length);

      reqEl.innerHTML = this.effortDraft.reqs
        .map((r, i) => `
          <div class="staged-item">
            <input type="text" class="dr-req-label" data-idx="${i}" value="${escapeHtml(r.label)}" style="width:45%" />
            <input type="text" class="dr-req-skill" data-idx="${i}" value="${escapeHtml(r.required_skill || "")}" placeholder="Skill" style="width:30%" />
            <button type="button" class="btn btn-ghost btn-xs dr-rm-req" data-idx="${i}">×</button>
          </div>
        `).join("");

      riskEl.innerHTML = this.effortDraft.risks
        .map((r, i) => `
          <div class="staged-item">
            <input type="text" class="dr-risk-title" data-idx="${i}" value="${escapeHtml(r.title)}" style="width:60%" />
            <input type="number" class="dr-risk-slip" data-idx="${i}" value="${r.potential_slip_days}" style="width:22%" />
            <button type="button" class="btn btn-ghost btn-xs dr-rm-risk" data-idx="${i}">×</button>
          </div>
        `).join("");

      mitEl.innerHTML = this.effortDraft.mits
        .map((m, i) => `
          <div class="staged-item">
            <input type="text" class="dr-mit-name" data-idx="${i}" value="${escapeHtml(m.name)}" style="width:60%" />
            <input type="number" class="dr-mit-slip" data-idx="${i}" value="${m.slip_reduction_days}" style="width:22%" />
            <button type="button" class="btn btn-ghost btn-xs dr-rm-mit" data-idx="${i}">×</button>
          </div>
        `).join("");

      reqEl.querySelectorAll(".dr-req-label").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.reqs[Number(e.target.dataset.idx)].label = e.target.value;
      }));
      reqEl.querySelectorAll(".dr-req-skill").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.reqs[Number(e.target.dataset.idx)].required_skill = e.target.value.trim() || null;
      }));
      reqEl.querySelectorAll(".dr-rm-req").forEach((b) => b.addEventListener("click", (e) => {
        this.effortDraft.reqs.splice(Number(e.target.dataset.idx), 1);
        this.renderEffortDraftLists();
      }));

      riskEl.querySelectorAll(".dr-risk-title").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.risks[Number(e.target.dataset.idx)].title = e.target.value;
      }));
      riskEl.querySelectorAll(".dr-risk-slip").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.risks[Number(e.target.dataset.idx)].potential_slip_days = parseInt(e.target.value || "0", 10);
      }));
      riskEl.querySelectorAll(".dr-rm-risk").forEach((b) => b.addEventListener("click", (e) => {
        this.effortDraft.risks.splice(Number(e.target.dataset.idx), 1);
        this.renderEffortDraftLists();
      }));

      mitEl.querySelectorAll(".dr-mit-name").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.mits[Number(e.target.dataset.idx)].name = e.target.value;
      }));
      mitEl.querySelectorAll(".dr-mit-slip").forEach((inp) => inp.addEventListener("input", (e) => {
        this.effortDraft.mits[Number(e.target.dataset.idx)].slip_reduction_days = parseInt(e.target.value || "0", 10);
      }));
      mitEl.querySelectorAll(".dr-rm-mit").forEach((b) => b.addEventListener("click", (e) => {
        this.effortDraft.mits.splice(Number(e.target.dataset.idx), 1);
        this.renderEffortDraftLists();
      }));
    }

    renderEdgesTab() {
      const { escapeHtml } = global.BijouApi;
      const orgs = this.manifest.organizations || [];
      const intrs = this.manifest.interests || [];
      const effs = this.manifest.efforts || [];
      const allEdges = [
        ...(this.manifest.org_org_edges || []).map((e) => ({ cat: "org_org_edge", label: `ORG->ORG (${e.relation_type}): ${e.source_org_id} → ${e.target_org_id}`, ...e })),
        ...(this.manifest.org_interest_edges || []).map((e) => ({ cat: "org_interest_edge", label: `ORG->INTR (${e.stance}, P=${e.priority_rank}): ${e.org_id} → ${e.interest_id}`, ...e })),
        ...(this.manifest.interest_interest_edges || []).map((e) => ({ cat: "interest_interest_edge", label: `INTR->INTR (${e.relation_type}): ${e.parent_interest_id} → ${e.child_interest_id}`, ...e })),
        ...(this.manifest.org_effort_edges || []).map((e) => ({ cat: "org_effort_edge", label: `ORG->EFF (${e.resourcing_type} ${e.allocation_amount} ${e.allocation_unit}): ${e.org_id} → ${e.effort_id}`, ...e })),
        ...(this.manifest.effort_interest_edges || []).map((e) => ({ cat: "effort_interest_edge", label: `EFF->INTR (${e.relation_type}, W=${e.impact_weight}): ${e.effort_id} → ${e.interest_id}`, ...e })),
        ...(this.manifest.effort_effort_edges || []).map((e) => ({ cat: "effort_effort_edge", label: `EFF->EFF (${e.blocking_mode}, deg=${e.dependency_degree}): ${e.source_effort_id} → ${e.target_effort_id}`, ...e })),
      ];

      this.bodyEl.innerHTML = `
        <div class="studio-split">
          <div class="studio-panel">
            <h3>Author Typed Relationship + Intelligence Pedigree</h3>
            <form id="st-edge-form" class="studio-form">
              <label>Relationship Category
                <select id="st-edge-kind">
                  <option value="effort_effort">Effort → Effort (Dependency)</option>
                  <option value="org_effort">Org → Effort (Direct Resourcing)</option>
                  <option value="effort_interest">Effort → Interest (Alignment)</option>
                  <option value="org_interest">Org → Interest (Stance &amp; Priority)</option>
                  <option value="interest_interest">Interest → Interest (Taxonomy Parent→Child)</option>
                  <option value="org_org">Org → Org (Hierarchy / Collaboration)</option>
                </select>
              </label>
              <div id="st-edge-dynamic-fields" class="studio-form"></div>
              <div class="form-row-2">
                <label>Pedigree Confidence
                  <select id="st-edge-conf">
                    <option value="CONFIRMED">CONFIRMED</option>
                    <option value="ASSESSED">ASSESSED</option>
                    <option value="UNCONFIRMED">UNCONFIRMED</option>
                  </select>
                </label>
                <label>Provenance Note
                  <input type="text" id="st-edge-prov" placeholder="Source doc / assessment basis" />
                </label>
              </div>
              <button type="submit" class="btn btn-primary btn-sm">Upsert Relationship Edge</button>
            </form>
          </div>

          <div class="studio-panel">
            <h3>All Typed Graph Relationships (${allEdges.length})</h3>
            <table class="data-table">
              <thead><tr><th>Edge Summary</th><th>Pedigree</th><th>Del</th></tr></thead>
              <tbody>
                ${allEdges.map((ed) => `
                  <tr>
                    <td><strong>${escapeHtml(ed.label)}</strong><div class="mono-text">${escapeHtml(ed.id)}${ed.provenance_note ? ` · ${escapeHtml(ed.provenance_note)}` : ""}</div></td>
                    <td><span class="state-pill">${escapeHtml(ed.confidence)}</span></td>
                    <td><button class="btn btn-danger-outline btn-xs st-del-edge" data-cat="${escapeHtml(ed.cat)}" data-id="${escapeHtml(ed.id)}">Del</button></td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;

      const kindSel = document.getElementById("st-edge-kind");
      const dynEl = document.getElementById("st-edge-dynamic-fields");
      const orgOpts = orgs.map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)}</option>`).join("");
      const intrOpts = intrs.map((i) => `<option value="${escapeHtml(i.id)}">${escapeHtml(i.name)}</option>`).join("");
      const effOpts = effs.map((e) => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("");

      const renderFields = () => {
        const k = kindSel.value;
        if (k === "effort_effort") {
          dynEl.innerHTML = `
            <label>Source (Upstream) Effort <select id="ed-src">${effOpts}</select></label>
            <label>Target (Downstream) Effort <select id="ed-dst">${effOpts}</select></label>
            <div class="form-row-2">
              <label>Blocking Mode
                <select id="ed-mode"><option value="BLOCKING">BLOCKING</option><option value="NON_BLOCKING_INFORMS">NON_BLOCKING_INFORMS</option></select>
              </label>
              <label>Degree (0.0-1.0) <input type="number" step="0.1" min="0" max="1" value="1.0" id="ed-deg" /></label>
            </div>
          `;
        } else if (k === "org_effort") {
          dynEl.innerHTML = `
            <label>Organization <select id="ed-org">${orgOpts}</select></label>
            <label>Target Effort <select id="ed-eff">${effOpts}</select></label>
            <div class="form-row-3">
              <label>Type <select id="ed-rtype"><option value="MONEY">MONEY</option><option value="STAFF">STAFF</option><option value="COMPUTE">COMPUTE</option><option value="MATERIAL">MATERIAL</option><option value="GENERIC_SUPPORT">GENERIC</option></select></label>
              <label>Amount <input type="number" step="any" min="0" value="100000" id="ed-amt" /></label>
              <label>Unit <input type="text" value="USD" id="ed-unit" /></label>
            </div>
          `;
        } else if (k === "effort_interest") {
          dynEl.innerHTML = `
            <label>Effort <select id="ed-eff">${effOpts}</select></label>
            <label>Interest <select id="ed-intr">${intrOpts}</select></label>
            <div class="form-row-2">
              <label>Relation <select id="ed-rel"><option value="DIRECT_SOLUTION">DIRECT_SOLUTION</option><option value="INDIRECT_ENABLER">INDIRECT_ENABLER</option><option value="FUNDED_FOR">FUNDED_FOR</option><option value="PARTIAL_ALIGNMENT">PARTIAL_ALIGNMENT</option></select></label>
              <label>Weight <input type="number" step="0.1" min="0" max="1" value="0.9" id="ed-wt" /></label>
            </div>
          `;
        } else if (k === "org_interest") {
          dynEl.innerHTML = `
            <label>Organization <select id="ed-org">${orgOpts}</select></label>
            <label>Interest <select id="ed-intr">${intrOpts}</select></label>
            <div class="form-row-2">
              <label>Stance <select id="ed-stance"><option value="RESPONSIBLE_OWNER">RESPONSIBLE_OWNER</option><option value="DIRECT_INVESTOR">DIRECT_INVESTOR</option><option value="MISSION_ALIGNED">MISSION_ALIGNED</option><option value="BENEFICIARY">BENEFICIARY</option><option value="PERCEIVED_GAP">PERCEIVED_GAP</option></select></label>
              <label>Priority (0-1) <input type="number" step="0.05" min="0" max="1" value="0.8" id="ed-prio" /></label>
            </div>
          `;
        } else if (k === "interest_interest") {
          dynEl.innerHTML = `
            <label>Parent (Broader) Interest <select id="ed-src">${intrOpts}</select></label>
            <label>Child (Specific) Interest <select id="ed-dst">${intrOpts}</select></label>
            <label>Relation <select id="ed-rel"><option value="SPECIALIZES">SPECIALIZES</option><option value="CONTRIBUTES_TO">CONTRIBUTES_TO</option><option value="RELATED_TO">RELATED_TO</option></select></label>
          `;
        } else {
          dynEl.innerHTML = `
            <label>Source Org <select id="ed-src">${orgOpts}</select></label>
            <label>Target Org <select id="ed-dst">${orgOpts}</select></label>
            <label>Relation <select id="ed-rel"><option value="HIERARCHICAL_PARENT">HIERARCHICAL_PARENT</option><option value="FORMAL_SUPPORTING">FORMAL_SUPPORTING</option><option value="COLLABORATIVE_ADJACENT">COLLABORATIVE_ADJACENT</option><option value="CO_SPONSOR">CO_SPONSOR</option></select></label>
          `;
        }
      };

      kindSel.addEventListener("change", renderFields);
      renderFields();

      document.getElementById("st-edge-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const k = kindSel.value;
        const base = {
          confidence: document.getElementById("st-edge-conf").value,
          provenance_note: document.getElementById("st-edge-prov").value.trim() || null,
        };
        try {
          if (k === "effort_effort") {
            await global.BijouApi.upsertEffortEffortEdge({
              ...base,
              source_effort_id: document.getElementById("ed-src").value,
              target_effort_id: document.getElementById("ed-dst").value,
              blocking_mode: document.getElementById("ed-mode").value,
              dependency_degree: parseFloat(document.getElementById("ed-deg").value || "1"),
            });
          } else if (k === "org_effort") {
            await global.BijouApi.upsertOrgEffortEdge({
              ...base,
              org_id: document.getElementById("ed-org").value,
              effort_id: document.getElementById("ed-eff").value,
              resourcing_type: document.getElementById("ed-rtype").value,
              allocation_amount: parseFloat(document.getElementById("ed-amt").value || "0"),
              allocation_unit: document.getElementById("ed-unit").value.trim() || "UNITS",
              is_generic: true,
            });
          } else if (k === "effort_interest") {
            await global.BijouApi.upsertEffortInterestEdge({
              ...base,
              effort_id: document.getElementById("ed-eff").value,
              interest_id: document.getElementById("ed-intr").value,
              relation_type: document.getElementById("ed-rel").value,
              impact_weight: parseFloat(document.getElementById("ed-wt").value || "1"),
            });
          } else if (k === "org_interest") {
            await global.BijouApi.upsertOrgInterestEdge({
              ...base,
              org_id: document.getElementById("ed-org").value,
              interest_id: document.getElementById("ed-intr").value,
              stance: document.getElementById("ed-stance").value,
              priority_rank: parseFloat(document.getElementById("ed-prio").value || "0.5"),
              allow_hierarchy_inheritance: true,
            });
          } else if (k === "interest_interest") {
            await global.BijouApi.upsertInterestInterestEdge({
              ...base,
              parent_interest_id: document.getElementById("ed-src").value,
              child_interest_id: document.getElementById("ed-dst").value,
              relation_type: document.getElementById("ed-rel").value,
            });
          } else {
            await global.BijouApi.upsertOrgOrgEdge({
              ...base,
              source_org_id: document.getElementById("ed-src").value,
              target_org_id: document.getElementById("ed-dst").value,
              relation_type: document.getElementById("ed-rel").value,
            });
          }
          this.notify?.("Relationship edge saved.", "success");
          await this.refresh();
          this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(`Edge error: ${err.message}`, "error");
        }
      });

      this.bodyEl.querySelectorAll(".st-del-edge").forEach((b) => {
        b.addEventListener("click", async (ev) => {
          await global.BijouApi.deleteEdge(ev.target.dataset.cat, ev.target.dataset.id);
          this.notify?.("Edge deleted.", "info");
          await this.refresh();
          this.onGraphMutated?.();
        });
      });
    }

    async renderDiagnosticsTab() {
      const { escapeHtml } = global.BijouApi;
      this.bodyEl.innerHTML = '<div class="empty-state">Running pre-flight portfolio diagnostics...</div>';
      try {
        const diag = await global.BijouApi.validateManifest();
        this.bodyEl.innerHTML = `
          <div class="studio-split">
            <div class="studio-panel">
              <h3>Pre-Flight Graph &amp; Resource Diagnostics</h3>
              <div class="staged-item mt-2"><span>Effort DAG Cycles</span><strong>${diag.effort_cycles.length}</strong></div>
              <div class="staged-item mt-2"><span>Interest DAG Cycles</span><strong>${diag.interest_cycles.length}</strong></div>
              <div class="staged-item mt-2"><span>Color-of-Money Violations</span><strong>${diag.color_of_money_violations.length}</strong></div>
              <div class="staged-item mt-2"><span>Overallocated Pools</span><strong>${diag.overallocated_pools.length}</strong></div>
              <div class="staged-item mt-2"><span>Skill Mismatch Risks</span><strong>${diag.skill_mismatch_risks.length}</strong></div>
              ${diag.blockers.map((b) => `<div class="hint-banner warn mt-2">${escapeHtml(b)}</div>`).join("")}
              ${diag.warnings.map((w) => `<div class="hint-banner mt-2">${escapeHtml(w)}</div>`).join("")}
            </div>

            <div class="studio-panel">
              <h3>Canonical Bijou v2 Manifest JSON</h3>
              <textarea id="st-manifest-json" style="width:100%;min-height:360px;font-family:var(--font-mono);font-size:0.72rem;background:var(--bg-primary);color:var(--text-main);border:1px solid var(--border-subtle);padding:8px">${escapeHtml(JSON.stringify(this.manifest, null, 2))}</textarea>
              <div class="btn-row-2 mt-2">
                <button class="btn btn-secondary btn-sm" id="st-manifest-import-merge">Import Merge</button>
                <button class="btn btn-danger-outline btn-sm" id="st-manifest-import-replace">Import Replace-All</button>
              </div>
            </div>
          </div>
        `;

        const doImport = async (replaceAll) => {
          try {
            const payload = JSON.parse(document.getElementById("st-manifest-json").value);
            await global.BijouApi.importManifest(payload, replaceAll);
            this.notify?.("Manifest imported.", "success");
            await this.refresh();
            this.onGraphMutated?.();
          } catch (err) {
            this.notify?.(`Import error: ${err.message}`, "error");
          }
        };

        document.getElementById("st-manifest-import-merge")?.addEventListener("click", () => doImport(false));
        document.getElementById("st-manifest-import-replace")?.addEventListener("click", () => doImport(true));
      } catch (err) {
        this.bodyEl.innerHTML = `<div class="hint-banner warn">${escapeHtml(err.message)}</div>`;
      }
    }
  }

  global.StudioController = StudioController;
})(window);

