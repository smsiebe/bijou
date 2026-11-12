/* ==========================================================================
   Bijou v2 Graph-Native Editing Engine
   Provides:
   - Right-click Contextual Canvas/Node/Edge Menu
   - Drag-to-Connect Rubber-Band SVG Interaction + Click-to-Connect Banner
   - Contextual Edge Creation Popup across all 6 Typed Relationship Families
   - Quick Node Create / Edit Modal spawning directly onto Canvas Coordinates
   ========================================================================== */

(function (global) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";

  class GraphEditor {
    constructor(opts) {
      this.notify = opts.notify;
      this.getSnapshot = opts.getSnapshot; // () => { treeView, triView, zoom, canvasMode }
      this.onGraphMutated = opts.onGraphMutated;
      this.onInspectEntity = opts.onInspectEntity;
      this.onFocusNode = opts.onFocusNode;
      this.onResetGraph = opts.onResetGraph;
      this.isFiltered = opts.isFiltered;
      this.onStageSlip = opts.onStageSlip;
      this.onOpenCart = opts.onOpenCart;
      this.onOpenStudio = opts.onOpenStudio;

      this.viewportEl = document.getElementById("canvas-viewport");
      this.worldEl = document.getElementById("canvas-world");
      this.dragSvgEl = document.getElementById("canvas-drag-svg");

      this.connectPickSource = null;
      this.isDraggingConnection = false;
      this.pendingSpawn = null;

      this.ensureUiContainers();
      this.bindEvents();
    }

    isConnecting() {
      return this.isDraggingConnection || Boolean(this.connectPickSource);
    }

    ensureUiContainers() {
      if (!document.getElementById("graph-context-menu")) {
        const menu = document.createElement("div");
        menu.id = "graph-context-menu";
        menu.className = "graph-context-menu hidden";
        menu.setAttribute("role", "menu");
        document.body.appendChild(menu);
      }
      this.menuEl = document.getElementById("graph-context-menu");

      if (!document.getElementById("connect-mode-banner")) {
        const banner = document.createElement("div");
        banner.id = "connect-mode-banner";
        banner.className = "connect-mode-banner hidden";
        document.body.appendChild(banner);
      }
      this.bannerEl = document.getElementById("connect-mode-banner");

      if (!document.getElementById("graph-node-modal-backdrop")) {
        const wrap = document.createElement("div");
        wrap.id = "graph-node-modal-backdrop";
        wrap.className = "graph-modal-backdrop hidden";
        wrap.innerHTML = `
          <div class="graph-modal" id="graph-node-modal" role="dialog" aria-labelledby="node-modal-title">
            <div class="graph-modal-header">
              <div>
                <div class="puck-kind-pill" id="node-modal-pill">GRAPH NODE</div>
                <h3 id="node-modal-title">Create Entity</h3>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" id="btn-close-node-modal">×</button>
            </div>
            <form id="graph-node-form" class="studio-form graph-modal-body">
              <div class="form-row-2">
                <label>What are you adding?
                  <select id="gm-node-kind">
                    <option value="effort">Work Effort / Project</option>
                    <option value="organization">Organization / Stakeholder</option>
                    <option value="interest">Mission Goal / Topic</option>
                  </select>
                </label>
                <label>Short Reference ID
                  <input type="text" id="gm-node-id" required placeholder="eff-new-item" />
                </label>
              </div>
              <label>Title / Name
                <input type="text" id="gm-node-name" required placeholder="Short clear title" />
              </label>
              <div id="gm-node-dynamic-fields" class="studio-form"></div>
              <label>Description / Scope
                <textarea id="gm-node-desc" placeholder="Mission scope, capability deliverable, or priority rationale"></textarea>
              </label>
              <div id="gm-node-error" class="hint-banner warn hidden"></div>
              <div class="graph-modal-footer">
                <button type="button" class="btn btn-secondary btn-sm hidden" id="gm-node-studio-btn">Open Full Builder in Studio</button>
                <div style="display:flex;gap:8px;margin-left:auto">
                  <button type="button" class="btn btn-ghost btn-sm" id="gm-node-cancel-btn">Cancel</button>
                  <button type="submit" class="btn btn-primary btn-sm" id="gm-node-save-btn">Save Node</button>
                </div>
              </div>
            </form>
          </div>
        `;
        document.body.appendChild(wrap);
      }
      this.nodeModalBackdrop = document.getElementById("graph-node-modal-backdrop");

      if (!document.getElementById("graph-edge-modal-backdrop")) {
        const wrap = document.createElement("div");
        wrap.id = "graph-edge-modal-backdrop";
        wrap.className = "graph-modal-backdrop hidden";
        wrap.innerHTML = `
          <div class="graph-modal" id="graph-edge-modal" role="dialog" aria-labelledby="edge-modal-title">
            <div class="graph-modal-header">
              <div>
                <div class="puck-kind-pill" id="edge-modal-pill">TYPED RELATIONSHIP</div>
                <h3 id="edge-modal-title">Connect Entities</h3>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" id="btn-close-edge-modal">×</button>
            </div>
            <form id="graph-edge-form" class="studio-form graph-modal-body">
              <div class="edge-endpoints-bar" id="gm-edge-endpoints-bar"></div>
              <div id="gm-edge-manual-selectors" class="form-row-2 hidden">
                <label>First Item (A)
                  <select id="gm-edge-src-select"></select>
                </label>
                <label>Second Item (B)
                  <select id="gm-edge-dst-select"></select>
                </label>
              </div>
              <div id="gm-edge-norm-note" class="hint-banner hidden"></div>
              <div id="gm-edge-dynamic-fields" class="studio-form"></div>
              <div class="form-row-2">
                <label>How certain is this link?
                  <select id="gm-edge-conf">
                    <option value="CONFIRMED">Confirmed (Verified / Documented)</option>
                    <option value="ASSESSED">Likely (Analytical Judgment)</option>
                    <option value="UNCONFIRMED">Draft / Unconfirmed Assumption</option>
                  </select>
                </label>
                <label>Source or Context Note (Optional)
                  <input type="text" id="gm-edge-prov" placeholder="Document, meeting, or rationale" />
                </label>
              </div>
              <div id="gm-edge-error" class="hint-banner warn hidden"></div>
              <div class="graph-modal-footer">
                <button type="button" class="btn btn-secondary btn-sm hidden" id="gm-edge-swap-btn">⇄ Swap Direction</button>
                <div style="display:flex;gap:8px;margin-left:auto">
                  <button type="button" class="btn btn-ghost btn-sm" id="gm-edge-cancel-btn">Cancel</button>
                  <button type="submit" class="btn btn-primary btn-sm" id="gm-edge-save-btn">Create Relationship</button>
                </div>
              </div>
            </form>
          </div>
        `;
        document.body.appendChild(wrap);
      }
      this.edgeModalBackdrop = document.getElementById("graph-edge-modal-backdrop");
    }

    getWorldPoint(clientX, clientY) {
      const snap = this.getSnapshot();
      const zoom = Number(snap?.zoom || 1) || 1;
      const rect = this.worldEl.getBoundingClientRect();
      return {
        x: (clientX - rect.left) / zoom,
        y: (clientY - rect.top) / zoom,
      };
    }

    getEntityEntitiesCatalog() {
      const snap = this.getSnapshot();
      const tree = snap?.triView?.capability_tree || snap?.treeView || {};
      return {
        organizations: tree.organizations || [],
        efforts: (tree.nodes || []).map((n) => n.effort),
        effortNodes: tree.nodes || [],
        interests: tree.interests || [],
        pools: tree.resource_pools || [],
        poolBalances: snap?.triView?.pool_balances || [],
      };
    }

    findEntityLabel(kind, id) {
      const cat = this.getEntityEntitiesCatalog();
      if (kind === "organization") return cat.organizations.find((o) => o.id === id)?.name || id;
      if (kind === "effort") return cat.efforts.find((e) => e.id === id)?.name || id;
      if (kind === "interest") return cat.interests.find((i) => i.id === id)?.name || id;
      return id;
    }

    bindEvents() {
      // Hide menu on global click or Escape
      window.addEventListener("click", (ev) => {
        if (!ev.target.closest("#graph-context-menu")) this.hideMenu();
      });
      window.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") {
          this.hideMenu();
          this.cancelConnectPick();
          this.closeNodeModal();
          this.closeEdgeModal();
        }
      });

      // Modal close buttons
      document.getElementById("btn-close-node-modal")?.addEventListener("click", () => this.closeNodeModal());
      document.getElementById("gm-node-cancel-btn")?.addEventListener("click", () => this.closeNodeModal());
      this.nodeModalBackdrop?.addEventListener("click", (ev) => {
        if (ev.target === this.nodeModalBackdrop) this.closeNodeModal();
      });

      document.getElementById("btn-close-edge-modal")?.addEventListener("click", () => this.closeEdgeModal());
      document.getElementById("gm-edge-cancel-btn")?.addEventListener("click", () => this.closeEdgeModal());
      this.edgeModalBackdrop?.addEventListener("click", (ev) => {
        if (ev.target === this.edgeModalBackdrop) this.closeEdgeModal();
      });

      // Canvas right-click context menu (empty canvas, node card, or SVG edge)
      this.viewportEl?.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        this.cancelConnectPick();

        const nodeEl = ev.target.closest("[data-entity-kind][data-entity-id]");
        if (nodeEl) {
          this.showNodeMenu(ev.clientX, ev.clientY, {
            kind: nodeEl.dataset.entityKind,
            id: nodeEl.dataset.entityId,
            label: nodeEl.dataset.entityLabel || nodeEl.dataset.entityId,
          });
          return;
        }

        const edgeEl = ev.target.closest("path[data-edge-cat][data-edge-id]");
        if (edgeEl) {
          this.showEdgeMenu(ev.clientX, ev.clientY, {
            cat: edgeEl.dataset.edgeCat,
            id: edgeEl.dataset.edgeId,
            label: edgeEl.dataset.edgeLabel || edgeEl.dataset.edgeId,
          });
          return;
        }

        const worldPt = this.getWorldPoint(ev.clientX, ev.clientY);
        this.showCanvasMenu(ev.clientX, ev.clientY, worldPt);
      });

      // Left-click directly on interactive SVG edge opens compact edge menu
      this.viewportEl?.addEventListener("click", (ev) => {
        const edgeEl = ev.target.closest("path[data-edge-cat][data-edge-id]");
        if (edgeEl) {
          ev.stopPropagation();
          this.showEdgeMenu(ev.clientX, ev.clientY, {
            cat: edgeEl.dataset.edgeCat,
            id: edgeEl.dataset.edgeId,
            label: edgeEl.dataset.edgeLabel || edgeEl.dataset.edgeId,
          });
          return;
        }

        // Handle click-to-connect target picking if active
        if (this.connectPickSource) {
          const targetEl = ev.target.closest("[data-entity-kind][data-entity-id]");
          if (targetEl) {
            ev.stopPropagation();
            ev.preventDefault();
            const target = {
              kind: targetEl.dataset.entityKind,
              id: targetEl.dataset.entityId,
              label: targetEl.dataset.entityLabel || targetEl.dataset.entityId,
            };
            const source = this.connectPickSource;
            this.cancelConnectPick();
            if (source.kind === target.kind && source.id === target.id) {
              this.notify?.("Cannot link a node to itself.", "warn");
              return;
            }
            this.openEdgeModal(source, target);
          }
        }
      }, true);

      // Drag-to-connect starting from any .node-connect-port
      this.viewportEl?.addEventListener("mousedown", (ev) => {
        const port = ev.target.closest(".node-connect-port");
        if (!port || ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();

        const nodeEl = port.closest("[data-entity-kind][data-entity-id]");
        if (!nodeEl) return;

        const source = {
          kind: nodeEl.dataset.entityKind,
          id: nodeEl.dataset.entityId,
          label: nodeEl.dataset.entityLabel || nodeEl.dataset.entityId,
        };

        const portRect = port.getBoundingClientRect();
        const startWorld = this.getWorldPoint(
          portRect.left + portRect.width / 2,
          portRect.top + portRect.height / 2
        );

        this.isDraggingConnection = true;
        document.body.classList.add("is-connecting");

        const w = this.worldEl.offsetWidth || 1200;
        const h = this.worldEl.offsetHeight || 800;
        this.dragSvgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
        this.dragSvgEl.style.width = `${w}px`;
        this.dragSvgEl.style.height = `${h}px`;
        this.dragSvgEl.innerHTML = "";

        const wire = document.createElementNS(SVG_NS, "path");
        wire.setAttribute("class", "rubber-band-wire");
        wire.setAttribute("fill", "none");
        this.dragSvgEl.appendChild(wire);

        let hoveredTargetEl = null;

        const updateWire = (clientX, clientY) => {
          const endWorld = this.getWorldPoint(clientX, clientY);
          const dx = Math.max(40, Math.abs(endWorld.x - startWorld.x) * 0.4);
          wire.setAttribute(
            "d",
            `M ${startWorld.x.toFixed(1)} ${startWorld.y.toFixed(1)} C ${(startWorld.x + dx).toFixed(1)} ${startWorld.y.toFixed(1)}, ${(endWorld.x - dx).toFixed(1)} ${endWorld.y.toFixed(1)}, ${endWorld.x.toFixed(1)} ${endWorld.y.toFixed(1)}`
          );

          const elUnder = document.elementFromPoint(clientX, clientY)?.closest("[data-entity-kind][data-entity-id]");
          if (hoveredTargetEl && hoveredTargetEl !== elUnder) {
            hoveredTargetEl.classList.remove("drop-target-hover");
            hoveredTargetEl = null;
          }
          if (
            elUnder &&
            !(elUnder.dataset.entityKind === source.kind && elUnder.dataset.entityId === source.id)
          ) {
            elUnder.classList.add("drop-target-hover");
            hoveredTargetEl = elUnder;
          }
        };

        updateWire(ev.clientX, ev.clientY);

        const onMove = (mv) => {
          updateWire(mv.clientX, mv.clientY);
        };

        const onUp = (up) => {
          window.removeEventListener("mousemove", onMove);
          window.removeEventListener("mouseup", onUp);
          this.isDraggingConnection = false;
          document.body.classList.remove("is-connecting");
          this.dragSvgEl.innerHTML = "";
          if (hoveredTargetEl) {
            hoveredTargetEl.classList.remove("drop-target-hover");
          }

          const finalTarget = document.elementFromPoint(up.clientX, up.clientY)?.closest("[data-entity-kind][data-entity-id]");
          if (
            finalTarget &&
            !(finalTarget.dataset.entityKind === source.kind && finalTarget.dataset.entityId === source.id)
          ) {
            this.openEdgeModal(source, {
              kind: finalTarget.dataset.entityKind,
              id: finalTarget.dataset.entityId,
              label: finalTarget.dataset.entityLabel || finalTarget.dataset.entityId,
            });
          }
        };

        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
      });
    }

    hideMenu() {
      this.menuEl?.classList.add("hidden");
    }

    positionMenu(clientX, clientY) {
      this.menuEl.classList.remove("hidden");
      const mw = this.menuEl.offsetWidth || 230;
      const mh = this.menuEl.offsetHeight || 220;
      const x = Math.min(clientX, window.innerWidth - mw - 12);
      const y = Math.min(clientY, window.innerHeight - mh - 12);
      this.menuEl.style.left = `${Math.max(8, x)}px`;
      this.menuEl.style.top = `${Math.max(8, y)}px`;
    }

    showCanvasMenu(clientX, clientY, worldPt) {
      const { escapeHtml } = global.BijouApi;
      const filtered = this.isFiltered ? this.isFiltered() : false;
      this.menuEl.innerHTML = `
        <div class="gcm-header">Graph Actions</div>
        <button type="button" class="gcm-item" data-act="create" data-kind="effort">+ Create Work Effort Here</button>
        <button type="button" class="gcm-item" data-act="create" data-kind="organization">+ Create Organization Here</button>
        <button type="button" class="gcm-item" data-act="create" data-kind="interest">+ Create Goal / Interest Here</button>
        <div class="gcm-divider"></div>
        <button type="button" class="gcm-item" data-act="create-edge">+ Connect Two Items...</button>
        ${filtered ? '<button type="button" class="gcm-item" data-act="reset-graph">Reset Graph Filters &amp; Show All</button>' : ""}
        <div class="gcm-meta mono-text">Canvas (${Math.round(worldPt.x)}, ${Math.round(worldPt.y)})</div>
      `;

      this.menuEl.querySelectorAll("[data-act='create']").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.hideMenu();
          this.openNodeModal({
            mode: "create",
            kind: btn.dataset.kind,
            spawnPoint: worldPt,
          });
        });
      });

      this.menuEl.querySelector("[data-act='create-edge']")?.addEventListener("click", () => {
        this.hideMenu();
        this.openEdgeModal(null, null);
      });

      this.menuEl.querySelector("[data-act='reset-graph']")?.addEventListener("click", () => {
        this.hideMenu();
        this.onResetGraph?.();
      });

      this.positionMenu(clientX, clientY);
      void escapeHtml;
    }

    showNodeMenu(clientX, clientY, entity) {
      const { escapeHtml } = global.BijouApi;
      const isEffort = entity.kind === "effort";
      this.menuEl.innerHTML = `
        <div class="gcm-header">${escapeHtml(entity.kind.toUpperCase())}: ${escapeHtml(entity.label)}</div>
        <button type="button" class="gcm-item" data-act="focus">Isolate "${escapeHtml(entity.label)}" &amp; Connections</button>
        <button type="button" class="gcm-item" data-act="connect">Connect "${escapeHtml(entity.label)}" → Target...</button>
        <button type="button" class="gcm-item" data-act="edit">Quick Edit</button>
        <button type="button" class="gcm-item" data-act="inspect">Inspect Full Details</button>
        ${isEffort ? '<div class="gcm-divider"></div><button type="button" class="gcm-item" data-act="stage-slip">Test +30d Delay in Cart</button>' : ""}
        <div class="gcm-divider"></div>
        <button type="button" class="gcm-item gcm-danger" data-act="delete">Delete "${escapeHtml(entity.label)}"</button>
      `;

      this.menuEl.querySelector("[data-act='focus']")?.addEventListener("click", () => {
        this.hideMenu();
        this.onFocusNode?.(entity);
      });

      this.menuEl.querySelector("[data-act='connect']")?.addEventListener("click", () => {
        this.hideMenu();
        this.startConnectPick(entity);
      });

      this.menuEl.querySelector("[data-act='edit']")?.addEventListener("click", () => {
        this.hideMenu();
        this.openNodeModal({ mode: "edit", kind: entity.kind, id: entity.id });
      });

      this.menuEl.querySelector("[data-act='inspect']")?.addEventListener("click", () => {
        this.hideMenu();
        this.onInspectEntity?.(entity.kind, entity.id);
      });

      this.menuEl.querySelector("[data-act='stage-slip']")?.addEventListener("click", () => {
        this.hideMenu();
        this.onStageSlip?.(entity.id, 30);
      });

      let deleteArmed = false;
      const delBtn = this.menuEl.querySelector("[data-act='delete']");
      delBtn?.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!deleteArmed) {
          deleteArmed = true;
          delBtn.textContent = `Confirm Delete "${entity.label}"?`;
          delBtn.classList.add("armed");
          return;
        }
        this.hideMenu();
        try {
          if (entity.kind === "organization") await global.BijouApi.deleteOrganization(entity.id);
          else if (entity.kind === "interest") await global.BijouApi.deleteInterest(entity.id);
          else await global.BijouApi.deleteEffort(entity.id);
          this.notify?.(`Deleted ${entity.kind} "${entity.label}".`, "info");
          await this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(`Delete blocked: ${err.message}`, "error");
        }
      });

      this.positionMenu(clientX, clientY);
    }

    showEdgeMenu(clientX, clientY, edge) {
      const { escapeHtml } = global.BijouApi;
      this.menuEl.innerHTML = `
        <div class="gcm-header">Relationship Edge</div>
        <div class="gcm-meta">${escapeHtml(edge.label)}</div>
        <div class="gcm-divider"></div>
        <button type="button" class="gcm-item gcm-danger" data-act="del-edge">Delete Relationship</button>
      `;

      let armed = false;
      const btn = this.menuEl.querySelector("[data-act='del-edge']");
      btn?.addEventListener("click", async (ev) => {
        ev.stopPropagation();
        if (!armed) {
          armed = true;
          btn.textContent = "Confirm Delete Relationship?";
          btn.classList.add("armed");
          return;
        }
        this.hideMenu();
        try {
          await global.BijouApi.deleteEdge(edge.cat, edge.id);
          this.notify?.("Relationship removed.", "info");
          await this.onGraphMutated?.();
        } catch (err) {
          this.notify?.(`Delete edge failed: ${err.message}`, "error");
        }
      });

      this.positionMenu(clientX, clientY);
    }

    startConnectPick(source) {
      const { escapeHtml } = global.BijouApi;
      this.connectPickSource = source;
      this.bannerEl.innerHTML = `
        <span>Connect mode: Click a target node to link from <strong>${escapeHtml(source.label)}</strong></span>
        <button type="button" class="btn btn-ghost btn-xs" id="btn-cancel-connect-pick">Cancel (Esc)</button>
      `;
      this.bannerEl.classList.remove("hidden");
      document.getElementById("btn-cancel-connect-pick")?.addEventListener("click", () => this.cancelConnectPick());
    }

    cancelConnectPick() {
      this.connectPickSource = null;
      this.bannerEl?.classList.add("hidden");
    }

    // --- QUICK NODE CREATE / EDIT MODAL ---

    openNodeModal({ mode, kind, id = null, spawnPoint = null }) {
      const cat = this.getEntityEntitiesCatalog();
      const kindSel = document.getElementById("gm-node-kind");
      const idInput = document.getElementById("gm-node-id");
      const nameInput = document.getElementById("gm-node-name");
      const descInput = document.getElementById("gm-node-desc");
      const errEl = document.getElementById("gm-node-error");
      const studioBtn = document.getElementById("gm-node-studio-btn");

      errEl.classList.add("hidden");
      this.pendingSpawn = mode === "create" ? spawnPoint : null;
      let existingRecord = null;
      let idTouched = mode === "edit";

      if (mode === "edit" && id) {
        if (kind === "effort") existingRecord = cat.efforts.find((e) => e.id === id);
        else if (kind === "organization") existingRecord = cat.organizations.find((o) => o.id === id);
        else existingRecord = cat.interests.find((i) => i.id === id);
      }

      document.getElementById("node-modal-title").textContent =
        mode === "edit" ? `Edit ${kind.toUpperCase()}` : "Create Graph Node";
      document.getElementById("node-modal-pill").textContent =
        mode === "edit" ? `${kind.toUpperCase()} · ${id}` : "GRAPH-NATIVE CREATE";

      kindSel.value = kind || "effort";
      kindSel.disabled = mode === "edit";
      idInput.readOnly = mode === "edit";

      idInput.value = existingRecord?.id || "";
      nameInput.value = existingRecord?.name || "";
      descInput.value = existingRecord?.description || "";

      if (mode === "edit" && kind === "effort") {
        studioBtn.classList.remove("hidden");
        studioBtn.onclick = () => {
          this.closeNodeModal();
          this.onOpenStudio?.("efforts", id);
        };
      } else {
        studioBtn.classList.add("hidden");
      }

      const renderDynamic = () => {
        const k = kindSel.value;
        const dyn = document.getElementById("gm-node-dynamic-fields");
        if (k === "effort") {
          dyn.innerHTML = `
            <div class="form-row-2">
              <label>Current Status
                <select id="gm-eff-state">
                  <option value="COMPLETED">Completed / Done</option>
                  <option value="IN_WORK">In Progress / Active</option>
                  <option value="PLANNED">Planned / Future</option>
                  <option value="BACKLOGGED">Backlogged / On Hold</option>
                  <option value="DISCOVERY_PENDING">Needs Discovery / Scoping</option>
                  <option value="CANCELLED">Cancelled</option>
                </select>
              </label>
              <label>Estimated Duration (Days)
                <input type="number" min="1" id="gm-eff-days" placeholder="Optional / Unknown" />
              </label>
            </div>
            <div class="form-row-2">
              <label>Start Date (Optional) <input type="date" id="gm-eff-start" /></label>
              <label>Target Finish Date (Optional) <input type="date" id="gm-eff-end" /></label>
            </div>
          `;
          document.getElementById("gm-eff-state").value = existingRecord?.state || "PLANNED";
          document.getElementById("gm-eff-days").value = existingRecord?.estimated_duration_days || "";
          document.getElementById("gm-eff-start").value = existingRecord?.start_date || "";
          document.getElementById("gm-eff-end").value = existingRecord?.end_date || "";
        } else if (k === "organization") {
          dyn.innerHTML = `
            <div class="form-row-2">
              <label>Echelon Level <input type="number" min="0" id="gm-org-echelon" value="${existingRecord?.echelon_level ?? 1}" /></label>
              <label style="flex-direction:row;align-items:center;gap:8px;padding-top:16px">
                <input type="checkbox" id="gm-org-managed" ${existingRecord?.is_managed ? "checked" : ""} /> Managed Org Owner
              </label>
            </div>
            <label>Tags (comma-separated) <input type="text" id="gm-org-tags" value="${global.BijouApi.escapeHtml((existingRecord?.tags || []).join(", "))}" placeholder="space, isr" /></label>
          `;
        } else {
          dyn.innerHTML = `
            <div class="form-row-3">
              <label>Interest Kind
                <select id="gm-intr-kind">
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
              <label>Start Date <input type="date" id="gm-intr-start" value="${existingRecord?.start_date || ""}" /></label>
              <label>End Date <input type="date" id="gm-intr-end" value="${existingRecord?.end_date || ""}" /></label>
            </div>
          `;
          if (existingRecord?.interest_kind) {
            document.getElementById("gm-intr-kind").value = existingRecord.interest_kind;
          }
        }
      };

      renderDynamic();
      kindSel.onchange = () => {
        renderDynamic();
        if (!idTouched && nameInput.value.trim()) {
          idInput.value = this.slugId(kindSel.value, nameInput.value);
        }
      };

      idInput.oninput = () => {
        idTouched = idInput.value.trim().length > 0;
      };

      nameInput.oninput = () => {
        if (!idTouched) {
          idInput.value = this.slugId(kindSel.value, nameInput.value);
        }
      };

      const form = document.getElementById("graph-node-form");
      form.onsubmit = async (e) => {
        e.preventDefault();
        errEl.classList.add("hidden");
        const activeKind = kindSel.value;
        const cleanName = nameInput.value.trim();
        const cleanId = idInput.value.trim() || this.slugId(activeKind, cleanName);
        const cleanDesc = descInput.value.trim();

        try {
          if (activeKind === "effort") {
            const daysRaw = document.getElementById("gm-eff-days").value.trim();
            await global.BijouApi.upsertEffort({
              id: cleanId,
              name: cleanName,
              description: cleanDesc,
              state: document.getElementById("gm-eff-state").value,
              start_date: document.getElementById("gm-eff-start").value || null,
              end_date: document.getElementById("gm-eff-end").value || null,
              estimated_duration_days: daysRaw ? parseInt(daysRaw, 10) : null,
              resource_requirements: existingRecord?.resource_requirements || [],
              risks: existingRecord?.risks || [],
              mitigators: existingRecord?.mitigators || [],
            });
          } else if (activeKind === "organization") {
            await global.BijouApi.upsertOrganization({
              id: cleanId,
              name: cleanName,
              description: cleanDesc,
              echelon_level: parseInt(document.getElementById("gm-org-echelon").value || "1", 10),
              is_managed: Boolean(document.getElementById("gm-org-managed").checked),
              tags: document
                .getElementById("gm-org-tags")
                .value.split(",")
                .map((s) => s.trim())
                .filter(Boolean),
            });
          } else {
            await global.BijouApi.upsertInterest({
              id: cleanId,
              name: cleanName,
              description: cleanDesc,
              interest_kind: document.getElementById("gm-intr-kind").value,
              start_date: document.getElementById("gm-intr-start").value || null,
              end_date: document.getElementById("gm-intr-end").value || null,
            });
          }

          if (this.pendingSpawn && global.BijouViewNeural?.setSpawnPosition) {
            global.BijouViewNeural.setSpawnPosition(activeKind, cleanId, this.pendingSpawn.x, this.pendingSpawn.y);
          }

          this.notify?.(`Saved ${activeKind} "${cleanName}".`, "success");
          this.closeNodeModal();
          await this.onGraphMutated?.();
        } catch (err) {
          errEl.textContent = err.message;
          errEl.classList.remove("hidden");
        }
      };

      this.nodeModalBackdrop.classList.remove("hidden");
      setTimeout(() => nameInput.focus(), 20);
    }

    slugId(kind, name) {
      const prefix = kind === "organization" ? "org" : kind === "interest" ? "intr" : "eff";
      const slug = (name || "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "")
        .slice(0, 32);
      return slug ? `${prefix}-${slug}` : `${prefix}-${Date.now().toString(36).slice(-5)}`;
    }

    closeNodeModal() {
      this.nodeModalBackdrop?.classList.add("hidden");
    }

    // --- CONTEXTUAL EDGE CREATION MODAL ---

    normalizePair(src, dst) {
      // Automatically align asymmetric directional pairs into valid graph semantics
      if (src.kind === "effort" && dst.kind === "organization") {
        return {
          src: dst,
          dst: src,
          edgeCategory: "org_effort",
          note: "Auto-aligned direction: Organization resources Effort.",
        };
      }
      if (src.kind === "interest" && dst.kind === "effort") {
        return {
          src: dst,
          dst: src,
          edgeCategory: "effort_interest",
          note: "Auto-aligned direction: Effort aligns with Interest.",
        };
      }
      if (src.kind === "interest" && dst.kind === "organization") {
        return {
          src: dst,
          dst: src,
          edgeCategory: "org_interest",
          note: "Auto-aligned direction: Organization holds stance on Interest.",
        };
      }
      if (src.kind === "organization" && dst.kind === "organization") {
        return { src, dst, edgeCategory: "org_org", note: null };
      }
      if (src.kind === "organization" && dst.kind === "interest") {
        return { src, dst, edgeCategory: "org_interest", note: null };
      }
      if (src.kind === "interest" && dst.kind === "interest") {
        return { src, dst, edgeCategory: "interest_interest", note: null };
      }
      if (src.kind === "organization" && dst.kind === "effort") {
        return { src, dst, edgeCategory: "org_effort", note: null };
      }
      if (src.kind === "effort" && dst.kind === "interest") {
        return { src, dst, edgeCategory: "effort_interest", note: null };
      }
      return { src, dst, edgeCategory: "effort_effort", note: null };
    }

    openEdgeModal(sourceArg, targetArg) {
      const { escapeHtml } = global.BijouApi;
      const cat = this.getEntityEntitiesCatalog();
      const errEl = document.getElementById("gm-edge-error");
      const manualWrap = document.getElementById("gm-edge-manual-selectors");
      const swapBtn = document.getElementById("gm-edge-swap-btn");
      errEl.classList.add("hidden");

      const allEntities = [
        ...cat.organizations.map((o) => ({ kind: "organization", id: o.id, label: o.name })),
        ...cat.efforts.map((e) => ({ kind: "effort", id: e.id, label: e.name })),
        ...cat.interests.map((i) => ({ kind: "interest", id: i.id, label: i.name })),
      ];

      if (allEntities.length < 2) {
        this.notify?.("Create at least two entities before connecting them.", "warn");
        return;
      }

      const isManual = !sourceArg || !targetArg;
      let pairState = isManual
        ? this.normalizePair(allEntities[0], allEntities[1])
        : this.normalizePair(sourceArg, targetArg);

      const srcSel = document.getElementById("gm-edge-src-select");
      const dstSel = document.getElementById("gm-edge-dst-select");

      if (isManual) {
        manualWrap.classList.remove("hidden");
        const optsHtml = allEntities
          .map((it) => `<option value="${escapeHtml(it.kind)}::${escapeHtml(it.id)}">[${escapeHtml(it.kind.toUpperCase())}] ${escapeHtml(it.label)}</option>`)
          .join("");
        srcSel.innerHTML = optsHtml;
        dstSel.innerHTML = optsHtml;
        srcSel.value = `${pairState.src.kind}::${pairState.src.id}`;
        dstSel.value = `${pairState.dst.kind}::${pairState.dst.id}`;

        const syncManual = () => {
          const [sk, sid] = srcSel.value.split("::");
          const [dk, did] = dstSel.value.split("::");
          pairState = this.normalizePair(
            { kind: sk, id: sid, label: this.findEntityLabel(sk, sid) },
            { kind: dk, id: did, label: this.findEntityLabel(dk, did) }
          );
          renderPairUi();
        };
        srcSel.onchange = syncManual;
        dstSel.onchange = syncManual;
      } else {
        manualWrap.classList.add("hidden");
      }

      const renderPairUi = () => {
        const { src, dst, edgeCategory, note } = pairState;
        const barEl = document.getElementById("gm-edge-endpoints-bar");
        const noteEl = document.getElementById("gm-edge-norm-note");
        const dynEl = document.getElementById("gm-edge-dynamic-fields");

        const pillNames = {
          org_org: "PARTNERSHIP OR HIERARCHY",
          org_interest: "ORGANIZATION PRIORITY",
          interest_interest: "GOAL / TOPIC RELATIONSHIP",
          org_effort: "SUPPORT & RESOURCING",
          effort_interest: "WORK TO GOAL ALIGNMENT",
          effort_effort: "WORK DEPENDENCY",
        };
        const friendlyKind = (k) =>
          k === "organization" ? "Org" : k === "interest" ? "Goal" : "Effort";
        document.getElementById("edge-modal-pill").textContent = pillNames[edgeCategory];
        document.getElementById("edge-modal-title").textContent = `Link: ${src.label} ↔ ${dst.label}`;

        barEl.innerHTML = `
          <span class="endpoint-badge kind-${escapeHtml(src.kind)}">${escapeHtml(friendlyKind(src.kind))}: ${escapeHtml(src.label)}</span>
          <span class="endpoint-arrow">↔</span>
          <span class="endpoint-badge kind-${escapeHtml(dst.kind)}">${escapeHtml(friendlyKind(dst.kind))}: ${escapeHtml(dst.label)}</span>
        `;

        if (note) {
          noteEl.textContent = note;
          noteEl.classList.remove("hidden");
        } else {
          noteEl.classList.add("hidden");
        }

        // Allow swapping ends on same-type edges for convenience
        if (src.kind === dst.kind) {
          swapBtn.classList.remove("hidden");
          swapBtn.onclick = () => {
            pairState = this.normalizePair(dst, src);
            renderPairUi();
          };
        } else {
          swapBtn.classList.add("hidden");
        }

        if (edgeCategory === "effort_effort") {
          dynEl.innerHTML = `
            <label>How do these two efforts depend on each other?
              <select id="ge-ee-choice">
                <option value="AB|BLOCKING">"${escapeHtml(src.label)}" must finish before "${escapeHtml(dst.label)}" can complete (Blocking)</option>
                <option value="BA|BLOCKING">"${escapeHtml(dst.label)}" must finish before "${escapeHtml(src.label)}" can complete (Blocking)</option>
                <option value="AB|NON_BLOCKING_INFORMS">"${escapeHtml(src.label)}" shares useful insights with "${escapeHtml(dst.label)}" without delaying schedule</option>
                <option value="BA|NON_BLOCKING_INFORMS">"${escapeHtml(dst.label)}" shares useful insights with "${escapeHtml(src.label)}" without delaying schedule</option>
              </select>
            </label>
            <label>How strong is this dependency?
              <select id="ge-degree">
                <option value="1.0">Critical / Direct Handoff</option>
                <option value="0.75">Strong Dependency</option>
                <option value="0.5">Moderate Influence</option>
                <option value="0.25">Light Advisory Input</option>
              </select>
            </label>
          `;
        } else if (edgeCategory === "org_effort") {
          const orgPools = cat.pools.filter((p) => p.org_id === src.id);
          const effNode = cat.effortNodes.find((n) => n.effort.id === dst.id);
          const effReqs = effNode?.effort?.resource_requirements || [];

          dynEl.innerHTML = `
            <div class="form-row-2">
              <label>Funding / Resource Pool (Optional)
                <select id="ge-pool">
                  <option value="">General / Unspecified Support</option>
                  ${orgPools.map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)} (${p.capacity} ${escapeHtml(p.unit)})</option>`).join("")}
                </select>
              </label>
              <label>Specific Need Filled (Optional)
                <select id="ge-req">
                  <option value="">General Support for this Work</option>
                  ${effReqs.map((r) => `<option value="${escapeHtml(r.id)}">${escapeHtml(r.label)} (${r.quantity} ${escapeHtml(r.unit)}${r.required_skill ? ` · ${escapeHtml(r.required_skill)}` : ""})</option>`).join("")}
                </select>
              </label>
            </div>
            <div class="form-row-3">
              <label>What is being provided?
                <select id="ge-rtype">
                  <option value="MONEY">Funding ($ Money)</option>
                  <option value="STAFF">People / Staffing</option>
                  <option value="COMPUTE">Compute / Servers</option>
                  <option value="MATERIAL">Equipment / Material</option>
                  <option value="GENERIC_SUPPORT">General Support</option>
                </select>
              </label>
              <label>Amount <input type="number" step="any" min="0" value="100000" id="ge-amount" required /></label>
              <label>Unit <input type="text" value="USD" id="ge-unit" required /></label>
            </div>
            <div class="form-row-2">
              <label>Assigned Specialty / Skill (Optional) <input type="text" id="ge-skill" placeholder="Optional specialty" /></label>
              <label>Delay Estimate if Specialty Differs (Days) <input type="number" min="0" id="ge-slip-penalty" placeholder="Default 30 days" /></label>
            </div>
            <div id="ge-eligibility-hint" class="hint-banner hidden"></div>
          `;

          const poolSel = document.getElementById("ge-pool");
          const reqSel = document.getElementById("ge-req");
          const catSel = document.getElementById("ge-rtype");
          const amtInp = document.getElementById("ge-amount");
          const unitInp = document.getElementById("ge-unit");
          const skillInp = document.getElementById("ge-skill");
          const hintBox = document.getElementById("ge-eligibility-hint");

          const refreshHint = () => {
            const hints = [];
            let warn = false;
            const pid = poolSel.value;
            const rid = reqSel.value;

            if (pid && effNode) {
              const pb = cat.poolBalances.find((b) => b.pool.id === pid);
              if (pb && pb.pool.restricted_interest_ids?.length > 0) {
                const elig = new Set(pb.eligible_interest_ids || []);
                const ok = (effNode.aligned_interest_ids || []).some((iid) => elig.has(iid));
                if (ok) {
                  hints.push(`Funding Rule Check: "${pb.pool.name}" is eligible for this effort.`);
                } else {
                  warn = true;
                  hints.push(`Funding Rule Warning: "${pb.pool.name}" is earmarked for other goals (color-of-money mismatch).`);
                }
              }
            }
            if (rid && effNode) {
              const req = effReqs.find((r) => r.id === rid);
              const assigned = skillInp.value.trim();
              if (req?.required_skill && assigned && req.required_skill.toLowerCase() !== assigned.toLowerCase()) {
                warn = true;
                hints.push(`Skill Mismatch Notice: Needs "${req.required_skill}", assigning "${assigned}". Adds a schedule risk.`);
              }
            }

            if (hints.length) {
              hintBox.classList.remove("hidden");
              hintBox.classList.toggle("warn", warn);
              hintBox.innerHTML = hints.map((h) => `<div>${escapeHtml(h)}</div>`).join("");
            } else {
              hintBox.classList.add("hidden");
            }
          };

          poolSel.onchange = () => {
            const p = orgPools.find((x) => x.id === poolSel.value);
            if (p) {
              catSel.value = p.category;
              unitInp.value = p.unit;
              if (p.skill_tag) skillInp.value = p.skill_tag;
            }
            refreshHint();
          };
          reqSel.onchange = () => {
            const r = effReqs.find((x) => x.id === reqSel.value);
            if (r && !poolSel.value) {
              catSel.value = r.category;
              unitInp.value = r.unit;
              amtInp.value = String(r.quantity || 1);
            }
            refreshHint();
          };
          skillInp.oninput = refreshHint;
        } else if (edgeCategory === "effort_interest") {
          dynEl.innerHTML = `
            <div class="form-row-2">
              <label>How does "${escapeHtml(src.label)}" help "${escapeHtml(dst.label)}"?
                <select id="ge-ei-rel">
                  <option value="DIRECT_SOLUTION">Directly delivers or solves this goal</option>
                  <option value="INDIRECT_ENABLER">Supports or enables progress toward it</option>
                  <option value="FUNDED_FOR">Funded specifically to address it</option>
                  <option value="PARTIAL_ALIGNMENT">Partially contributes / overlaps</option>
                </select>
              </label>
              <label>Contribution Impact
                <select id="ge-ei-weight">
                  <option value="1.0">Primary Driver (High Impact)</option>
                  <option value="0.8">Major Contributor</option>
                  <option value="0.5">Moderate Contributor</option>
                  <option value="0.25">Minor Alignment</option>
                </select>
              </label>
            </div>
          `;
        } else if (edgeCategory === "org_interest") {
          dynEl.innerHTML = `
            <div class="form-row-2">
              <label>What is "${escapeHtml(src.label)}"'s role on "${escapeHtml(dst.label)}"?
                <select id="ge-oi-stance">
                  <option value="MISSION_ALIGNED">Aligns with their mission</option>
                  <option value="RESPONSIBLE_OWNER">Owns / is accountable for delivering it</option>
                  <option value="DIRECT_INVESTOR">Directly funding or investing in it</option>
                  <option value="BENEFICIARY">Benefits from progress (Customer / User)</option>
                  <option value="PERCEIVED_GAP">Sees an unaddressed gap or need here</option>
                </select>
              </label>
              <label>How important is this to ${escapeHtml(src.label)}?
                <select id="ge-oi-prio">
                  <option value="1.0">Top / Critical Priority</option>
                  <option value="0.8">High Priority</option>
                  <option value="0.5">Medium Priority</option>
                  <option value="0.25">Low / Watchlist</option>
                </select>
              </label>
            </div>
            <label style="flex-direction:row;align-items:center;gap:8px">
              <input type="checkbox" id="ge-oi-inherit" checked /> Sub-teams should inherit this priority automatically
            </label>
          `;
        } else if (edgeCategory === "interest_interest") {
          dynEl.innerHTML = `
            <label>How do these two goals or topics relate?
              <select id="ge-ii-choice">
                <option value="AB|SPECIALIZES">"${escapeHtml(src.label)}" is a broader category containing "${escapeHtml(dst.label)}"</option>
                <option value="BA|SPECIALIZES">"${escapeHtml(dst.label)}" is a broader category containing "${escapeHtml(src.label)}"</option>
                <option value="AB|CONTRIBUTES_TO">"${escapeHtml(src.label)}" helps advance "${escapeHtml(dst.label)}"</option>
                <option value="BA|CONTRIBUTES_TO">"${escapeHtml(dst.label)}" helps advance "${escapeHtml(src.label)}"</option>
                <option value="AB|RELATED_TO">"${escapeHtml(src.label)}" and "${escapeHtml(dst.label)}" are closely related topics</option>
              </select>
            </label>
          `;
        } else {
          dynEl.innerHTML = `
            <label>How are "${escapeHtml(src.label)}" and "${escapeHtml(dst.label)}" connected?
              <select id="ge-oo-choice">
                <option value="AB|HIERARCHICAL_PARENT">"${escapeHtml(src.label)}" oversees / is parent organization of "${escapeHtml(dst.label)}"</option>
                <option value="BA|HIERARCHICAL_PARENT">"${escapeHtml(dst.label)}" oversees / is parent organization of "${escapeHtml(src.label)}"</option>
                <option value="AB|FORMAL_SUPPORTING">"${escapeHtml(src.label)}" formally supports "${escapeHtml(dst.label)}"</option>
                <option value="BA|FORMAL_SUPPORTING">"${escapeHtml(dst.label)}" formally supports "${escapeHtml(src.label)}"</option>
                <option value="AB|COLLABORATIVE_ADJACENT">"${escapeHtml(src.label)}" and "${escapeHtml(dst.label)}" collaborate closely</option>
                <option value="AB|CO_SPONSOR">"${escapeHtml(src.label)}" and "${escapeHtml(dst.label)}" co-sponsor joint efforts</option>
              </select>
            </label>
          `;
        }
      };

      renderPairUi();

      document.getElementById("graph-edge-form").onsubmit = async (e) => {
        e.preventDefault();
        errEl.classList.add("hidden");
        const { src, dst, edgeCategory } = pairState;
        if (src.kind === dst.kind && src.id === dst.id) {
          errEl.textContent = "Please select two different items to connect.";
          errEl.classList.remove("hidden");
          return;
        }

        const base = {
          confidence: document.getElementById("gm-edge-conf").value,
          provenance_note: document.getElementById("gm-edge-prov").value.trim() || null,
        };

        try {
          if (edgeCategory === "effort_effort") {
            const [dir, mode] = document.getElementById("ge-ee-choice").value.split("|");
            const sId = dir === "BA" ? dst.id : src.id;
            const dId = dir === "BA" ? src.id : dst.id;
            await global.BijouApi.upsertEffortEffortEdge({
              ...base,
              source_effort_id: sId,
              target_effort_id: dId,
              blocking_mode: mode,
              dependency_degree: parseFloat(document.getElementById("ge-degree").value || "1"),
            });
          } else if (edgeCategory === "org_effort") {
            const pid = document.getElementById("ge-pool").value || null;
            const rid = document.getElementById("ge-req").value || null;
            const penaltyRaw = document.getElementById("ge-slip-penalty").value.trim();
            await global.BijouApi.upsertOrgEffortEdge(
              {
                ...base,
                org_id: src.id,
                effort_id: dst.id,
                resource_pool_id: pid,
                requirement_id: rid,
                resourcing_type: document.getElementById("ge-rtype").value,
                allocation_amount: parseFloat(document.getElementById("ge-amount").value || "0"),
                allocation_unit: document.getElementById("ge-unit").value.trim() || "UNITS",
                assigned_skill: document.getElementById("ge-skill").value.trim() || null,
                is_generic: !pid,
              },
              penaltyRaw !== "" ? parseInt(penaltyRaw, 10) : null
            );
          } else if (edgeCategory === "effort_interest") {
            await global.BijouApi.upsertEffortInterestEdge({
              ...base,
              effort_id: src.id,
              interest_id: dst.id,
              relation_type: document.getElementById("ge-ei-rel").value,
              impact_weight: parseFloat(document.getElementById("ge-ei-weight").value || "1"),
            });
          } else if (edgeCategory === "org_interest") {
            await global.BijouApi.upsertOrgInterestEdge({
              ...base,
              org_id: src.id,
              interest_id: dst.id,
              stance: document.getElementById("ge-oi-stance").value,
              priority_rank: parseFloat(document.getElementById("ge-oi-prio").value || "0.5"),
              allow_hierarchy_inheritance: Boolean(document.getElementById("ge-oi-inherit").checked),
            });
          } else if (edgeCategory === "interest_interest") {
            const [dir, rel] = document.getElementById("ge-ii-choice").value.split("|");
            const pId = dir === "BA" ? dst.id : src.id;
            const cId = dir === "BA" ? src.id : dst.id;
            await global.BijouApi.upsertInterestInterestEdge({
              ...base,
              parent_interest_id: pId,
              child_interest_id: cId,
              relation_type: rel,
            });
          } else {
            const [dir, rel] = document.getElementById("ge-oo-choice").value.split("|");
            const sId = dir === "BA" ? dst.id : src.id;
            const dId = dir === "BA" ? src.id : dst.id;
            await global.BijouApi.upsertOrgOrgEdge({
              ...base,
              source_org_id: sId,
              target_org_id: dId,
              relation_type: rel,
            });
          }

          this.notify?.(`Connected "${src.label}" and "${dst.label}".`, "success");
          this.closeEdgeModal();
          await this.onGraphMutated?.();
        } catch (err) {
          errEl.textContent = err.message;
          errEl.classList.remove("hidden");
        }
      };

      this.edgeModalBackdrop.classList.remove("hidden");
    }

    closeEdgeModal() {
      this.edgeModalBackdrop?.classList.add("hidden");
    }
  }

  global.BijouGraphEditor = GraphEditor;
})(window);

