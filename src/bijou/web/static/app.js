/**
 * Bijou Application Entry Point & Lens Coordinator.
 * Strictly offline-first, relative paths, zero CDN dependencies.
 */

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Setup Lens Navigation Switching
  const lensButtons = document.querySelectorAll(".lens-btn");
  const lensViews = document.querySelectorAll(".lens-view");

  function switchLens(targetId) {
    lensButtons.forEach(btn => {
      if (btn.dataset.lens === targetId) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }
    });

    lensViews.forEach(view => {
      if (view.id === targetId) {
        view.classList.add("active");
      } else {
        view.classList.remove("active");
      }
    });

    if (targetId === "briefing-one-pager") {
      ViewsManager.refreshBriefing();
    } else if (targetId === "focal-dashboard") {
      ViewsManager.refreshFocal();
    } else if (targetId === "tech-tree-canvas") {
      TechTreeManager.refresh();
    }
  }

  lensButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.lens;
      if (target) switchLens(target);
    });
  });

  // 2. Populate Dropdowns (Organizations & Things)
  try {
    const orgs = await BijouAPI.getOrganizations();
    const things = await BijouAPI.getThings();

    // Populate Briefing Org Dropdowns
    const subjectSelect = document.getElementById("briefing-subject-org");
    const perspSelect = document.getElementById("briefing-perspective-org");
    const techTreeOrgFilter = document.getElementById("tech-tree-org-filter");

    if (subjectSelect) {
      subjectSelect.innerHTML = orgs.map(o => `<option value="${o.id}">${o.name} (Echelon ${o.echelon_level})</option>`).join("");
    }
    if (perspSelect) {
      perspSelect.innerHTML = `<option value="">Self (Unfiltered Sovereign)</option>` +
        orgs.map(o => `<option value="${o.id}">${o.name} (Echelon ${o.echelon_level})</option>`).join("");
    }
    if (techTreeOrgFilter) {
      techTreeOrgFilter.innerHTML = `<option value="">All Organizations</option>` +
        orgs.map(o => `<option value="${o.id}">${o.name}</option>`).join("");
    }

    // Populate Focal Thing Dropdown & Tradeoff Candidates
    const focalThingSelect = document.getElementById("focal-thing-select");
    const tradeoffContainer = document.getElementById("tradeoff-candidates-container");

    if (focalThingSelect) {
      focalThingSelect.innerHTML = things.map(t => `<option value="${t.id}">${t.name} (${t.lifecycle})</option>`).join("");
    }

    if (tradeoffContainer) {
      tradeoffContainer.innerHTML = things.map(t => `
        <label style="display: flex; align-items: center; gap: 8px; font-size: 0.8rem; cursor: pointer;">
          <input type="checkbox" class="tradeoff-candidate-checkbox" value="${t.id}" />
          <span>${t.name} ($${(t.estimated_cost / 1000).toFixed(0)}k)</span>
        </label>
      `).join("");
    }
  } catch (err) {
    console.warn("Could not pre-populate entities (database may be empty):", err.message);
  }

  // 3. Initialize Subsystems
  await TechTreeManager.init();
  await ViewsManager.initBriefing();
  await ViewsManager.initFocal();
  await ViewsManager.initCrud();

  // 4. Omnibar Command Palette (Ctrl+K) (REC-018)
  const omnibarDialog = document.getElementById("omnibar-dialog");
  const omnibarInput = document.getElementById("omnibar-input");
  const omnibarResults = document.getElementById("omnibar-results");

  let omnibarItems = [];
  let selectedIndex = 0;

  async function refreshOmnibarData() {
    try {
      const [things, concerns] = await Promise.all([
        BijouAPI.getThings().catch(() => []),
        BijouAPI.getConcerns().catch(() => [])
      ]);

      omnibarItems = [
        // Lens actions
        { type: "lens", id: "tech-tree-canvas", title: "Lens 1: Strategic Tech Tree Canvas", category: "View" },
        { type: "lens", id: "briefing-one-pager", title: "Lens 2: Executive Perspective Briefing", category: "View" },
        { type: "lens", id: "focal-dashboard", title: "Lens 3: Thing Focal Dashboard & Trade-Offs", category: "View" },
        { type: "lens", id: "crud-studio", title: "Lens 4: Manifest Studio & Admin CRUD", category: "View" },
        // Things
        ...things.map(t => ({
          type: "thing",
          id: t.id,
          title: t.name,
          subtitle: `${t.lifecycle} • $${(t.estimated_cost / 1000).toFixed(0)}k`,
          category: "Thing",
          data: t
        })),
        // Concerns
        ...concerns.map(c => ({
          type: "concern",
          id: c.id,
          title: c.name,
          subtitle: `Priority ${c.priority} • Org: ${c.owner_org_id}`,
          category: "Concern",
          data: c
        }))
      ];
    } catch (e) {
      console.warn("Could not cache items for Omnibar:", e);
    }
  }

  function openOmnibar() {
    if (!omnibarDialog || !omnibarInput) return;
    refreshOmnibarData();
    if (typeof omnibarDialog.showModal === "function") {
      if (!omnibarDialog.open) omnibarDialog.showModal();
    } else {
      omnibarDialog.setAttribute("open", "");
    }
    omnibarInput.value = "";
    selectedIndex = 0;
    renderOmnibarMatches("");
    omnibarInput.focus();
  }

  function closeOmnibar() {
    if (!omnibarDialog) return;
    if (typeof omnibarDialog.close === "function") {
      omnibarDialog.close();
    } else {
      omnibarDialog.removeAttribute("open");
    }
  }

  function renderOmnibarMatches(query) {
    if (!omnibarResults) return;
    const q = query.trim().toLowerCase();
    const filtered = omnibarItems.filter(item => {
      if (!q) return true;
      return item.title.toLowerCase().includes(q) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(q)) ||
        (item.category && item.category.toLowerCase().includes(q)) ||
        item.id.toLowerCase().includes(q);
    }).slice(0, 20);

    if (filtered.length === 0) {
      omnibarResults.innerHTML = `<div style="padding: 16px; color: var(--text-dim); text-align: center; font-size: 0.85rem;">No matching entities or actions found.</div>`;
      return;
    }

    if (selectedIndex >= filtered.length) {
      selectedIndex = 0;
    }

    omnibarResults.innerHTML = filtered.map((item, idx) => `
      <div class="omnibar-item ${idx === selectedIndex ? 'selected' : ''}" data-idx="${idx}" data-type="${item.type}" data-id="${item.id}">
        <div>
          <div style="font-weight: 600; font-size: 0.88rem; color: var(--text-main);">${item.title}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">${item.subtitle || item.id}</div>
        </div>
        <span class="badge-pill" style="font-size: 0.65rem;">${item.category}</span>
      </div>
    `).join("");

    omnibarResults.querySelectorAll(".omnibar-item").forEach(el => {
      el.addEventListener("click", () => {
        const idx = parseInt(el.dataset.idx, 10);
        executeOmnibarAction(filtered[idx]);
      });
    });
  }

  function executeOmnibarAction(item) {
    if (!item) return;
    closeOmnibar();

    if (item.type === "lens") {
      switchLens(item.id);
    } else if (item.type === "thing") {
      switchLens("focal-dashboard");
      const focalSelect = document.getElementById("focal-thing-select");
      if (focalSelect) {
        focalSelect.value = item.id;
        ViewsManager.refreshFocal();
      }
    } else if (item.type === "concern") {
      switchLens("briefing-one-pager");
      const orgSelect = document.getElementById("briefing-subject-org");
      if (orgSelect && item.data && item.data.owner_org_id) {
        orgSelect.value = item.data.owner_org_id;
        ViewsManager.refreshBriefing();
      }
    }
  }

  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      openOmnibar();
    }
  });

  if (omnibarInput) {
    omnibarInput.addEventListener("input", (e) => {
      selectedIndex = 0;
      renderOmnibarMatches(e.target.value);
    });

    omnibarInput.addEventListener("keydown", (e) => {
      const items = omnibarResults ? omnibarResults.querySelectorAll(".omnibar-item") : [];
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (items.length > 0) {
          selectedIndex = (selectedIndex + 1) % items.length;
          renderOmnibarMatches(omnibarInput.value);
        }
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (items.length > 0) {
          selectedIndex = (selectedIndex - 1 + items.length) % items.length;
          renderOmnibarMatches(omnibarInput.value);
        }
      } else if (e.key === "Enter") {
        e.preventDefault();
        const selected = omnibarResults ? omnibarResults.querySelector(".omnibar-item.selected") : null;
        if (selected) {
          selected.click();
        }
      } else if (e.key === "Escape") {
        closeOmnibar();
      }
    });
  }

  if (omnibarDialog) {
    omnibarDialog.addEventListener("click", (e) => {
      if (e.target === omnibarDialog) {
        closeOmnibar();
      }
    });
  }
});
