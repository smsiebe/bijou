/* ==========================================================================
   Bijou v2 View C: Bill of Efforts Scenario Cart & Live Simulation Dock
   Manages Mitigator Toggles, Pool Allocations (Color-of-Money & Skill Mismatch),
   Schedule Shocks, KPI Deltas, and Commit-to-Graph
   ========================================================================== */

(function (global) {
  "use strict";

  class BillOfEffortsDock {
    constructor(opts) {
      this.onSimulationUpdated = opts.onSimulationUpdated;
      this.onCommitted = opts.onCommitted;
      this.notify = opts.notify;

      this.request = {
        toggle_mitigators: {},
        add_allocations: [],
        remove_edge_ids: [],
        effort_slips: {},
        cancelled_effort_ids: [],
      };
      this.latestSimulation = null;
      this.baselineTree = null;
      this.poolBalances = [];
      this.bindDom();
    }

    bindDom() {
      const byId = (id) => document.getElementById(id);
      this.dockEl = byId("bill-of-efforts-dock");
      this.badgeCountEl = byId("cart-badge-count");

      this.allocForm = byId("boe-alloc-form");
      this.allocOrg = byId("boe-alloc-org");
      this.allocPool = byId("boe-alloc-pool");
      this.allocEffort = byId("boe-alloc-effort");
      this.allocReq = byId("boe-alloc-req");
      this.allocCat = byId("boe-alloc-cat");
      this.allocAmount = byId("boe-alloc-amount");
      this.allocUnit = byId("boe-alloc-unit");
      this.allocSkill = byId("boe-alloc-skill");
      this.allocPenalty = byId("boe-alloc-slip-penalty");
      this.allocHint = byId("boe-alloc-eligibility-hint");

      this.shockForm = byId("boe-shock-form");
      this.shockEffort = byId("boe-shock-effort");
      this.shockDays = byId("boe-shock-days");

      this.allocOrg?.addEventListener("change", () => this.populatePoolOptions());
      this.allocPool?.addEventListener("change", () => this.syncFromSelectedPool());
      this.allocEffort?.addEventListener("change", () => {
        this.populateReqOptions();
        this.updateAllocationEligibilityHint();
      });
      this.allocReq?.addEventListener("change", () => this.syncFromSelectedReq());
      this.allocSkill?.addEventListener("input", () => this.updateAllocationEligibilityHint());

      this.allocForm?.addEventListener("submit", (e) => {
        e.preventDefault();
        this.stageAllocationFromForm();
      });

      this.shockForm?.addEventListener("submit", (e) => {
        e.preventDefault();
        const eid = this.shockEffort.value;
        const days = parseInt(this.shockDays.value || "0", 10);
        if (!eid) return;
        this.request.effort_slips[eid] = days;
        this.updateCartCount();
        this.simulate();
      });

      byId("btn-boe-cancel-effort")?.addEventListener("click", () => {
        const eid = this.shockEffort.value;
        if (!eid) return;
        const idx = this.request.cancelled_effort_ids.indexOf(eid);
        if (idx >= 0) this.request.cancelled_effort_ids.splice(idx, 1);
        else this.request.cancelled_effort_ids.push(eid);
        this.updateCartCount();
        this.simulate();
      });

      byId("btn-boe-reset")?.addEventListener("click", () => this.reset());
      byId("btn-boe-simulate")?.addEventListener("click", () => this.simulate());
      byId("btn-boe-commit")?.addEventListener("click", () => this.commit());
    }

    setOpen(open) {
      if (!this.dockEl) return;
      this.dockEl.classList.toggle("hidden", !open);
    }

    isOpen() {
      return this.dockEl && !this.dockEl.classList.contains("hidden");
    }

    setBaseline(treeView, poolBalances) {
      this.baselineTree = treeView;
      this.poolBalances = poolBalances || [];
      this.populateFormSelectors();
      this.renderStaticLists();
      if (!this.latestSimulation) {
        this.renderSimulationOutput({
          projected_tree: treeView,
          pool_balances: this.poolBalances,
          skill_mismatch_warnings: [],
          newly_registered_risks: [],
          impacted_effort_ids: [],
          total_cost_delta: 0,
          net_risk_count_delta: 0,
        });
      }
    }

    stageMitigator(mitigatorId, exercised) {
      this.request.toggle_mitigators[mitigatorId] = Boolean(exercised);
      this.updateCartCount();
      this.setOpen(true);
      return this.simulate();
    }

    updateCartCount() {
      const count =
        Object.keys(this.request.toggle_mitigators).length +
        this.request.add_allocations.length +
        this.request.remove_edge_ids.length +
        Object.keys(this.request.effort_slips).length +
        this.request.cancelled_effort_ids.length;
      if (this.badgeCountEl) this.badgeCountEl.textContent = String(count);
    }

    reset() {
      this.request = {
        toggle_mitigators: {},
        add_allocations: [],
        remove_edge_ids: [],
        effort_slips: {},
        cancelled_effort_ids: [],
      };
      this.latestSimulation = null;
      this.updateCartCount();
      this.renderStaticLists();
      if (this.baselineTree) {
        this.renderSimulationOutput({
          projected_tree: this.baselineTree,
          pool_balances: this.poolBalances,
          skill_mismatch_warnings: [],
          newly_registered_risks: [],
          impacted_effort_ids: [],
          total_cost_delta: 0,
          net_risk_count_delta: 0,
        });
      }
      if (this.onSimulationUpdated) this.onSimulationUpdated(null);
      this.notify?.("Bill of Efforts scenario cart cleared.", "info");
    }

    async simulate(asOfDate) {
      try {
        const res = await global.BijouApi.simulateBillOfEfforts(this.request, asOfDate ? { as_of_date: asOfDate } : null);
        this.latestSimulation = res;
        this.renderSimulationOutput(res);
        if (this.onSimulationUpdated) this.onSimulationUpdated(res);
        return res;
      } catch (err) {
        this.notify?.(`Simulation failed: ${err.message}`, "error");
        return null;
      }
    }

    async commit(asOfDate) {
      try {
        const res = await global.BijouApi.commitBillOfEfforts(this.request, asOfDate ? { as_of_date: asOfDate } : null);
        this.notify?.("Bill of Efforts scenario committed to persistent graph.", "success");
        this.request = {
          toggle_mitigators: {},
          add_allocations: [],
          remove_edge_ids: [],
          effort_slips: {},
          cancelled_effort_ids: [],
        };
        this.latestSimulation = null;
        this.updateCartCount();
        if (this.onCommitted) await this.onCommitted(res);
      } catch (err) {
        this.notify?.(`Commit blocked (${err.status || "Error"}): ${err.message}`, "error");
      }
    }

    populateFormSelectors() {
      if (!this.baselineTree) return;
      const { escapeHtml } = global.BijouApi;
      const orgs = this.baselineTree.organizations || [];
      const efforts = (this.baselineTree.nodes || []).map((n) => n.effort);

      const prevOrg = this.allocOrg.value;
      this.allocOrg.innerHTML = orgs
        .map((o) => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.name)} ${o.is_managed ? "(Managed)" : ""}</option>`)
        .join("");
      if (prevOrg && orgs.some((o) => o.id === prevOrg)) this.allocOrg.value = prevOrg;

      const prevEff = this.allocEffort.value;
      const effOpts = efforts.map((e) => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.name)}</option>`).join("");
      this.allocEffort.innerHTML = effOpts;
      this.shockEffort.innerHTML = effOpts;
      if (prevEff && efforts.some((e) => e.id === prevEff)) this.allocEffort.value = prevEff;

      this.populatePoolOptions();
      this.populateReqOptions();
    }

    populatePoolOptions() {
      const { escapeHtml } = global.BijouApi;
      const orgId = this.allocOrg.value;
      const pools = (this.baselineTree?.resource_pools || []).filter((p) => p.org_id === orgId);
      this.allocPool.innerHTML =
        `<option value="">Generic / Unmanaged Contribution</option>` +
        pools.map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)} (${p.capacity} ${escapeHtml(p.unit)})</option>`).join("");
      this.syncFromSelectedPool();
    }

    populateReqOptions() {
      const { escapeHtml } = global.BijouApi;
      const eid = this.allocEffort.value;
      const node = (this.baselineTree?.nodes || []).find((n) => n.effort.id === eid);
      const reqs = node?.effort?.resource_requirements || [];
      this.allocReq.innerHTML =
        `<option value="">General Effort Support</option>` +
        reqs
          .map(
            (r) =>
              `<option value="${escapeHtml(r.id)}">${escapeHtml(r.label)} (${r.quantity} ${escapeHtml(r.unit)}${
                r.required_skill ? ` · Skill: ${escapeHtml(r.required_skill)}` : ""
              })</option>`
          )
          .join("");
      this.syncFromSelectedReq();
    }

    syncFromSelectedPool() {
      const poolId = this.allocPool.value;
      const pool = (this.baselineTree?.resource_pools || []).find((p) => p.id === poolId);
      if (pool) {
        this.allocCat.value = pool.category;
        this.allocUnit.value = pool.unit;
        if (pool.skill_tag) this.allocSkill.value = pool.skill_tag;
      }
      this.updateAllocationEligibilityHint();
    }

    syncFromSelectedReq() {
      const eid = this.allocEffort.value;
      const reqId = this.allocReq.value;
      const node = (this.baselineTree?.nodes || []).find((n) => n.effort.id === eid);
      const req = (node?.effort?.resource_requirements || []).find((r) => r.id === reqId);
      if (req && !this.allocPool.value) {
        this.allocCat.value = req.category;
        this.allocUnit.value = req.unit;
        this.allocAmount.value = String(req.quantity || 1);
      }
      this.updateAllocationEligibilityHint();
    }

    updateAllocationEligibilityHint() {
      if (!this.allocHint || !this.baselineTree) return;
      const { escapeHtml } = global.BijouApi;
      const hints = [];
      let isWarn = false;

      const poolId = this.allocPool.value;
      const eid = this.allocEffort.value;
      const reqId = this.allocReq.value;
      const node = (this.baselineTree.nodes || []).find((n) => n.effort.id === eid);

      if (poolId && node) {
        const pb = (this.latestSimulation?.pool_balances || this.poolBalances || []).find((b) => b.pool.id === poolId);
        if (pb && pb.pool.restricted_interest_ids?.length > 0) {
          const eligible = new Set(pb.eligible_interest_ids || []);
          const aligned = node.aligned_interest_ids || [];
          const ok = aligned.some((iid) => eligible.has(iid));
          if (ok) {
            hints.push(`Color-of-Money Eligible: Effort aligns with ${pb.pool.name}'s Interest lineage.`);
          } else {
            isWarn = true;
            hints.push(`Color-of-Money Violation Warning: Effort does NOT align with ${pb.pool.name}'s earmarked Interests!`);
          }
        }
      }

      if (reqId && node) {
        const req = (node.effort.resource_requirements || []).find((r) => r.id === reqId);
        const assigned = (this.allocSkill.value || "").trim();
        if (req?.required_skill && assigned && req.required_skill.toLowerCase() !== assigned.toLowerCase()) {
          isWarn = true;
          hints.push(`Skill Mismatch: Requires "${req.required_skill}", assigning "${assigned}". Will register a Slip Risk!`);
        }
      }

      if (!hints.length) {
        this.allocHint.classList.add("hidden");
        this.allocHint.textContent = "";
      } else {
        this.allocHint.classList.remove("hidden");
        this.allocHint.classList.toggle("warn", isWarn);
        this.allocHint.innerHTML = hints.map((h) => `<div>${escapeHtml(h)}</div>`).join("");
      }
    }

    stageAllocationFromForm() {
      const penaltyRaw = this.allocPenalty.value.trim();
      const alloc = {
        org_id: this.allocOrg.value,
        pool_id: this.allocPool.value || null,
        effort_id: this.allocEffort.value,
        requirement_id: this.allocReq.value || null,
        resourcing_type: this.allocCat.value,
        amount: parseFloat(this.allocAmount.value || "0"),
        unit: this.allocUnit.value.trim() || "UNITS",
        assigned_skill: this.allocSkill.value.trim() || null,
        is_generic: !this.allocPool.value,
        human_slip_penalty_days: penaltyRaw !== "" ? parseInt(penaltyRaw, 10) : null,
      };
      this.request.add_allocations.push(alloc);
      this.updateCartCount();
      this.renderStaticLists();
      this.simulate();
    }

    renderStaticLists() {
      const { escapeHtml } = global.BijouApi;
      // Render all mitigator options across efforts
      const mitList = document.getElementById("boe-mitigator-list");
      if (mitList && this.baselineTree) {
        const rows = [];
        (this.baselineTree.nodes || []).forEach((n) => {
          (n.effort.mitigators || []).forEach((m) => {
            const currentVal =
              m.id in this.request.toggle_mitigators ? this.request.toggle_mitigators[m.id] : m.is_exercised;
            rows.push({ effort: n.effort, mit: m, exercised: currentVal });
          });
        });

        mitList.innerHTML = rows.length
          ? rows
              .map(
                (r) => `
              <label class="mitigator-row">
                <div>
                  <div><strong>${escapeHtml(r.mit.name)}</strong></div>
                  <div class="mono-text">${escapeHtml(r.effort.name)} · -${r.mit.slip_reduction_days}d slip</div>
                </div>
                <input type="checkbox" class="boe-mit-toggle" data-mit-id="${escapeHtml(r.mit.id)}" ${r.exercised ? "checked" : ""} />
              </label>
            `
              )
              .join("")
          : '<div class="mono-text">No mitigators defined yet.</div>';

        mitList.querySelectorAll(".boe-mit-toggle").forEach((cb) => {
          cb.addEventListener("change", (ev) => {
            const mid = ev.target.dataset.mitId;
            this.request.toggle_mitigators[mid] = Boolean(ev.target.checked);
            this.updateCartCount();
            this.simulate();
          });
        });
      }

      // Render staged allocations
      const stagedEl = document.getElementById("boe-staged-allocations");
      if (stagedEl) {
        stagedEl.innerHTML = this.request.add_allocations
          .map(
            (a, idx) => `
            <div class="staged-item">
              <span>${escapeHtml(a.org_id)} → ${escapeHtml(a.effort_id)} (${a.amount} ${escapeHtml(a.unit)}${a.assigned_skill ? ` · ${escapeHtml(a.assigned_skill)}` : ""})</span>
              <button class="btn btn-ghost btn-xs boe-rm-alloc" data-idx="${idx}">×</button>
            </div>
          `
          )
          .join("");
        stagedEl.querySelectorAll(".boe-rm-alloc").forEach((b) => {
          b.addEventListener("click", (ev) => {
            this.request.add_allocations.splice(Number(ev.target.dataset.idx), 1);
            this.updateCartCount();
            this.renderStaticLists();
            this.simulate();
          });
        });
      }

      // Render staged shocks & cancellations
      const shockEl = document.getElementById("boe-staged-shocks");
      if (shockEl) {
        const items = [];
        Object.entries(this.request.effort_slips).forEach(([eid, d]) => {
          items.push(`<div class="staged-item"><span>Slip +${d}d on ${escapeHtml(eid)}</span><button class="btn btn-ghost btn-xs boe-rm-slip" data-eid="${escapeHtml(eid)}">×</button></div>`);
        });
        this.request.cancelled_effort_ids.forEach((eid) => {
          items.push(`<div class="staged-item"><span>Cancelled: ${escapeHtml(eid)}</span><button class="btn btn-ghost btn-xs boe-rm-cancel" data-eid="${escapeHtml(eid)}">×</button></div>`);
        });
        shockEl.innerHTML = items.join("");
        shockEl.querySelectorAll(".boe-rm-slip").forEach((b) => {
          b.addEventListener("click", (ev) => {
            delete this.request.effort_slips[ev.target.dataset.eid];
            this.updateCartCount();
            this.renderStaticLists();
            this.simulate();
          });
        });
        shockEl.querySelectorAll(".boe-rm-cancel").forEach((b) => {
          b.addEventListener("click", (ev) => {
            this.request.cancelled_effort_ids = this.request.cancelled_effort_ids.filter((x) => x !== ev.target.dataset.eid);
            this.updateCartCount();
            this.renderStaticLists();
            this.simulate();
          });
        });
      }
    }

    renderSimulationOutput(sim) {
      const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
      document.getElementById("boe-cost-delta").textContent = fmtUsd(sim.total_cost_delta || 0);
      const rDelta = Number(sim.net_risk_count_delta || 0);
      document.getElementById("boe-risk-delta").textContent = rDelta > 0 ? `+${rDelta}` : String(rDelta);
      document.getElementById("boe-impacted-count").textContent = String((sim.impacted_effort_ids || []).length);

      // Skill mismatch alerts
      const mmSec = document.getElementById("boe-mismatch-section");
      const mmList = document.getElementById("boe-mismatch-list");
      const warnings = sim.skill_mismatch_warnings || [];
      if (warnings.length) {
        mmSec.classList.remove("hidden");
        mmList.innerHTML = warnings
          .map(
            (w) => `
            <div class="hint-banner warn">
              <strong>${escapeHtml(w.effort_id)}</strong>: ${escapeHtml(w.message)}
              <div class="mono-text">Auto-Risk: ${escapeHtml(w.generated_risk?.title || "")} (+${w.suggested_slip_penalty_days}d slip)</div>
            </div>
          `
          )
          .join("");
      } else {
        mmSec.classList.add("hidden");
        mmList.innerHTML = "";
      }

      // Pool Balances
      const poolBox = document.getElementById("boe-pool-balances");
      const balances = sim.pool_balances || [];
      poolBox.innerHTML = balances.length
        ? balances
            .map((pb) => {
              const hasViol = (pb.color_of_money_violations || []).length > 0 || pb.remaining_amount < 0;
              return `
                <div class="pool-row ${hasViol ? "violation" : ""}">
                  <div class="pool-row-top">
                    <span>${escapeHtml(pb.pool.name)}</span>
                    <span class="mono-text">${pb.remaining_amount} / ${pb.pool.capacity} ${escapeHtml(pb.pool.unit)}</span>
                  </div>
                  <div class="mono-text">
                    ${pb.eligible_interest_ids?.length ? `Earmarked Eligible (${pb.eligible_interest_ids.length} interests incl. descendants)` : "Unrestricted Color-of-Money"}
                  </div>
                  ${(pb.color_of_money_violations || []).map((v) => `<div class="mono-text" style="color:#fca5a5">${escapeHtml(v)}</div>`).join("")}
                </div>
              `;
            })
            .join("")
        : '<div class="mono-text">No managed resource pools configured.</div>';

      // Impacted Efforts
      const impList = document.getElementById("boe-impacted-list");
      const impIds = sim.impacted_effort_ids || [];
      const nodeMap = Object.fromEntries((sim.projected_tree?.nodes || []).map((n) => [n.effort.id, n]));
      impList.innerHTML = impIds.length
        ? impIds
            .map((eid) => {
              const n = nodeMap[eid];
              return `<div class="staged-item"><span><strong>${escapeHtml(n?.effort?.name || eid)}</strong></span><span class="mono-text">${escapeHtml(fmtForecast(n))}</span></div>`;
            })
            .join("")
        : '<div class="mono-text">Stage a mitigator, allocation, or slip shock to preview deltas.</div>';

      this.renderStaticLists();
    }
  }

  global.BillOfEffortsDock = BillOfEffortsDock;
})(window);
