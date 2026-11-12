/* ==========================================================================
   Bijou v2 View A: Stateful Capability Progression Tree (DAG)
   Renders COMPLETED -> IN_WORK -> Future/Discovery Effort Layers + Overlays
   with View-B-parity Hover Neighborhood Emphasis & Graph-Native Connect Ports
   ========================================================================== */

(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  function buildColorMap(items) {
    const palette = ["#38bdf8", "#a855f7", "#10b981", "#f59e0b", "#f43f5e", "#6366f1", "#14b8a6"];
    const map = {};
    (items || []).forEach((item, idx) => {
      map[item.id] = palette[idx % palette.length];
    });
    return map;
  }

  function renderViewADag({
    treeView,
    svgEl,
    domEl,
    worldEl,
    clusterBy = "state",
    impactedIds = [],
    onSelectEffort,
  }) {
    const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
    svgEl.innerHTML = "";
    domEl.innerHTML = "";

    const nodes = treeView?.nodes || [];
    const edges = treeView?.effort_edges || [];
    if (!nodes.length) {
      domEl.innerHTML = '<div class="empty-state">No Efforts match the current filter criteria. Right-click canvas to create an Effort.</div>';
      worldEl.style.width = "100%";
      worldEl.style.height = "400px";
      return;
    }

    const orgById = Object.fromEntries((treeView.organizations || []).map((o) => [o.id, o]));
    const intrById = Object.fromEntries((treeView.interests || []).map((i) => [i.id, i]));
    const effNameById = Object.fromEntries(nodes.map((n) => [n.effort.id, n.effort.name]));
    const orgColors = buildColorMap(treeView.organizations || []);
    const intrColors = buildColorMap(treeView.interests || []);
    const impactedSet = new Set(impactedIds || []);

    const connectionIndex = new Map();
    edges.forEach((edge) => {
      const a = `effort:${edge.source_effort_id}`;
      const b = `effort:${edge.target_effort_id}`;
      if (!connectionIndex.has(a)) connectionIndex.set(a, new Set());
      if (!connectionIndex.has(b)) connectionIndex.set(b, new Set());
      connectionIndex.get(a).add(b);
      connectionIndex.get(b).add(a);
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
        const baseW = parseFloat(p.dataset.baseWidth || "2");
        p.setAttribute("stroke-opacity", active ? "1" : "0.12");
        p.setAttribute("stroke-width", active ? (baseW + 1.2).toFixed(1) : "1.2");
      });
    }

    function clearHighlight() {
      domEl.querySelectorAll("[data-node-key]").forEach((el) => {
        el.classList.remove("highlighted", "dimmed");
      });
      svgEl.querySelectorAll("path[data-endpoints]").forEach((p) => {
        p.setAttribute("stroke-opacity", p.dataset.baseOpacity || "0.9");
        p.setAttribute("stroke-width", p.dataset.baseWidth || "2");
      });
    }

    // Group by topological depth layers, ordered Completed -> In Work -> Future inside columns
    const stateOrder = {
      COMPLETED: 0,
      IN_WORK: 1,
      BACKLOGGED: 2,
      PLANNED: 3,
      DISCOVERY_PENDING: 4,
      CANCELLED: 5,
    };

    const byDepth = new Map();
    nodes.forEach((n) => {
      const d = Number(n.topological_depth || 0);
      if (!byDepth.has(d)) byDepth.set(d, []);
      byDepth.get(d).push(n);
    });

    const depths = Array.from(byDepth.keys()).sort((a, b) => a - b);
    const colWidth = 310;
    const cardW = 252;
    const cardH = 162;
    const rowGap = 28;
    const startX = 24;
    const startY = 38;

    const coords = new Map();
    let maxRows = 1;

    depths.forEach((d, colIdx) => {
      const colNodes = byDepth.get(d).slice().sort((a, b) => {
        const sa = stateOrder[a.effort.state] ?? 9;
        const sb = stateOrder[b.effort.state] ?? 9;
        if (sa !== sb) return sa - sb;
        return a.effort.name.localeCompare(b.effort.name);
      });
      maxRows = Math.max(maxRows, colNodes.length);

      const header = document.createElement("div");
      header.className = "mono-text";
      header.style.position = "absolute";
      header.style.left = `${startX + colIdx * colWidth}px`;
      header.style.top = "8px";
      header.style.width = `${cardW}px`;
      header.textContent = `TIER ${d + 1} · DEPTH ${d}`;
      domEl.appendChild(header);

      colNodes.forEach((node, rowIdx) => {
        const x = startX + colIdx * colWidth;
        const y = startY + rowIdx * (cardH + rowGap);
        coords.set(node.effort.id, { x, y, w: cardW, h: cardH });

        const eff = node.effort;
        const card = document.createElement("div");
        card.className = `effort-card state-${escapeHtml(eff.state)}${impactedSet.has(eff.id) ? " impacted" : ""}`;
        card.dataset.effortId = eff.id;
        card.dataset.nodeKey = `effort:${eff.id}`;
        card.dataset.entityKind = "effort";
        card.dataset.entityId = eff.id;
        card.dataset.entityLabel = eff.name;
        card.style.left = `${x}px`;
        card.style.top = `${y}px`;
        card.style.minHeight = `${cardH}px`;

        if (clusterBy === "org" && node.primary_org_id && orgColors[node.primary_org_id]) {
          card.style.borderLeftColor = orgColors[node.primary_org_id];
        } else if (clusterBy === "interest" && (node.aligned_interest_ids || []).length > 0) {
          const i0 = node.aligned_interest_ids[0];
          if (intrColors[i0]) card.style.borderLeftColor = intrColors[i0];
        }

        const primaryOrg = node.primary_org_id ? orgById[node.primary_org_id]?.name : "Unfunded / No Direct Org";
        const interestChips = (node.aligned_interest_ids || [])
          .slice(0, 2)
          .map((id) => `<span class="mini-chip">${escapeHtml(intrById[id]?.name || id)}</span>`)
          .join("");

        let forecastClass = "";
        if (node.horizon_status === "OPEN_ENDED_ACTIVE") forecastClass = "open-ended";
        else if (node.horizon_status === "RELATIVE_TO_DEPENDENCY") forecastClass = "relative";
        else if (node.horizon_status === "UNSCHEDULED_PLAN") forecastClass = "unscheduled";

        const covPct = Math.round((node.resourcing_coverage_ratio || 0) * 100);
        const indirectCnt = (node.indirect_beneficiary_org_ids || []).length;

        card.innerHTML = `
          <div class="card-top-row">
            <span class="state-pill ${escapeHtml(eff.state)}">${escapeHtml(eff.state)}</span>
            <div class="chip-row" style="margin-top:0">
              ${node.is_spof ? '<span class="spof-sample">SPOF</span>' : ""}
              ${node.active_risk_count > 0 ? `<span class="mini-chip risk">${node.active_risk_count} Risk</span>` : ""}
              ${node.unexercised_mitigator_count > 0 ? `<span class="mini-chip mit">+${node.unexercised_mitigator_count} Mit</span>` : ""}
            </div>
          </div>
          <div class="effort-card-title">${escapeHtml(eff.name)}</div>
          <div class="forecast-tag ${forecastClass}">${escapeHtml(fmtForecast(node))}</div>
          <div class="coverage-bar-track" title="Requirements funding coverage: ${covPct}%">
            <div class="coverage-bar-fill" style="width:${covPct}%"></div>
          </div>
          <div class="chip-row">
            ${interestChips}
            ${indirectCnt > 0 ? `<span class="mini-chip indirect">+${indirectCnt} Indirect Org</span>` : ""}
          </div>
          <div class="card-meta-row">
            <span title="Primary Resourcing Org">${escapeHtml(primaryOrg)}</span>
            <span>${fmtUsd(node.total_estimated_cost_usd)} · ${covPct}%</span>
          </div>
          <span class="node-connect-port" title="Drag to link to another Effort" data-port-kind="effort" data-port-id="${escapeHtml(eff.id)}"></span>
        `;

        card.addEventListener("click", (ev) => {
          if (ev.target.closest(".node-connect-port")) return;
          ev.stopPropagation();
          if (onSelectEffort) onSelectEffort(eff.id);
        });
        card.addEventListener("mouseenter", () => highlightConnected(`effort:${eff.id}`));
        card.addEventListener("mouseleave", clearHighlight);
        domEl.appendChild(card);
      });
    });

    const totalW = Math.max(1050, startX + depths.length * colWidth + 60);
    const totalH = Math.max(600, startY + maxRows * (cardH + rowGap) + 60);
    worldEl.style.width = `${totalW}px`;
    worldEl.style.height = `${totalH}px`;
    svgEl.setAttribute("viewBox", `0 0 ${totalW} ${totalH}`);
    svgEl.style.width = `${totalW}px`;
    svgEl.style.height = `${totalH}px`;

    const defs = document.createElementNS(SVG_NS, "defs");
    defs.innerHTML = `
      <marker id="arrow-blocking" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8"></path>
      </marker>
      <marker id="arrow-informs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="#a855f7"></path>
      </marker>
    `;
    svgEl.appendChild(defs);

    edges.forEach((edge) => {
      const src = coords.get(edge.source_effort_id);
      const dst = coords.get(edge.target_effort_id);
      if (!src || !dst) return;

      const x1 = src.x + src.w;
      const y1 = src.y + src.h / 2;
      const x2 = dst.x;
      const y2 = dst.y + dst.h / 2;
      const dx = Math.max(40, Math.abs(x2 - x1) * 0.45);

      const path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
      path.setAttribute("fill", "none");

      const isBlocking = edge.blocking_mode === "BLOCKING";
      const baseWidth = isBlocking ? (1.6 + edge.dependency_degree).toFixed(1) : "1.6";
      let baseOpacity = "0.9";

      path.setAttribute("stroke", isBlocking ? "#38bdf8" : "#a855f7");
      path.setAttribute("stroke-width", baseWidth);
      path.setAttribute("marker-end", isBlocking ? "url(#arrow-blocking)" : "url(#arrow-informs)");

      if (!isBlocking) {
        path.setAttribute("stroke-dasharray", "6,4");
      } else if (edge.confidence === "ASSESSED") {
        path.setAttribute("stroke-dasharray", "10,3");
        baseOpacity = "0.85";
      } else if (edge.confidence === "UNCONFIRMED") {
        path.setAttribute("stroke-dasharray", "3,4");
        baseOpacity = "0.65";
      }

      path.setAttribute("stroke-opacity", baseOpacity);
      path.dataset.endpoints = `effort:${edge.source_effort_id}|effort:${edge.target_effort_id}`;
      path.dataset.baseOpacity = baseOpacity;
      path.dataset.baseWidth = baseWidth;
      path.dataset.edgeCat = "effort_effort_edge";
      path.dataset.edgeId = edge.id;
      path.dataset.edgeLabel = `${effNameById[edge.source_effort_id] || edge.source_effort_id} → ${effNameById[edge.target_effort_id] || edge.target_effort_id} (${edge.blocking_mode})`;
      path.classList.add("interactive-edge");

      const title = document.createElementNS(SVG_NS, "title");
      title.textContent = `${path.dataset.edgeLabel} · ${edge.confidence} · Click or right-click to inspect/delete`;
      path.appendChild(title);

      svgEl.appendChild(path);
    });
  }

  global.BijouViewA = { renderViewADag };
})(window);
