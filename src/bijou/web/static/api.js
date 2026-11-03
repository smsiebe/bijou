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

  simulateSlip(milestoneId, slipDays, simulateCancellation = false, simulatedSlips = null, cancelledMilestoneIds = null) {
    const slips = simulatedSlips || (milestoneId ? { [milestoneId]: slipDays } : {});
    const cancellations = cancelledMilestoneIds || (simulateCancellation && milestoneId ? [milestoneId] : []);
    return this.post("/api/v1/analysis/simulate-slip", {
      simulated_slips: slips,
      cancelled_milestone_ids: cancellations,
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
  },

  getParetoFrontier(budgetCeiling = 100000000.0, asOfDate = null) {
    return this.get("/api/v1/analysis/pareto-frontier", {
      budget_ceiling: budgetCeiling,
      as_of_date: asOfDate
    });
  },

  validateManifest(manifestData) {
    return this.post("/api/v1/manifest/validate", manifestData);
  },

  getDecisionLogs(targetMilestoneId = null) {
    return this.get("/api/v1/decision-logs", {
      target_milestone_id: targetMilestoneId
    });
  },

  createDecisionLog(entry) {
    return this.post("/api/v1/decision-logs", entry);
  },

  getTools() {
    return this.get("/api/v1/tools");
  },

  getClusteredSpheres(asOfDate = null, orgFilter = null) {
    return this.get("/api/v1/views/clustered-spheres", {
      as_of_date: asOfDate,
      org_filter: orgFilter
    });
  },

  getEdges() {
    return this.get("/api/v1/edges");
  },

  createThing(thingData) {
    return this.post("/api/v1/things", thingData);
  },

  deleteThing(thingId) {
    return this.delete(`/api/v1/things/${thingId}`);
  },

  async retireThing(thingId) {
    const existing = await this.get(`/api/v1/things/${thingId}`);
    existing.lifecycle = "RETIRED";
    return this.post("/api/v1/things", existing);
  },

  createConcern(concernData) {
    return this.post("/api/v1/concerns", concernData);
  },

  deleteConcern(concernId) {
    return this.delete(`/api/v1/concerns/${concernId}`);
  },

  createEdge(edgeData) {
    return this.post("/api/v1/edges", edgeData);
  },

  deleteEdge(edgeId) {
    return this.delete(`/api/v1/edges/${edgeId}`);
  },

  createOrganization(orgData) {
    return this.post("/api/v1/organizations", orgData);
  },

  deleteOrganization(orgId) {
    return this.delete(`/api/v1/organizations/${orgId}`);
  }
};

window.BijouAPI = BijouAPI;
