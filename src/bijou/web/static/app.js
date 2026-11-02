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
});
