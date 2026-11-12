/* ==========================================================================
   Bijou v2 View B: Tri-Partite Architectural Flow
   Organizations & Pools  <-->  Efforts DAG  <-->  Interest Taxonomy DAG
   Illuminates Direct Resourcing, Dependencies & Indirect Benefit Paths
   with Graph-Native Connect Ports & Hover Neighborhood Emphasis
   ========================================================================== */

(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  function renderViewBTripartite({
    triView,
    svgEl,
    domEl,
    worldEl,
    showIndirect = true,
    showPartners = true,
    focusNodeKey = null,
    impactedIds = [],
    onSelectEntity,
  }) {
    const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
    svgEl.innerHTML = "";
    domEl.innerHTML = "";

    const tree = triView?.capability_tree;
    if (!tree) {
      domEl.innerHTML = '<div class="empty-state">Tri-Partite Flow data unavailable.</div>';
      return;
    }

    const impactedSet = new Set(impactedIds || []);

    let orgs = tree.organizations || [];
    let efforts = tree.nodes || [];
    let interests = tree.interests || [];
    const poolBalances = triView.pool_balances || [];
    const indirectBenefits = triView.indirect_benefits || [];
    const partnerships = triView.shared_interest_partnerships || [];

    if (focusNodeKey) {
      const fSet = new Set([focusNodeKey]);
      const addNb = (a, b) => {
        if (a === focusNodeKey) fSet.add(b);
        if (b === focusNodeKey) fSet.add(a);
      };
      (tree.org_effort_edges || []).forEach((e) => addNb(`org:${e.org_id}`, `effort:${e.effort_id}`));
      (tree.effort_interest_edges || []).forEach((e) => addNb(`effort:${e.effort_id}`, `interest:${e.interest_id}`));
      (tree.org_interest_edges || []).forEach((e) => addNb(`org:${e.org_id}`, `interest:${e.interest_id}`));
      (tree.effort_edges || tree.effort_effort_edges || []).forEach((e) => addNb(`effort:${e.source_effort_id}`, `effort:${e.target_effort_id}`));
      (tree.org_org_edges || []).forEach((e) => addNb(`org:${e.source_org_id}`, `org:${e.target_org_id}`));
      (tree.interest_interest_edges || []).forEach((e) => addNb(`interest:${e.parent_interest_id}`, `interest:${e.child_interest_id}`));
      if (showIndirect) {
        indirectBenefits.forEach((b) => addNb(`org:${b.beneficiary_org_id}`, `interest:${b.via_interest_id}`));
      }
      orgs = orgs.filter((o) => fSet.has(`org:${o.id}`));
      efforts = efforts.filter((n) => fSet.has(`effort:${n.effort.id}`));
      interests = interests.filter((i) => fSet.has(`interest:${i.id}`));
    }

    const orgName = Object.fromEntries(orgs.map((o) => [o.id, o.name]));
    const effName = Object.fromEntries(efforts.map((n) => [n.effort.id, n.effort.name]));
    const intrName = Object.fromEntries(interests.map((i) => [i.id, i.name]));

    const poolsByOrg = {};
    poolBalances.forEach((pb) => {
      const oid = pb.pool.org_id;
      if (!poolsByOrg[oid]) poolsByOrg[oid] = [];
      poolsByOrg[oid].push(pb);
    });

    const grid = document.createElement("div");
    grid.className = "tripartite-grid";

    // Column 1: Organizations & Resource Pools
    const colOrgs = document.createElement("div");
    colOrgs.className = "tripartite-col";
    colOrgs.innerHTML = `<div class="tripartite-col-header"><span>Organizations &amp; Pools</span><span>${orgs.length}</span></div>`;

    orgs.forEach((org) => {
      const opools = poolsByOrg[org.id] || [];
      const indCount = indirectBenefits.filter((b) => b.beneficiary_org_id === org.id).length;
      const el = document.createElement("div");
      el.className = `tri-node kind-organization${focusNodeKey === `org:${org.id}` ? " focus-root" : ""}`;
      el.dataset.nodeKey = `org:${org.id}`;
      el.dataset.entityKind = "organization";
      el.dataset.entityId = org.id;
      el.dataset.entityLabel = org.name;
      el.innerHTML = `
        <div class="card-top-row">
          <span class="state-pill">${org.is_managed ? "MANAGED" : "MODELED"}</span>
          <span class="mono-text">Echelon ${org.echelon_level}</span>
        </div>
        <div class="tri-node-title">${escapeHtml(org.name)}</div>
        <div class="tri-node-sub">${opools.length} pool(s) · ${indCount} indirect benefit(s)</div>
        ${opools.slice(0, 2).map((pb) => `
          <div class="chip-row">
            <span class="mini-chip">${escapeHtml(pb.pool.name)}: ${escapeHtml(String(pb.remaining_amount))} ${escapeHtml(pb.pool.unit)}</span>
          </div>
        `).join("")}
        <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="organization" data-port-id="${escapeHtml(org.id)}"></span>
      `;
      el.addEventListener("click", (ev) => {
        if (ev.target.closest(".node-connect-port")) return;
        if (onSelectEntity) onSelectEntity("organization", org.id);
      });
      el.addEventListener("mouseenter", () => highlightConnected(`org:${org.id}`));
      el.addEventListener("mouseleave", clearHighlight);
      colOrgs.appendChild(el);
    });

    if (showPartners && partnerships.length > 0) {
      const pbox = document.createElement("div");
      pbox.className = "partner-callout";
      pbox.innerHTML = `
        <div class="tri-node-title" style="color:#d8b4fe">Shared-Interest Partnership Candidates (${partnerships.length})</div>
        ${partnerships.slice(0, 4).map((p) => `
          <div class="tri-node-sub" style="margin-top:4px">
            <strong>${escapeHtml(orgName[p.org_a_id] || p.org_a_id)}</strong> + <strong>${escapeHtml(orgName[p.org_b_id] || p.org_b_id)}</strong>
            <br/>Shared: ${p.shared_interest_ids.map((id) => escapeHtml(intrName[id] || id)).join(", ")}
            (${p.has_existing_org_link ? "Linked" : "Untapped Candidate"})
          </div>
        `).join("")}
      `;
      colOrgs.appendChild(pbox);
    }

    // Column 2: Efforts DAG
    const colEfforts = document.createElement("div");
    colEfforts.className = "tripartite-col";
    colEfforts.innerHTML = `<div class="tripartite-col-header"><span>Capability Efforts</span><span>${efforts.length}</span></div>`;

    efforts
      .slice()
      .sort((a, b) => a.topological_depth - b.topological_depth)
      .forEach((node) => {
        const eff = node.effort;
        const el = document.createElement("div");
        el.className = `tri-node kind-effort${impactedSet.has(eff.id) ? " impacted" : ""}${focusNodeKey === `effort:${eff.id}` ? " focus-root" : ""}`;
        el.dataset.nodeKey = `effort:${eff.id}`;
        el.dataset.entityKind = "effort";
        el.dataset.entityId = eff.id;
        el.dataset.entityLabel = eff.name;
        el.innerHTML = `
          <div class="card-top-row">
            <span class="state-pill ${escapeHtml(eff.state)}">${escapeHtml(eff.state)}</span>
            <span class="mono-text">Tier ${node.topological_depth + 1} · ${fmtUsd(node.total_estimated_cost_usd)}</span>
          </div>
          <div class="tri-node-title">${escapeHtml(eff.name)}</div>
          <div class="tri-node-sub">${escapeHtml(fmtForecast(node))}</div>
          <div class="chip-row">
            ${(node.indirect_beneficiary_org_ids || []).length > 0 ? `<span class="mini-chip indirect">${node.indirect_beneficiary_org_ids.length} Indirect Beneficiaries</span>` : ""}
            ${node.active_risk_count > 0 ? `<span class="mini-chip risk">${node.active_risk_count} Risks</span>` : ""}
          </div>
          <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="effort" data-port-id="${escapeHtml(eff.id)}"></span>
        `;
        el.addEventListener("click", (ev) => {
          if (ev.target.closest(".node-connect-port")) return;
          if (onSelectEntity) onSelectEntity("effort", eff.id);
        });
        el.addEventListener("mouseenter", () => highlightConnected(`effort:${eff.id}`));
        el.addEventListener("mouseleave", clearHighlight);
        colEfforts.appendChild(el);
      });

    // Column 3: Interests & Taxonomy
    const colInterests = document.createElement("div");
    colInterests.className = "tripartite-col";
    colInterests.innerHTML = `<div class="tripartite-col-header"><span>Interests &amp; Taxonomy</span><span>${interests.length}</span></div>`;

    const childMap = {};
    (tree.interest_interest_edges || []).forEach((e) => {
      if (!childMap[e.child_interest_id]) childMap[e.child_interest_id] = [];
      childMap[e.child_interest_id].push(e.parent_interest_id);
    });

    interests.forEach((intr) => {
      const parents = (childMap[intr.id] || []).map((pid) => intrName[pid] || pid);
      const el = document.createElement("div");
      el.className = `tri-node kind-interest${focusNodeKey === `interest:${intr.id}` ? " focus-root" : ""}`;
      el.dataset.nodeKey = `interest:${intr.id}`;
      el.dataset.entityKind = "interest";
      el.dataset.entityId = intr.id;
      el.dataset.entityLabel = intr.name;
      el.innerHTML = `
        <div class="card-top-row">
          <span class="state-pill">${escapeHtml(intr.interest_kind)}</span>
          <span class="mono-text">${parents.length ? "Sub-Interest" : "Top Category"}</span>
        </div>
        <div class="tri-node-title">${escapeHtml(intr.name)}</div>
        <div class="tri-node-sub">${parents.length ? `Parent(s): ${escapeHtml(parents.join(", "))}` : escapeHtml(intr.description || "")}</div>
        <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="interest" data-port-id="${escapeHtml(intr.id)}"></span>
      `;
      el.addEventListener("click", (ev) => {
        if (ev.target.closest(".node-connect-port")) return;
        if (onSelectEntity) onSelectEntity("interest", intr.id);
      });
      el.addEventListener("mouseenter", () => highlightConnected(`interest:${intr.id}`));
      el.addEventListener("mouseleave", clearHighlight);
      colInterests.appendChild(el);
    });

    grid.appendChild(colOrgs);
    grid.appendChild(colEfforts);
    grid.appendChild(colInterests);
    domEl.appendChild(grid);

    const connectionIndex = new Map();
    const linkPairs = [];

    function addConnection(a, b, style) {
      if (!connectionIndex.has(a)) connectionIndex.set(a, new Set());
      if (!connectionIndex.has(b)) connectionIndex.set(b, new Set());
      connectionIndex.get(a).add(b);
      connectionIndex.get(b).add(a);
      linkPairs.push({ a, b, ...style });
    }

    (tree.org_effort_edges || []).forEach((e) =>
      addConnection(`org:${e.org_id}`, `effort:${e.effort_id}`, {
        color: "#38bdf8",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : null,
        width: 2.0,
        opacity: 0.78,
        kind: "direct",
        edgeCat: "org_effort_edge",
        edgeId: e.id,
        label: `${orgName[e.org_id] || e.org_id} → ${effName[e.effort_id] || e.effort_id} (${e.resourcing_type}: ${e.allocation_amount} ${e.allocation_unit})`,
      })
    );

    (tree.effort_interest_edges || []).forEach((e) =>
      addConnection(`effort:${e.effort_id}`, `interest:${e.interest_id}`, {
        color: "#10b981",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : null,
        width: 2.0,
        opacity: 0.78,
        kind: "align",
        edgeCat: "effort_interest_edge",
        edgeId: e.id,
        label: `${effName[e.effort_id] || e.effort_id} → ${intrName[e.interest_id] || e.interest_id} (${e.relation_type})`,
      })
    );

    (tree.org_interest_edges || []).forEach((e) =>
      addConnection(`org:${e.org_id}`, `interest:${e.interest_id}`, {
        color: "#818cf8",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : "2,3",
        width: 1.4,
        opacity: 0.45,
        kind: "stance",
        edgeCat: "org_interest_edge",
        edgeId: e.id,
        label: `${orgName[e.org_id] || e.org_id} ↦ ${intrName[e.interest_id] || e.interest_id} (${e.stance})`,
      })
    );

    if (showIndirect) {
      indirectBenefits.forEach((b) => {
        addConnection(`org:${b.beneficiary_org_id}`, `interest:${b.via_interest_id}`, {
          color: "#a855f7",
          dash: "5,5",
          width: 1.5,
          opacity: 0.48,
          kind: "indirect",
          edgeCat: null,
          edgeId: null,
          label: `Indirect benefit via ${intrName[b.via_interest_id] || b.via_interest_id}`,
        });
      });
    }

    (tree.effort_edges || tree.effort_effort_edges || []).forEach((e) =>
      addConnection(`effort:${e.source_effort_id}`, `effort:${e.target_effort_id}`, {
        color: e.blocking_mode === "BLOCKING" ? "#f59e0b" : "#94a3b8",
        dash: e.blocking_mode === "NON_BLOCKING_INFORMS" ? "4,4" : null,
        width: 1.6,
        opacity: 0.75,
        kind: "dep",
        edgeCat: "effort_effort_edge",
        edgeId: e.id,
        label: `${effName[e.source_effort_id] || e.source_effort_id} → ${effName[e.target_effort_id] || e.target_effort_id} (${e.blocking_mode})`,
      })
    );

    (tree.org_org_edges || []).forEach((e) =>
      addConnection(`org:${e.source_org_id}`, `org:${e.target_org_id}`, {
        color: "#2dd4bf",
        dash: e.relation_type === "COLLABORATIVE_ADJACENT" ? "4,3" : null,
        width: 1.6,
        opacity: 0.68,
        kind: "org_org",
        edgeCat: "org_org_edge",
        edgeId: e.id,
        label: `${orgName[e.source_org_id] || e.source_org_id} → ${orgName[e.target_org_id] || e.target_org_id} (${e.relation_type})`,
      })
    );

    (tree.interest_interest_edges || []).forEach((e) =>
      addConnection(`interest:${e.parent_interest_id}`, `interest:${e.child_interest_id}`, {
        color: "#c084fc",
        dash: null,
        width: 1.6,
        opacity: 0.68,
        kind: "intr_intr",
        edgeCat: "interest_interest_edge",
        edgeId: e.id,
        label: `${intrName[e.parent_interest_id] || e.parent_interest_id} ⊃ ${intrName[e.child_interest_id] || e.child_interest_id} (${e.relation_type})`,
      })
    );

    requestAnimationFrame(() => {
      const worldRect = worldEl.getBoundingClientRect();
      const liveScale = (worldEl.offsetWidth ? worldRect.width / worldEl.offsetWidth : 1) || 1;
      const boxMap = new Map();
      domEl.querySelectorAll("[data-node-key]").forEach((el) => {
        const r = el.getBoundingClientRect();
        boxMap.set(el.dataset.nodeKey, {
          left: (r.left - worldRect.left) / liveScale,
          right: (r.right - worldRect.left) / liveScale,
          top: (r.top - worldRect.top) / liveScale,
          bottom: (r.bottom - worldRect.top) / liveScale,
          cx: (r.left - worldRect.left + r.width / 2) / liveScale,
          cy: (r.top - worldRect.top + r.height / 2) / liveScale,
        });
      });

      const totalW = Math.max(1180, grid.scrollWidth + 60);
      const totalH = Math.max(660, grid.scrollHeight + 48);
      worldEl.style.width = `${totalW}px`;
      worldEl.style.height = `${totalH}px`;
      svgEl.setAttribute("viewBox", `0 0 ${totalW} ${totalH}`);
      svgEl.style.width = `${totalW}px`;
      svgEl.style.height = `${totalH}px`;
      svgEl.innerHTML = "";

      linkPairs.forEach((lnk) => {
        const ba = boxMap.get(lnk.a);
        const bb = boxMap.get(lnk.b);
        if (!ba || !bb) return;

        let d = "";
        if (lnk.kind === "dep") {
          const x1 = ba.right;
          const y1 = ba.cy;
          const x2 = bb.right;
          const y2 = bb.cy;
          const bulge = Math.max(x1, x2) + 34;
          d = `M ${x1} ${y1} C ${bulge} ${y1}, ${bulge} ${y2}, ${x2} ${y2}`;
        } else if (lnk.kind === "org_org") {
          const x1 = ba.left;
          const y1 = ba.cy;
          const x2 = bb.left;
          const y2 = bb.cy;
          const bulge = Math.min(x1, x2) - 26;
          d = `M ${x1} ${y1} C ${bulge} ${y1}, ${bulge} ${y2}, ${x2} ${y2}`;
        } else if (lnk.kind === "intr_intr") {
          const x1 = ba.right;
          const y1 = ba.cy;
          const x2 = bb.right;
          const y2 = bb.cy;
          const bulge = Math.max(x1, x2) + 28;
          d = `M ${x1} ${y1} C ${bulge} ${y1}, ${bulge} ${y2}, ${x2} ${y2}`;
        } else if (lnk.kind === "indirect" || lnk.kind === "stance") {
          const x1 = ba.right;
          const y1 = ba.cy - (lnk.kind === "indirect" ? 10 : 0);
          const x2 = bb.left;
          const y2 = bb.cy - (lnk.kind === "indirect" ? 10 : 0);
          const midX = (x1 + x2) / 2;
          const archOffset = lnk.kind === "indirect" ? -44 : 38;
          const ctrlY = (lnk.kind === "indirect" ? Math.min(y1, y2) : Math.max(y1, y2)) + archOffset;
          d = `M ${x1} ${y1} Q ${midX} ${ctrlY}, ${x2} ${y2}`;
        } else {
          const x1 = ba.right;
          const y1 = ba.cy;
          const x2 = bb.left;
          const y2 = bb.cy;
          const dx = Math.abs(x2 - x1) * 0.45;
          d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
        }

        const p = document.createElementNS(SVG_NS, "path");
        p.setAttribute("d", d);
        p.setAttribute("fill", "none");
        p.setAttribute("stroke", lnk.color);
        p.setAttribute("stroke-width", String(lnk.width));
        p.setAttribute("stroke-opacity", String(lnk.opacity));
        if (lnk.dash) p.setAttribute("stroke-dasharray", lnk.dash);
        p.dataset.endpoints = `${lnk.a}|${lnk.b}`;
        p.dataset.baseOpacity = String(lnk.opacity);
        p.dataset.baseWidth = String(lnk.width);
        if (lnk.edgeCat && lnk.edgeId) {
          p.dataset.edgeCat = lnk.edgeCat;
          p.dataset.edgeId = lnk.edgeId;
          p.dataset.edgeLabel = lnk.label;
          p.classList.add("interactive-edge");
        }
        const title = document.createElementNS(SVG_NS, "title");
        title.textContent = lnk.label || "";
        p.appendChild(title);
        svgEl.appendChild(p);
      });
    });

    function highlightConnected(rootKey) {
      if (document.body.classList.contains("is-connecting")) return;
      const neighbors = connectionIndex.get(rootKey) || new Set();
      domEl.querySelectorAll("[data-node-key]").forEach((el) => {
        const k = el.dataset.nodeKey;
        if (k === rootKey || neighbors.has(k)) {
          el.classList.add("highlighted");
          el.classList.remove("dimmed");
        } else {
          el.classList.remove("highlighted");
          el.classList.add("dimmed");
        }
      });
      svgEl.querySelectorAll("path[data-endpoints]").forEach((p) => {
        const [a, b] = p.dataset.endpoints.split("|");
        const active = a === rootKey || b === rootKey;
        const baseW = parseFloat(p.dataset.baseWidth || "1.8");
        p.setAttribute("stroke-opacity", active ? "1" : "0.08");
        p.setAttribute("stroke-width", active ? (baseW + 1.0).toFixed(1) : "1.1");
      });
    }

    function clearHighlight() {
      domEl.querySelectorAll("[data-node-key]").forEach((el) => {
        el.classList.remove("highlighted", "dimmed");
      });
      svgEl.querySelectorAll("path[data-endpoints]").forEach((p) => {
        p.setAttribute("stroke-opacity", p.dataset.baseOpacity || "0.75");
        p.setAttribute("stroke-width", p.dataset.baseWidth || "1.8");
      });
    }
  }

  global.BijouViewB = { renderViewBTripartite };
})(window);
