/**
 * Bijou REST API Client wrapper.
 * Communicates strictly via relative /api/v1/* endpoints (Zero external CDNs or hardcoded hosts).
 */

const BijouAPI = {
  async get(endpoint, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.append(k, v);
      }
    });
    const res = await fetch(url.toString(), {
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async post(endpoint, data = {}, params = {}) {
    const url = new URL(endpoint, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.append(k, v);
      }
    });
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  async delete(endpoint) {
    const res = await fetch(endpoint, {
      method: "DELETE",
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  // High-level API calls
  getOrganizations() {
    return this.get("/api/v1/organizations");
  },

  getThings() {
    return this.get("/api/v1/things");
  },

  getConcerns() {
    return this.get("/api/v1/concerns");
  },

  getTechTree(stratificationMode = "TRL_TIERS", asOfDate = null, orgFilter = null) {
    return this.get("/api/v1/views/tech-tree", {
      stratification_mode: stratificationMode,
      as_of_date: asOfDate,
      org_filter: orgFilter
    });
  },

  simulateSlip(milestoneId, slipDays, simulateCancellation = false) {
    return this.post("/api/v1/analysis/simulate-slip", {
      milestone_id: milestoneId,
      slip_days: slipDays,
      simulate_cancellation: simulateCancellation
    });
  },

  getPerspectiveBriefing(subjectOrgId, perspectiveOrgId = null, includeDescendants = true, asOfDate = null) {
    return this.get(`/api/v1/views/perspectives/${subjectOrgId}`, {
      perspective_org_id: perspectiveOrgId,
      include_descendants: includeDescendants,
      as_of_date: asOfDate
    });
  },

  getThingFocalDashboard(thingId, asOfDate = null) {
    return this.get(`/api/v1/views/things/${thingId}/focal`, { as_of_date: asOfDate });
  },

  evaluateTradeoff(proposedThingIds) {
    return this.post("/api/v1/analysis/tradeoff", proposedThingIds);
  },

  exportManifest() {
    return this.get("/api/v1/manifest/export");
  },

  importManifest(manifestData, replaceAll = false) {
    return this.post("/api/v1/manifest/import", manifestData, { replace_all: replaceAll });
  }
};
