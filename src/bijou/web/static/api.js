/* ==========================================================================
   Bijou v2 API Client & Shared Formatting Helpers
   Pure Vanilla JS | Relative Same-Origin Requests | Perspective Header Seam
   ========================================================================== */

(function (global) {
  "use strict";

  const perspectiveState = {
    mode: "GLOBAL_ANALYST",
    activeOrgId: null,
  };

  let customTransport = null;

  function setPerspective(mode, activeOrgId) {
    perspectiveState.mode = mode || "GLOBAL_ANALYST";
    perspectiveState.activeOrgId = activeOrgId || null;
  }

  function getPerspective() {
    return { ...perspectiveState };
  }

  function setTransport(transportFn) {
    customTransport = typeof transportFn === "function" ? transportFn : null;
  }

  async function waitForPyWebViewApi(timeoutMs = 2000) {
    if (global.pywebview?.api?.dispatch) return global.pywebview.api;
    if (!global.__BIJOU_DESKTOP_MODE__) return null;
    return await new Promise((resolve) => {
      const started = Date.now();
      const onReady = () => {
        window.removeEventListener("pywebviewready", onReady);
        resolve(global.pywebview?.api?.dispatch ? global.pywebview.api : null);
      };
      window.addEventListener("pywebviewready", onReady);
      const poll = () => {
        if (global.pywebview?.api?.dispatch) {
          window.removeEventListener("pywebviewready", onReady);
          resolve(global.pywebview.api);
          return;
        }
        if (Date.now() - started >= timeoutMs) {
          window.removeEventListener("pywebviewready", onReady);
          resolve(null);
          return;
        }
        setTimeout(poll, 25);
      };
      setTimeout(poll, 25);
    });
  }

  async function invokeBridge(method, url, headers, body) {
    if (customTransport) {
      return await customTransport(method, url, headers, body ?? null);
    }
    if (typeof global.__BIJOU_BRIDGE__ === "function") {
      return await global.__BIJOU_BRIDGE__(method, url, headers, body ?? null);
    }
    const pywebviewApi = await waitForPyWebViewApi();
    if (pywebviewApi?.dispatch) {
      return await pywebviewApi.dispatch(method, url, headers, body ?? null);
    }
    return null;
  }

  async function request(method, path, body, queryParams) {
    let url = path;
    if (queryParams) {
      const sp = new URLSearchParams();
      Object.entries(queryParams).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          sp.set(k, String(v));
        }
      });
      const qs = sp.toString();
      if (qs) url += (url.includes("?") ? "&" : "?") + qs;
    }

    const headers = {
      Accept: "application/json",
      "X-Bijou-Access-Mode": perspectiveState.mode,
    };
    if (perspectiveState.activeOrgId) {
      headers["X-Bijou-Active-Org"] = perspectiveState.activeOrgId;
    }

    const bridged = await invokeBridge(method, url, headers, body);
    if (bridged && typeof bridged === "object" && "status" in bridged) {
      const data = bridged.data ?? null;
      if (!bridged.ok) {
        let detail = `HTTP ${bridged.status}`;
        if (data && data.detail !== undefined) {
          detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
        const err = new Error(detail);
        err.status = bridged.status;
        err.payload = data;
        throw err;
      }
      return data;
    }

    const opts = { method, headers };
    if (body !== undefined && body !== null) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }

    const resp = await fetch(url, opts);
    const text = await resp.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (_) {
        data = { detail: text };
      }
    }

    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      if (data && data.detail !== undefined) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
      const err = new Error(detail);
      err.status = resp.status;
      err.payload = data;
      throw err;
    }

    return data;
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function fmtUsd(amount) {
    const num = Number(amount || 0);
    if (Math.abs(num) >= 1_000_000) {
      return `$${(num / 1_000_000).toFixed(2)}M`;
    }
    if (Math.abs(num) >= 1_000) {
      return `$${(num / 1_000).toFixed(1)}k`;
    }
    return `$${num.toFixed(0)}`;
  }

  function fmtForecast(node) {
    if (!node) return "Unknown";
    const status = node.horizon_status;
    if (status === "COMPLETED_HISTORICAL") {
      return node.forecast_end ? `Completed ${node.forecast_end}` : "Completed";
    }
    if (status === "OPEN_ENDED_ACTIVE") {
      return node.forecast_start ? `Active since ${node.forecast_start} (Open-Ended)` : "Open-Ended Active";
    }
    if (status === "RELATIVE_TO_DEPENDENCY") {
      const deps = (node.blocked_by_effort_ids || []).length;
      const offset = node.relative_offset_days !== null && node.relative_offset_days !== undefined
        ? `+${node.relative_offset_days}d`
        : "TBD duration";
      return `After ${deps} blocker(s) · ${offset}`;
    }
    if (status === "UNSCHEDULED_PLAN") {
      return node.effort?.estimated_duration_days
        ? `Unscheduled · ~${node.effort.estimated_duration_days}d`
        : "Unscheduled / Discovery Pending";
    }
    if (node.forecast_start && node.forecast_end) {
      return `${node.forecast_start} → ${node.forecast_end}`;
    }
    return node.forecast_end || node.forecast_start || "Scheduled";
  }

  const BijouApi = {
    setPerspective,
    getPerspective,
    setTransport,
    escapeHtml,
    fmtUsd,
    fmtForecast,

    health: () => request("GET", "/api/v1/health"),
    getPerspectiveState: () => request("GET", "/api/v1/perspective"),

    // Primary Graph Projections & Simulation
    getCapabilityTree: (params) => request("GET", "/api/v1/views/capability-tree", null, params),
    getTripartiteFlow: (params) => request("GET", "/api/v1/views/tripartite-flow", null, params),
    simulateBillOfEfforts: (payload, params) => request("POST", "/api/v1/simulation/bill-of-efforts", payload, params),
    commitBillOfEfforts: (payload, params) => request("POST", "/api/v1/simulation/bill-of-efforts/commit", payload, params),

    // Focal Dashboards & Briefing
    getEffortFocal: (id, params) => request("GET", `/api/v1/views/efforts/${encodeURIComponent(id)}/focal`, null, params),
    getOrgFocal: (id, params) => request("GET", `/api/v1/views/organizations/${encodeURIComponent(id)}/focal`, null, params),
    getInterestFocal: (id, params) => request("GET", `/api/v1/views/interests/${encodeURIComponent(id)}/focal`, null, params),
    getBriefing: (params) => request("GET", "/api/v1/views/briefing", null, params),
    getEffortBriefing: (params) => request("GET", "/api/v1/views/briefing/effort", null, params),

    // Entities CRUD
    listOrganizations: () => request("GET", "/api/v1/organizations"),
    upsertOrganization: (org) => request("POST", "/api/v1/organizations", org),
    deleteOrganization: (id) => request("DELETE", `/api/v1/organizations/${encodeURIComponent(id)}`),

    listResourcePools: (orgId) => request("GET", "/api/v1/resource-pools", null, orgId ? { org_id: orgId } : null),
    upsertResourcePool: (pool) => request("POST", "/api/v1/resource-pools", pool),
    deleteResourcePool: (id) => request("DELETE", `/api/v1/resource-pools/${encodeURIComponent(id)}`),

    listInterests: () => request("GET", "/api/v1/interests"),
    upsertInterest: (interest) => request("POST", "/api/v1/interests", interest),
    deleteInterest: (id) => request("DELETE", `/api/v1/interests/${encodeURIComponent(id)}`),

    listEfforts: () => request("GET", "/api/v1/efforts"),
    upsertEffort: (effort) => request("POST", "/api/v1/efforts", effort),
    deleteEffort: (id) => request("DELETE", `/api/v1/efforts/${encodeURIComponent(id)}`),

    // 6 Typed Edges
    upsertOrgOrgEdge: (edge) => request("POST", "/api/v1/edges/org-org", edge),
    upsertOrgInterestEdge: (edge) => request("POST", "/api/v1/edges/org-interest", edge),
    upsertInterestInterestEdge: (edge) => request("POST", "/api/v1/edges/interest-interest", edge),
    upsertOrgEffortEdge: (edge, slipPenaltyDays) =>
      request("POST", "/api/v1/edges/org-effort", edge, slipPenaltyDays !== undefined && slipPenaltyDays !== null ? { human_slip_penalty_days: slipPenaltyDays } : null),
    upsertEffortInterestEdge: (edge) => request("POST", "/api/v1/edges/effort-interest", edge),
    upsertEffortEffortEdge: (edge) => request("POST", "/api/v1/edges/effort-effort", edge),
    deleteEdge: (category, id) => request("DELETE", `/api/v1/edges/${encodeURIComponent(category)}/${encodeURIComponent(id)}`),

    // Diagnostics & Manifest
    validateManifest: (manifest) => request("POST", "/api/v1/manifest/validate", manifest || null),
    exportManifest: () => request("GET", "/api/v1/manifest/export"),
    importManifest: (manifest, replaceAll) =>
      request("POST", "/api/v1/manifest/import", manifest, { replace_all: Boolean(replaceAll) }),
    listDecisions: (effortId) => request("GET", "/api/v1/decisions", null, effortId ? { target_effort_id: effortId } : null),
  };

  global.BijouApi = BijouApi;
})(window);
