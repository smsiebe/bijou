/* ==========================================================================
   Bijou v2 Global Neural Graph View
   Free-Floating Force-Directed & Draggable Neural Topology
   Renders Organizations, Efforts, and Interests together with all 6 Typed Edges,
   Hover Neighborhood Emphasis, Live Node Repositioning & Connect Ports
   ========================================================================== */

(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const STORAGE_KEY = "bijou_neural_positions_v1";

  const positionCache = new Map();
  const pinnedKeys = new Set();

  function loadPersistedPositions() {
    if (positionCache.size > 0) return;
    try {
      const raw = global.localStorage?.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      Object.entries(parsed || {}).forEach(([k, v]) => {
        if (v && Number.isFinite(v.x) && Number.isFinite(v.y)) {
          positionCache.set(k, { x: v.x, y: v.y });
          pinnedKeys.add(k);
        }
      });
    } catch (_) {
      // Ignore storage unavailable in restricted contexts
    }
  }

  function persistPositions() {
    try {
      const obj = {};
      pinnedKeys.forEach((k) => {
        const v = positionCache.get(k);
        if (v) obj[k] = { x: Math.round(v.x), y: Math.round(v.y) };
      });
      global.localStorage?.setItem(STORAGE_KEY, JSON.stringify(obj));
    } catch (_) {
      // Ignore storage errors
    }
  }

  function setSpawnPosition(kind, id, x, y) {
    const prefix = kind === "organization" ? "org" : kind;
    const key = `${prefix}:${id}`;
    positionCache.set(key, { x: Math.max(24, x - 96), y: Math.max(24, y - 36) });
    pinnedKeys.add(key);
    persistPositions();
  }

  function resetLayout() {
    positionCache.clear();
    pinnedKeys.clear();
    try {
      global.localStorage?.removeItem(STORAGE_KEY);
    } catch (_) {
      // Ignore
    }
  }

  function hashString(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i += 1) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  function computeForceLayout(items, edges, width, height) {
    const coords = new Map();
    const n = items.length;
    if (!n) return coords;

    const cx = width / 2;
    const cy = height / 2;

    // Seed positions deterministically by ontology band + golden angle
    items.forEach((item, idx) => {
      if (pinnedKeys.has(item.key) && positionCache.has(item.key)) {
        coords.set(item.key, { ...positionCache.get(item.key) });
        return;
      }
      if (positionCache.has(item.key)) {
        coords.set(item.key, { ...positionCache.get(item.key) });
        return;
      }
      const golden = idx * 2.399963229728653;
      const jitter = (hashString(item.key) % 44) - 22;
      let rx = Math.min(340, width * 0.33);
      let ry = Math.min(210, height * 0.33);
      let baseAngle = golden;
      if (item.kind === "organization") {
        rx = Math.min(360, width * 0.35);
        ry = Math.min(220, height * 0.34);
        baseAngle = -Math.PI * 0.75 + (idx * 0.85);
      } else if (item.kind === "interest") {
        rx = Math.min(360, width * 0.35);
        ry = Math.min(220, height * 0.34);
        baseAngle = Math.PI * 0.25 + (idx * 0.85);
      } else {
        rx = 160 + (idx % 3) * 55;
        ry = 115 + (idx % 2) * 50;
      }
      coords.set(item.key, {
        x: Math.max(28, Math.min(width - 230, cx + Math.cos(baseAngle) * rx + jitter - 95)),
        y: Math.max(36, Math.min(height - 110, cy + Math.sin(baseAngle) * ry + jitter - 38)),
      });
    });

    // Run lightweight Fruchterman-Reingold iterations on unpinned nodes
    const nodeW = 200;
    const nodeH = 88;
    const area = width * height;
    const kDist = Math.sqrt(area / Math.max(n, 4)) * 0.88;
    const iterations = 135;

    for (let iter = 0; iter < iterations; iter += 1) {
      const disp = new Map();
      items.forEach((it) => disp.set(it.key, { dx: 0, dy: 0 }));

      // Pairwise repulsion + overlap box separation
      for (let i = 0; i < n; i += 1) {
        const a = items[i];
        const pa = coords.get(a.key);
        for (let j = i + 1; j < n; j += 1) {
          const b = items[j];
          const pb = coords.get(b.key);
          let vx = pa.x - pb.x;
          let vy = pa.y - pb.y;
          const dist = Math.hypot(vx, vy) || 0.01;
          const rep = (kDist * kDist) / (dist * 1.1);
          const ux = vx / dist;
          const uy = vy / dist;

          // Strong soft box separation when cards overlap
          const overlapX = nodeW + 26 - Math.abs(vx);
          const overlapY = nodeH + 22 - Math.abs(vy);
          const boxPush = overlapX > 0 && overlapY > 0 ? Math.min(overlapX, overlapY) * 0.55 : 0;

          const force = Math.min(48, rep * 0.08 + boxPush);
          if (!pinnedKeys.has(a.key)) {
            disp.get(a.key).dx += ux * force;
            disp.get(a.key).dy += uy * force;
          }
          if (!pinnedKeys.has(b.key)) {
            disp.get(b.key).dx -= ux * force;
            disp.get(b.key).dy -= uy * force;
          }
        }
      }

      // Edge attraction
      edges.forEach((ed) => {
        const pa = coords.get(ed.a);
        const pb = coords.get(ed.b);
        if (!pa || !pb) return;
        const vx = pa.x - pb.x;
        const vy = pa.y - pb.y;
        const dist = Math.hypot(vx, vy) || 0.01;
        const ideal = ed.kind === "indirect" ? kDist * 1.35 : kDist * 0.95;
        const attr = ((dist - ideal) * 0.08) * (ed.kind === "indirect" ? 0.35 : 0.8);
        const ux = vx / dist;
        const uy = vy / dist;
        if (!pinnedKeys.has(ed.a)) {
          disp.get(ed.a).dx -= ux * attr;
          disp.get(ed.a).dy -= uy * attr;
        }
        if (!pinnedKeys.has(ed.b)) {
          disp.get(ed.b).dx += ux * attr;
          disp.get(ed.b).dy += uy * attr;
        }
      });

      // Gentle gravity toward center
      items.forEach((it) => {
        if (pinnedKeys.has(it.key)) return;
        const p = coords.get(it.key);
        const d = disp.get(it.key);
        d.dx += (cx - 98 - p.x) * 0.025;
        d.dy += (cy - 42 - p.y) * 0.025;

        const maxStep = Math.max(4, 28 * (1 - iter / iterations));
        const mag = Math.hypot(d.dx, d.dy) || 1;
        const clamp = Math.min(mag, maxStep);
        p.x = Math.max(28, Math.min(width - nodeW - 28, p.x + (d.dx / mag) * clamp));
        p.y = Math.max(42, Math.min(height - nodeH - 32, p.y + (d.dy / mag) * clamp));
      });
    }

    coords.forEach((pos, k) => positionCache.set(k, { ...pos }));
    return coords;
  }

  function renderGlobalNeuralGraph({
    triView,
    svgEl,
    domEl,
    worldEl,
    showStructural = true,
    showIndirect = true,
    impactedIds = [],
    zoom = 1.0,
    onSelectEntity,
  }) {
    loadPersistedPositions();
    const { escapeHtml, fmtUsd, fmtForecast } = global.BijouApi;
    svgEl.innerHTML = "";
    domEl.innerHTML = "";

    const tree = triView?.capability_tree;
    if (!tree) {
      domEl.innerHTML = '<div class="empty-state">Global Neural Graph data unavailable. Right-click to create nodes.</div>';
      return;
    }

    const orgs = tree.organizations || [];
    const effortNodes = tree.nodes || [];
    const interests = tree.interests || [];
    const indirectBenefits = triView.indirect_benefits || [];
    const impactedSet = new Set(impactedIds || []);

    const orgName = Object.fromEntries(orgs.map((o) => [o.id, o.name]));
    const effName = Object.fromEntries(effortNodes.map((n) => [n.effort.id, n.effort.name]));
    const intrName = Object.fromEntries(interests.map((i) => [i.id, i.name]));

    const items = [
      ...orgs.map((o) => ({ key: `org:${o.id}`, kind: "organization", id: o.id, label: o.name, data: o })),
      ...effortNodes.map((n) => ({ key: `effort:${n.effort.id}`, kind: "effort", id: n.effort.id, label: n.effort.name, data: n })),
      ...interests.map((i) => ({ key: `interest:${i.id}`, kind: "interest", id: i.id, label: i.name, data: i })),
    ];

    if (!items.length) {
      domEl.innerHTML = '<div class="empty-state">No entities in graph yet. Right-click canvas to create an Organization, Interest, or Effort.</div>';
      worldEl.style.width = "1120px";
      worldEl.style.height = "680px";
      return;
    }

    const linkPairs = [];
    const connectionIndex = new Map();

    function addLink(a, b, style) {
      if (!connectionIndex.has(a)) connectionIndex.set(a, new Set());
      if (!connectionIndex.has(b)) connectionIndex.set(b, new Set());
      connectionIndex.get(a).add(b);
      connectionIndex.get(b).add(a);
      linkPairs.push({ a, b, ...style });
    }

    (tree.org_effort_edges || []).forEach((e) =>
      addLink(`org:${e.org_id}`, `effort:${e.effort_id}`, {
        color: "#38bdf8",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : null,
        width: 2.0,
        opacity: 0.78,
        kind: "org_effort",
        edgeCat: "org_effort_edge",
        edgeId: e.id,
        label: `${orgName[e.org_id] || e.org_id} → ${effName[e.effort_id] || e.effort_id} (${e.resourcing_type}: ${e.allocation_amount} ${e.allocation_unit})`,
      })
    );

    (tree.effort_interest_edges || []).forEach((e) =>
      addLink(`effort:${e.effort_id}`, `interest:${e.interest_id}`, {
        color: "#10b981",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : null,
        width: 2.0,
        opacity: 0.78,
        kind: "eff_intr",
        edgeCat: "effort_interest_edge",
        edgeId: e.id,
        label: `${effName[e.effort_id] || e.effort_id} → ${intrName[e.interest_id] || e.interest_id} (${e.relation_type})`,
      })
    );

    (tree.effort_edges || tree.effort_effort_edges || []).forEach((e) =>
      addLink(`effort:${e.source_effort_id}`, `effort:${e.target_effort_id}`, {
        color: e.blocking_mode === "BLOCKING" ? "#f59e0b" : "#94a3b8",
        dash: e.blocking_mode === "NON_BLOCKING_INFORMS" ? "5,4" : null,
        width: e.blocking_mode === "BLOCKING" ? 2.1 : 1.5,
        opacity: 0.82,
        kind: "eff_eff",
        edgeCat: "effort_effort_edge",
        edgeId: e.id,
        label: `${effName[e.source_effort_id] || e.source_effort_id} → ${effName[e.target_effort_id] || e.target_effort_id} (${e.blocking_mode})`,
      })
    );

    (tree.org_interest_edges || []).forEach((e) =>
      addLink(`org:${e.org_id}`, `interest:${e.interest_id}`, {
        color: "#818cf8",
        dash: e.confidence === "UNCONFIRMED" ? "3,4" : "2,3",
        width: 1.5,
        opacity: 0.56,
        kind: "org_intr",
        edgeCat: "org_interest_edge",
        edgeId: e.id,
        label: `${orgName[e.org_id] || e.org_id} ↦ ${intrName[e.interest_id] || e.interest_id} (${e.stance})`,
      })
    );

    if (showStructural) {
      (tree.org_org_edges || []).forEach((e) =>
        addLink(`org:${e.source_org_id}`, `org:${e.target_org_id}`, {
          color: "#2dd4bf",
          dash: e.relation_type === "COLLABORATIVE_ADJACENT" ? "4,4" : null,
          width: 1.6,
          opacity: 0.68,
          kind: "org_org",
          edgeCat: "org_org_edge",
          edgeId: e.id,
          label: `${orgName[e.source_org_id] || e.source_org_id} → ${orgName[e.target_org_id] || e.target_org_id} (${e.relation_type})`,
        })
      );

      (tree.interest_interest_edges || []).forEach((e) =>
        addLink(`interest:${e.parent_interest_id}`, `interest:${e.child_interest_id}`, {
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
    }

    if (showIndirect) {
      indirectBenefits.forEach((b) =>
        addLink(`org:${b.beneficiary_org_id}`, `interest:${b.via_interest_id}`, {
          color: "#e879f9",
          dash: "5,5",
          width: 1.4,
          opacity: 0.42,
          kind: "indirect",
          edgeCat: null,
          edgeId: null,
          label: `Indirect benefit via ${intrName[b.via_interest_id] || b.via_interest_id}`,
        })
      );
    }

    // Dynamic canvas sizing sized comfortably for laptop/desktop viewports
    let worldW = Math.max(1140, 820 + items.length * 18);
    let worldH = Math.max(620, 440 + items.length * 12);
    const coords = computeForceLayout(items, linkPairs, worldW, worldH);

    coords.forEach((p) => {
      worldW = Math.max(worldW, p.x + 260);
      worldH = Math.max(worldH, p.y + 150);
    });

    worldEl.style.width = `${worldW}px`;
    worldEl.style.height = `${worldH}px`;
    svgEl.setAttribute("viewBox", `0 0 ${worldW} ${worldH}`);
    svgEl.style.width = `${worldW}px`;
    svgEl.style.height = `${worldH}px`;

    const nodeEls = new Map();
    const edgePaths = [];

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
      edgePaths.forEach(({ path, link }) => {
        const active = link.a === rootKey || link.b === rootKey;
        const baseW = Number(link.width || 1.8);
        path.setAttribute("stroke-opacity", active ? "1" : "0.08");
        path.setAttribute("stroke-width", active ? (baseW + 1.2).toFixed(1) : "1.1");
      });
    }

    function clearHighlight() {
      domEl.querySelectorAll("[data-node-key]").forEach((el) => {
        el.classList.remove("highlighted", "dimmed");
      });
      edgePaths.forEach(({ path, link }) => {
        path.setAttribute("stroke-opacity", String(link.opacity));
        path.setAttribute("stroke-width", String(link.width));
      });
    }

    function computeCurveD(aPos, bPos, aEl, bEl, idxOffset) {
      const aw = aEl?.offsetWidth || 196;
      const ah = aEl?.offsetHeight || 78;
      const bw = bEl?.offsetWidth || 196;
      const bh = bEl?.offsetHeight || 78;
      const ax = aPos.x + aw / 2;
      const ay = aPos.y + ah / 2;
      const bx = bPos.x + bw / 2;
      const by = bPos.y + bh / 2;
      const dx = bx - ax;
      const dy = by - ay;
      const dist = Math.hypot(dx, dy) || 1;
      const nx = -dy / dist;
      const ny = dx / dist;
      const curveBend = (idxOffset % 2 === 0 ? 1 : -1) * Math.min(48, 16 + (idxOffset * 10));
      const mx = (ax + bx) / 2 + nx * curveBend;
      const my = (ay + by) / 2 + ny * curveBend;
      return `M ${ax.toFixed(1)} ${ay.toFixed(1)} Q ${mx.toFixed(1)} ${my.toFixed(1)}, ${bx.toFixed(1)} ${by.toFixed(1)}`;
    }

    function redrawSvgPaths(onlyKey = null) {
      edgePaths.forEach(({ path, link, pairIndex }) => {
        if (onlyKey && link.a !== onlyKey && link.b !== onlyKey) return;
        const pa = coords.get(link.a);
        const pb = coords.get(link.b);
        if (!pa || !pb) return;
        path.setAttribute("d", computeCurveD(pa, pb, nodeEls.get(link.a), nodeEls.get(link.b), pairIndex));
      });
    }

    // Create node cards first
    items.forEach((item) => {
      const pos = coords.get(item.key);
      const el = document.createElement("div");
      el.className = `neural-node kind-${item.kind}`;
      el.dataset.nodeKey = item.key;
      el.dataset.entityKind = item.kind;
      el.dataset.entityId = item.id;
      el.dataset.entityLabel = item.label;
      el.style.left = `${pos.x}px`;
      el.style.top = `${pos.y}px`;

      if (item.kind === "organization") {
        const o = item.data;
        el.innerHTML = `
          <div class="card-top-row">
            <span class="state-pill">ORG · E${o.echelon_level}</span>
            <span class="mono-text">${o.is_managed ? "Managed" : "Modeled"}</span>
          </div>
          <div class="neural-node-title">${escapeHtml(o.name)}</div>
          <div class="neural-node-sub">${escapeHtml((o.tags || []).slice(0, 2).join(" · ") || "Stakeholder Org")}</div>
          <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="organization" data-port-id="${escapeHtml(o.id)}"></span>
        `;
      } else if (item.kind === "effort") {
        const n = item.data;
        const eff = n.effort;
        if (impactedSet.has(eff.id)) el.classList.add("impacted");
        el.classList.add(`state-${eff.state}`);
        el.innerHTML = `
          <div class="card-top-row">
            <span class="state-pill ${escapeHtml(eff.state)}">${escapeHtml(eff.state)}</span>
            <span class="mono-text">${n.is_spof ? '<span class="spof-sample">SPOF</span>' : fmtUsd(n.total_estimated_cost_usd)}</span>
          </div>
          <div class="neural-node-title">${escapeHtml(eff.name)}</div>
          <div class="neural-node-sub">${escapeHtml(fmtForecast(n))}</div>
          <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="effort" data-port-id="${escapeHtml(eff.id)}"></span>
        `;
      } else {
        const intr = item.data;
        el.innerHTML = `
          <div class="card-top-row">
            <span class="state-pill">INTEREST</span>
            <span class="mono-text">${escapeHtml(intr.interest_kind)}</span>
          </div>
          <div class="neural-node-title">${escapeHtml(intr.name)}</div>
          <div class="neural-node-sub">${escapeHtml((intr.description || "Strategic Interest").slice(0, 52))}</div>
          <span class="node-connect-port" title="Drag to another node to create relationship" data-port-kind="interest" data-port-id="${escapeHtml(intr.id)}"></span>
        `;
      }

      // Free-floating drag repositioning (left mouse button, excluding port handle)
      el.addEventListener("mousedown", (ev) => {
        if (ev.button !== 0 || ev.target.closest(".node-connect-port")) return;
        ev.stopPropagation();

        const startX = ev.clientX;
        const startY = ev.clientY;
        const startPos = { ...coords.get(item.key) };
        const scale = Number(zoom || 1) || 1;
        let moved = false;

        el.classList.add("is-dragging");

        const onMove = (mv) => {
          const dx = (mv.clientX - startX) / scale;
          const dy = (mv.clientY - startY) / scale;
          if (!moved && Math.hypot(dx, dy) < 5) return;
          moved = true;
          const nx = Math.max(16, startPos.x + dx);
          const ny = Math.max(24, startPos.y + dy);
          coords.set(item.key, { x: nx, y: ny });
          positionCache.set(item.key, { x: nx, y: ny });
          pinnedKeys.add(item.key);
          el.style.left = `${nx}px`;
          el.style.top = `${ny}px`;
          redrawSvgPaths(item.key);
        };

        const onUp = () => {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
          el.classList.remove("is-dragging");
          if (moved) {
            persistPositions();
            el.dataset.justDragged = "1";
            setTimeout(() => delete el.dataset.justDragged, 50);
          }
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });

      el.addEventListener("click", (ev) => {
        if (ev.target.closest(".node-connect-port") || el.dataset.justDragged === "1") return;
        ev.stopPropagation();
        if (onSelectEntity) onSelectEntity(item.kind, item.id);
      });

      el.addEventListener("mouseenter", () => highlightConnected(item.key));
      el.addEventListener("mouseleave", clearHighlight);

      domEl.appendChild(el);
      nodeEls.set(item.key, el);
    });

    // Draw SVG curves after nodes are in DOM so dimensions are exact
    const pairCounters = new Map();
    const defs = document.createElementNS(SVG_NS, "defs");
    defs.innerHTML = `
      <marker id="neural-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
        <path d="M 0 1 L 10 5 L 0 9 z" fill="rgba(148, 163, 184, 0.7)"></path>
      </marker>
    `;
    svgEl.appendChild(defs);

    linkPairs.forEach((link) => {
      const pairKey = [link.a, link.b].sort().join("|");
      const pairIndex = pairCounters.get(pairKey) || 0;
      pairCounters.set(pairKey, pairIndex + 1);

      const p = document.createElementNS(SVG_NS, "path");
      p.setAttribute("fill", "none");
      p.setAttribute("stroke", link.color);
      p.setAttribute("stroke-width", String(link.width));
      p.setAttribute("stroke-opacity", String(link.opacity));
      if (link.dash) p.setAttribute("stroke-dasharray", link.dash);
      p.dataset.endpoints = `${link.a}|${link.b}`;
      p.dataset.baseOpacity = String(link.opacity);
      p.dataset.baseWidth = String(link.width);
      if (link.edgeCat && link.edgeId) {
        p.dataset.edgeCat = link.edgeCat;
        p.dataset.edgeId = link.edgeId;
        p.dataset.edgeLabel = link.label;
        p.classList.add("interactive-edge");
      }
      const title = document.createElementNS(SVG_NS, "title");
      title.textContent = link.label || "";
      p.appendChild(title);

      svgEl.appendChild(p);
      edgePaths.push({ path: p, link, pairIndex });
    });

    requestAnimationFrame(() => redrawSvgPaths());
  }

  global.BijouViewNeural = {
    renderGlobalNeuralGraph,
    resetLayout,
    setSpawnPosition,
  };
})(window);

