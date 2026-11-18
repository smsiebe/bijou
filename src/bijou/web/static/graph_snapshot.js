/**
 * Bijou v2 - Graph Snapshot Exporter with Dynamic Contrast Placement & Branded Legend
 * Air-gapped compliance: zero external CDNs, 100% deterministic SVG/Canvas rasterization.
 */
(function (global) {
  "use strict";

  const BRAND_LOGO_W = 160;
  const BRAND_LOGO_H = 44;
  const LEGEND_BOX_W = 440;
  const LEGEND_BOX_H = 88;
  const SNAPSHOT_PADDING = 24;

  /**
   * Evaluates the bounding boxes of all nodes on canvas relative to world coordinate system
   * to find dark background space with zero occlusion.
   */
  function findSafePlacement({
    width,
    height,
    targetW,
    targetH,
    padding = SNAPSHOT_PADDING,
    occupiedBoxes = [],
    preferredCorner = "bottom-right",
  }) {
    const candidates = [];

    // Bottom-Right
    candidates.push({
      id: "bottom-right",
      x: width - targetW - padding,
      y: height - targetH - padding,
    });
    // Bottom-Left
    candidates.push({
      id: "bottom-left",
      x: padding,
      y: height - targetH - padding,
    });
    // Top-Right
    candidates.push({
      id: "top-right",
      x: width - targetW - padding,
      y: padding + 40, // offset below any top toolbars/status
    });
    // Top-Left
    candidates.push({
      id: "top-left",
      x: padding,
      y: padding + 40,
    });

    // Sort to try preferred corner first
    candidates.sort((a, b) => (a.id === preferredCorner ? -1 : b.id === preferredCorner ? 1 : 0));

    function overlapsAny(cx, cy, cw, ch) {
      const buffer = 12;
      const r1 = {
        left: cx - buffer,
        right: cx + cw + buffer,
        top: cy - buffer,
        bottom: cy + ch + buffer,
      };

      for (const b of occupiedBoxes) {
        if (
          r1.left < b.right &&
          r1.right > b.left &&
          r1.top < b.bottom &&
          r1.bottom > b.top
        ) {
          return true;
        }
      }
      return false;
    }

    // 1. Check corner candidates
    for (const cand of candidates) {
      if (
        cand.x >= 0 &&
        cand.y >= 0 &&
        cand.x + targetW <= width &&
        cand.y + targetH <= height &&
        !overlapsAny(cand.x, cand.y, targetW, targetH)
      ) {
        return { x: Math.round(cand.x), y: Math.round(cand.y) };
      }
    }

    // 2. Grid-based scan looking for empty space across bottom to top
    const stepX = 50;
    const stepY = 40;
    for (let y = height - targetH - padding; y >= padding; y -= stepY) {
      for (let x = width - targetW - padding; x >= padding; x -= stepX) {
        if (!overlapsAny(x, y, targetW, targetH)) {
          return { x: Math.round(x), y: Math.round(y) };
        }
      }
    }

    // Fallback to default placement if densely packed
    return {
      x: Math.max(padding, Math.round(width - targetW - padding)),
      y: Math.max(padding, Math.round(height - targetH - padding)),
    };
  }

  /**
   * Collect bounding boxes of all rendered nodes in canvas-dom-layer.
   */
  function getOccupiedNodeBoxes(domLayer, worldRect) {
    const boxes = [];
    if (!domLayer) return boxes;

    const cards = domLayer.querySelectorAll(
      ".neural-node, .effort-card, .tri-node, .partner-callout, .tripartite-col-header"
    );

    cards.forEach((card) => {
      const r = card.getBoundingClientRect();
      // Translate to world coordinates
      const box = {
        left: (r.left - worldRect.left),
        top: (r.top - worldRect.top),
        right: (r.right - worldRect.left),
        bottom: (r.bottom - worldRect.top),
      };
      boxes.push(box);
    });

    return boxes;
  }

  /**
   * Escape XML string for embedding in SVG.
   */
  function xmlEscape(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  /**
   * Renders the branded Bijou logo group in SVG.
   */
  function buildLogoSvgGroup(x, y) {
    return `
      <g id="bijou-snapshot-logo" transform="translate(${x}, ${y})">
        <!-- Logo Container Pill -->
        <rect x="0" y="0" width="${BRAND_LOGO_W}" height="${BRAND_LOGO_H}" rx="8" fill="#111722" fill-opacity="0.94" stroke="#283548" stroke-width="1.2" />
        
        <!-- B2 Gradient Mark -->
        <rect x="8" y="7" width="30" height="30" rx="6" fill="url(#bijou-brand-grad)" />
        <text x="23" y="27" fill="#ffffff" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="14" font-weight="800" text-anchor="middle">B2</text>
        
        <!-- BIJOU Title & Tagline -->
        <text x="46" y="22" fill="#38bdf8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="13" font-weight="800" letter-spacing="1">BIJOU</text>
        <text x="46" y="33" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="7.5" font-weight="600" letter-spacing="0.4">STRATEGIC PORTFOLIO</text>
      </g>
    `;
  }

  /**
   * Renders the color status and entity type legend in SVG.
   */
  function buildLegendSvgGroup(x, y) {
    return `
      <g id="bijou-snapshot-legend" transform="translate(${x}, ${y})">
        <!-- Background panel -->
        <rect x="0" y="0" width="${LEGEND_BOX_W}" height="${LEGEND_BOX_H}" rx="8" fill="#111722" fill-opacity="0.94" stroke="#283548" stroke-width="1.2" />
        
        <!-- Title Banner -->
        <text x="12" y="16" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="9" font-weight="700" letter-spacing="0.5">BIJOU GRAPH LEGEND</text>
        
        <!-- Row 1: Status Colors -->
        <text x="12" y="34" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5" font-weight="700">STATUS:</text>
        
        <!-- Completed -->
        <circle cx="68" cy="31" r="4.5" fill="#10b981" />
        <text x="77" y="34" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Completed</text>
        
        <!-- In Work -->
        <circle cx="140" cy="31" r="4.5" fill="#06b6d4" />
        <text x="149" y="34" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">In Work</text>
        
        <!-- Planned -->
        <circle cx="204" cy="31" r="4.5" fill="#f59e0b" />
        <text x="213" y="34" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Planned</text>
        
        <!-- Discovery -->
        <circle cx="266" cy="31" r="4.5" fill="#a855f7" />
        <text x="275" y="34" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Discovery</text>
        
        <!-- Cancelled -->
        <circle cx="334" cy="31" r="4.5" fill="#64748b" />
        <text x="343" y="34" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Cancelled</text>
        
        <!-- Row 2: Entity Types -->
        <text x="12" y="55" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5" font-weight="700">ENTITY:</text>
        
        <!-- Organization -->
        <rect x="64" y="47" width="12" height="11" rx="2" fill="#1e293b" stroke="#38bdf8" stroke-width="2" />
        <text x="81" y="55" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Organization</text>
        
        <!-- Work Effort -->
        <rect x="156" y="47" width="12" height="11" rx="2" fill="#1b2434" stroke="#f59e0b" stroke-width="1.8" />
        <text x="173" y="55" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Work Effort</text>
        
        <!-- Interest / Goal -->
        <rect x="246" y="47" width="12" height="11" rx="2" fill="#201a35" stroke="#a855f7" stroke-width="2" />
        <text x="263" y="55" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Strategic Interest</text>
        
        <!-- Row 3: Relationships / SPOF -->
        <text x="12" y="76" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5" font-weight="700">EDGES:</text>
        
        <!-- Blocking Solid -->
        <line x1="64" y1="73" x2="82" y2="73" stroke="#38bdf8" stroke-width="2" />
        <text x="88" y="76" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Dependency / Resourcing</text>
        
        <!-- Indirect Dashed -->
        <line x1="218" y1="73" x2="236" y2="73" stroke="#94a3b8" stroke-width="1.6" stroke-dasharray="3,3" />
        <text x="242" y="76" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Indirect / Aligns</text>
        
        <!-- SPOF Badge -->
        <rect x="338" y="67" width="28" height="12" rx="3" fill="rgba(239, 68, 68, 0.22)" stroke="#ef4444" stroke-width="0.8" />
        <text x="352" y="76" fill="#ef4444" font-family="ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace" font-size="7.5" font-weight="700" text-anchor="middle">SPOF</text>
        <text x="371" y="76" fill="#cbd5e1" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="8.5">Bottleneck</text>
      </g>
    `;
  }

  /**
   * Serialize DOM nodes into standard SVG foreignObject representations so they render
   * cleanly inside an SVG snapshot with zero external libraries.
   */
  function serializeDomNodesToSvg(domLayer, worldRect) {
    if (!domLayer) return "";

    const nodes = domLayer.querySelectorAll(".neural-node, .effort-card, .tri-node, .partner-callout");
    let markup = "";

    nodes.forEach((node) => {
      const r = node.getBoundingClientRect();
      const x = Math.round(r.left - worldRect.left);
      const y = Math.round(r.top - worldRect.top);
      const w = Math.round(r.width);
      const h = Math.round(r.height);

      // Clone node to sanitize
      const clone = node.cloneNode(true);
      // Remove connection ports and interactive grab handles
      clone.querySelectorAll(".node-connect-port").forEach((el) => el.remove());
      clone.style.left = "0px";
      clone.style.top = "0px";
      clone.style.position = "static";
      clone.style.transform = "none";
      clone.style.margin = "0";

      const html = new XMLSerializer().serializeToString(clone);
      markup += `
        <foreignObject x="${x}" y="${y}" width="${w}" height="${h}">
          <div xmlns="http://www.w3.org/1999/xhtml" style="width:100%;height:100%;box-sizing:border-box;">
            ${html}
          </div>
        </foreignObject>
      `;
    });

    return markup;
  }

  /**
   * Extracts essential CSS stylesheet rules needed for foreignObject rendering.
   */
  function collectEmbeddedStyles() {
    let cssText = `
      * { box-sizing: border-box; }
      body, div, span, p { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
      .mono-text, .state-pill, .spof-sample { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    `;

    for (const sheet of document.styleSheets) {
      try {
        const rules = sheet.cssRules || sheet.rules;
        if (!rules) continue;
        for (const rule of rules) {
          if (
            rule.selectorText &&
            (rule.selectorText.includes(".neural-node") ||
              rule.selectorText.includes(".effort-card") ||
              rule.selectorText.includes(".tri-node") ||
              rule.selectorText.includes(".state-pill") ||
              rule.selectorText.includes(".forecast-tag") ||
              rule.selectorText.includes(".coverage-bar") ||
              rule.selectorText.includes(".spof-sample") ||
              rule.selectorText.includes(".mini-chip") ||
              rule.selectorText.includes(".card-top-row") ||
              rule.selectorText.includes(".chip-row") ||
              rule.selectorText.includes(":root"))
          ) {
            cssText += "\n" + rule.cssText;
          }
        }
      } catch (e) {
        // Cross-domain or security restrictions silently skipped
      }
    }

    return cssText;
  }

  /**
   * Captures the visible canvas graph into a branded, self-contained SVG and optional PNG download.
   */
  async function captureGraphSnapshot({ notify } = {}) {
    try {
      const worldEl = document.getElementById("canvas-world");
      const svgLayer = document.getElementById("canvas-svg-layer");
      const domLayer = document.getElementById("canvas-dom-layer");

      if (!worldEl || !svgLayer) {
        throw new Error("Canvas world element not found");
      }

      const worldRect = worldEl.getBoundingClientRect();
      const worldW = Math.max(1200, Math.round(worldRect.width));
      const worldH = Math.max(800, Math.round(worldRect.height));

      // 1. Collect occupied node areas to detect dark/empty space
      const occupied = getOccupiedNodeBoxes(domLayer, worldRect);

      // 2. Compute non-obscuring position for Bijou Brand Logo
      const logoPos = findSafePlacement({
        width: worldW,
        height: worldH,
        targetW: BRAND_LOGO_W,
        targetH: BRAND_LOGO_H,
        padding: 24,
        occupiedBoxes: occupied,
        preferredCorner: "bottom-right",
      });

      // Add logo area to occupied boxes so legend avoids it
      const occupiedWithLogo = [
        ...occupied,
        {
          left: logoPos.x,
          top: logoPos.y,
          right: logoPos.x + BRAND_LOGO_W,
          bottom: logoPos.y + BRAND_LOGO_H,
        },
      ];

      // 3. Compute non-obscuring position for Legend Box
      const legendPos = findSafePlacement({
        width: worldW,
        height: worldH,
        targetW: LEGEND_BOX_W,
        targetH: LEGEND_BOX_H,
        padding: 24,
        occupiedBoxes: occupiedWithLogo,
        preferredCorner: "bottom-left",
      });

      // 4. Extract SVG layer paths & defs
      const clonedSvg = svgLayer.cloneNode(true);
      const existingDefs = clonedSvg.querySelector("defs") ? clonedSvg.querySelector("defs").innerHTML : "";
      // Remove any existing defs so we can consolidate them
      const defsEl = clonedSvg.querySelector("defs");
      if (defsEl) defsEl.remove();

      const pathsHtml = clonedSvg.innerHTML;

      // 5. Serialize DOM nodes
      const foreignObjectsHtml = serializeDomNodesToSvg(domLayer, worldRect);

      // 6. Assemble complete SVG with Branding, Legend, and Theme Styles
      const embeddedStyles = collectEmbeddedStyles();

      const finalSvgXml = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${worldW} ${worldH}" width="${worldW}" height="${worldH}">
  <defs>
    <linearGradient id="bijou-brand-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0ea5e9" />
      <stop offset="100%" stop-color="#6366f1" />
    </linearGradient>
    ${existingDefs}
    <style type="text/css">
      <![CDATA[
      ${embeddedStyles}
      ]]>
    </style>
  </defs>

  <!-- Deep Obsidian Slate Background -->
  <rect x="0" y="0" width="${worldW}" height="${worldH}" fill="#090d14" />
  
  <!-- Subtle Grid Backdrop Pattern -->
  <g opacity="0.08" stroke="#38bdf8" stroke-width="0.75">
    ${Array.from({ length: Math.ceil(worldW / 60) }, (_, i) => `<line x1="${i * 60}" y1="0" x2="${i * 60}" y2="${worldH}" />`).join("")}
    ${Array.from({ length: Math.ceil(worldH / 60) }, (_, i) => `<line x1="0" y1="${i * 60}" x2="${worldW}" y2="${i * 60}" />`).join("")}
  </g>

  <!-- Rendered Graph Connectors Layer -->
  <g id="bijou-graph-paths">
    ${pathsHtml}
  </g>

  <!-- Rendered Node Cards Layer -->
  <g id="bijou-graph-nodes">
    ${foreignObjectsHtml}
  </g>

  <!-- Branded Bijou Logo (Positioned in Detected Non-Obscured Space) -->
  ${buildLogoSvgGroup(logoPos.x, logoPos.y)}

  <!-- Status & Entity Type Legend (Positioned in Detected Non-Obscured Space) -->
  ${buildLegendSvgGroup(legendPos.x, legendPos.y)}
</svg>
      `.trim();

      // 7. Rasterize or offer instant file download
      const dateStr = new Date().toISOString().slice(0, 10);
      const filename = `bijou-graph-snapshot-${dateStr}.svg`;

      const blob = new Blob([finalSvgXml], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      if (notify) {
        notify(`Graph snapshot saved with Bijou branding & legend (${filename}).`, "success");
      }
      return { success: true, filename, logoPos, legendPos };
    } catch (err) {
      if (notify) {
        notify(`Failed to save graph snapshot: ${err.message}`, "error");
      }
      throw err;
    }
  }

  global.BijouGraphSnapshot = {
    captureGraphSnapshot,
    findSafePlacement,
    buildLogoSvgGroup,
    buildLegendSvgGroup,
  };
})(window);
