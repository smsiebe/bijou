/* ==========================================================================
   Bijou v2 Offline Snapshot Bridge Adapter
   Enables zero-Python, zero-webserver, read-only browsing of exported snapshots.
   Intercepts BijouApi requests via window.__BIJOU_BRIDGE__ and serves data
   directly from window.__BIJOU_SNAPSHOT__.
   ========================================================================== */

(function (global) {
  "use strict";

  if (!global.__BIJOU_SNAPSHOT__) {
    // If not in offline snapshot mode, do nothing.
    return;
  }

  const snapshot = global.__BIJOU_SNAPSHOT__;
  global.__BIJOU_SNAPSHOT_ACTIVE__ = true;

  const CONFIDENCE_RANKS = {
    CONFIRMED: 3,
    ASSESSED: 2,
    UNCONFIRMED: 1,
  };

  function passesConfidence(conf, minConf) {
    if (!minConf) return true;
    const r = CONFIDENCE_RANKS[conf] || 1;
    const minR = CONFIDENCE_RANKS[minConf] || 1;
    return r >= minR;
  }

  function updateBadge() {
    if (typeof document === "undefined") return;
    const badge = document.getElementById("engine-health-badge");
    if (badge) {
      badge.textContent = "SNAPSHOT (OFFLINE)";
      badge.classList.remove("warn");
      badge.classList.add("snapshot");
      badge.title = "Viewing exported read-only Bijou snapshot (Zero Python runtime)";
    }
    if (document.body) {
      document.body.classList.add("bijou-snapshot-mode");
    }
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", updateBadge);
    } else {
      updateBadge();
    }
  }

  function addDaysIso(isoDate, days) {
    if (!isoDate) return null;
    const d = new Date(`${isoDate}T00:00:00Z`);
    if (Number.isNaN(d.getTime())) return isoDate;
    d.setUTCDate(d.getUTCDate() + Number(days || 0));
    return d.toISOString().slice(0, 10);
  }

  function diffDaysIso(a, b) {
    if (!a || !b) return 0;
    const da = new Date(`${a}T00:00:00Z`);
    const db = new Date(`${b}T00:00:00Z`);
    if (Number.isNaN(da.getTime()) || Number.isNaN(db.getTime())) return 0;
    return Math.round((da.getTime() - db.getTime()) / 86400000);
  }

  function getInterestDescendants(interestId, interestEdges) {
    const childrenMap = new Map();
    (interestEdges || []).forEach((edge) => {
      if (!childrenMap.has(edge.parent_interest_id)) childrenMap.set(edge.parent_interest_id, []);
      childrenMap.get(edge.parent_interest_id).push(edge.child_interest_id);
    });
    const visited = new Set([interestId]);
    const queue = [interestId];
    while (queue.length > 0) {
      const curr = queue.shift();
      (childrenMap.get(curr) || []).forEach((child) => {
        if (!visited.has(child)) {
          visited.add(child);
          queue.push(child);
        }
      });
    }
    return visited;
  }

  function computeEffectivePriorities(orgOrgEdges, orgInterestEdges, enableInheritance) {
    const childrenMap = new Map();
    (orgOrgEdges || []).forEach((oo) => {
      if (oo.relation_type === "HIERARCHICAL_PARENT") {
        if (!childrenMap.has(oo.source_org_id)) childrenMap.set(oo.source_org_id, []);
        childrenMap.get(oo.source_org_id).push(oo.target_org_id);
      }
    });

    const directMap = new Map();
    (orgInterestEdges || []).forEach((oi) => {
      directMap.set(`${oi.org_id}::${oi.interest_id}`, oi);
    });

    const effective = new Map();
    directMap.forEach((oi, key) => {
      effective.set(key, {
        org_id: oi.org_id,
        interest_id: oi.interest_id,
        direct_priority: oi.priority_rank,
        effective_priority: oi.priority_rank,
        inherited_from_org_id: null,
      });
    });

    if (enableInheritance) {
      directMap.forEach((oi) => {
        if (oi.allow_hierarchy_inheritance === false) return;
        const queue = [[oi.org_id, oi.priority_rank, oi.org_id]];
        const visited = new Set([oi.org_id]);
        while (queue.length > 0) {
          const [currOid, currPrio, rootOrigin] = queue.shift();
          (childrenMap.get(currOid) || []).forEach((childOid) => {
            if (visited.has(childOid)) return;
            visited.add(childOid);
            const inheritedPrio = Math.round(currPrio * 0.9 * 1000) / 1000;
            const cKey = `${childOid}::${oi.interest_id}`;
            const existing = effective.get(cKey);
            if (!existing || inheritedPrio > existing.effective_priority) {
              effective.set(cKey, {
                org_id: childOid,
                interest_id: oi.interest_id,
                direct_priority: existing ? existing.direct_priority : null,
                effective_priority: inheritedPrio,
                inherited_from_org_id: rootOrigin,
              });
            }
            queue.push([childOid, inheritedPrio, rootOrigin]);
          });
        }
      });
    }

    return Array.from(effective.values()).sort((a, b) => {
      if (a.org_id !== b.org_id) return a.org_id.localeCompare(b.org_id);
      return b.effective_priority - a.effective_priority;
    });
  }

  function applyPriorityInheritanceFilter(priorities, includeInheritance) {
    if (includeInheritance) return priorities || [];
    return (priorities || [])
      .filter((p) => p.direct_priority !== null && p.direct_priority !== undefined)
      .map((p) => ({
        ...p,
        effective_priority: p.direct_priority,
        inherited_from_org_id: null,
      }))
      .sort((a, b) => b.effective_priority - a.effective_priority);
  }

  function isHierarchyRollupEnabled(params) {
    if (!params) return true;
    if (params.include_hierarchy_priorities === false || params.include_hierarchy_priorities === "false") {
      return false;
    }
    if (params.include_hierarchy_inheritance === false || params.include_hierarchy_inheritance === "false") {
      return false;
    }
    return true;
  }

  function resolveRequestPerspective(headers) {
    const h = headers || {};
    const mode = h["X-Bijou-Access-Mode"] || h["x-bijou-access-mode"];
    const orgId = h["X-Bijou-Active-Org"] || h["x-bijou-active-org"] || null;
    const basePersp = snapshot.perspective || {
      mode: "GLOBAL_ANALYST",
      active_org_id: null,
      managed_organizations: (snapshot.organizations || []).filter((o) => o.is_managed),
    };
    if (!mode) return basePersp;
    return {
      ...basePersp,
      mode,
      active_org_id: mode === "MANAGED_ORG_OWNER" ? orgId : null,
    };
  }

  function filterCapabilityTree(tree, params) {
    if (!tree) return tree;
    const minConf = params?.min_confidence;
    const orgFilter = params?.org_filter;
    const includeHier = isHierarchyRollupEnabled(params);

    let nodes = tree.nodes || [];
    let effortEdges = tree.effort_edges || [];
    let orgOrgEdges = tree.org_org_edges || [];
    let orgIntrEdges = tree.org_interest_edges || [];
    let intrIntrEdges = tree.interest_interest_edges || [];
    let orgEffortEdges = tree.org_effort_edges || [];
    let effortIntrEdges = tree.effort_interest_edges || [];

    if (minConf) {
      effortEdges = effortEdges.filter((e) => passesConfidence(e.confidence, minConf));
      orgOrgEdges = orgOrgEdges.filter((e) => passesConfidence(e.confidence, minConf));
      orgIntrEdges = orgIntrEdges.filter((e) => passesConfidence(e.confidence, minConf));
      intrIntrEdges = intrIntrEdges.filter((e) => passesConfidence(e.confidence, minConf));
      orgEffortEdges = orgEffortEdges.filter((e) => passesConfidence(e.confidence, minConf));
      effortIntrEdges = effortIntrEdges.filter((e) => passesConfidence(e.confidence, minConf));
    }

    if (orgFilter) {
      const allowedEffortIds = new Set(
        nodes
          .filter(
            (n) =>
              (n.funding_org_ids || []).includes(orgFilter) ||
              (n.indirect_beneficiary_org_ids || []).includes(orgFilter)
          )
          .map((n) => n.effort.id)
      );

      nodes = nodes.filter((n) => allowedEffortIds.has(n.effort.id));
      effortEdges = effortEdges.filter(
        (e) => allowedEffortIds.has(e.source_effort_id) && allowedEffortIds.has(e.target_effort_id)
      );
    }

    const effectivePriorities = computeEffectivePriorities(orgOrgEdges, orgIntrEdges, includeHier);

    return {
      ...tree,
      nodes,
      effort_edges: effortEdges,
      org_org_edges: orgOrgEdges,
      org_interest_edges: orgIntrEdges,
      interest_interest_edges: intrIntrEdges,
      org_effort_edges: orgEffortEdges,
      effort_interest_edges: effortIntrEdges,
      effective_priorities: effectivePriorities,
    };
  }

  function filterTripartiteFlow(tri, params) {
    if (!tri) return tri;
    const minConf = params?.min_confidence;
    const filteredTree = filterCapabilityTree(tri.capability_tree, params);

    let indirectBenefits = tri.indirect_benefits || [];
    if (minConf) {
      indirectBenefits = indirectBenefits.filter((b) => passesConfidence(b.confidence, minConf));
    }

    return {
      ...tri,
      capability_tree: filteredTree,
      indirect_benefits: indirectBenefits,
    };
  }

  function computePoolBalancesJs(pools, efforts, orgEffortEdges, effortInterestEdges, interestEdges) {
    const effortNames = new Map((efforts || []).map((e) => [e.id, e.name]));
    const effortInterests = new Map();
    (effortInterestEdges || []).forEach((ei) => {
      if (!effortInterests.has(ei.effort_id)) effortInterests.set(ei.effort_id, new Set());
      effortInterests.get(ei.effort_id).add(ei.interest_id);
    });

    return (pools || []).map((pool) => {
      const eligible = new Set();
      (pool.restricted_interest_ids || []).forEach((rootId) => {
        getInterestDescendants(rootId, interestEdges).forEach((d) => eligible.add(d));
      });

      let allocated = 0;
      const violations = [];
      (orgEffortEdges || []).forEach((oe) => {
        if (oe.resource_pool_id === pool.id) {
          allocated += Number(oe.allocation_amount || 0);
          if ((pool.restricted_interest_ids || []).length > 0) {
            const served = effortInterests.get(oe.effort_id) || new Set();
            let intersects = false;
            served.forEach((iid) => {
              if (eligible.has(iid)) intersects = true;
            });
            if (!intersects) {
              const effLabel = effortNames.get(oe.effort_id) || oe.effort_id;
              const servedList = served.size > 0 ? JSON.stringify(Array.from(served).sort()) : "none";
              violations.push(
                `Pool '${pool.name}' earmarked for ${JSON.stringify(pool.restricted_interest_ids)} cannot fund Effort '${effLabel}' (serves ${servedList})`
              );
            }
          }
        }
      });

      return {
        pool,
        allocated_amount: allocated,
        remaining_amount: Number(pool.capacity || 0) - allocated,
        eligible_interest_ids: Array.from(eligible).sort(),
        color_of_money_violations: violations,
      };
    });
  }

  function computeInterestCoverageMap(nodes, interests, effortInterestEdges) {
    const nodeMap = new Map((nodes || []).map((n) => [n.effort.id, n]));
    const scores = new Map((interests || []).map((i) => [i.id, []]));
    (effortInterestEdges || []).forEach((ei) => {
      if (scores.has(ei.interest_id) && nodeMap.has(ei.effort_id)) {
        const n = nodeMap.get(ei.effort_id);
        let health = Math.max(0.1, Number(n.resourcing_coverage_ratio || 0)) * Number(ei.impact_weight ?? 1);
        if (n.effort.state === "CANCELLED") health = 0.0;
        scores.get(ei.interest_id).push(health);
      }
    });
    const out = {};
    scores.forEach((vals, iid) => {
      if (vals.length === 0) {
        out[iid] = 0.0;
      } else {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        out[iid] = Math.round(Math.min(1.0, avg) * 1000) / 1000;
      }
    });
    return out;
  }

  function simulateTransientBoe(request, queryParams) {
    const manifest = snapshot.manifest || {};
    const baseTree = snapshot.views?.capability_tree || {};
    const baseNodes = baseTree.nodes || [];
    const baseNodesById = new Map(baseNodes.map((n) => [n.effort.id, n]));

    const efforts = manifest.efforts || baseNodes.map((n) => n.effort);
    const effortsById = new Map(efforts.map((e) => [e.id, e]));
    const pools = manifest.resource_pools || baseTree.resource_pools || [];
    const poolsById = new Map(pools.map((p) => [p.id, p]));
    const effortEdges = manifest.effort_effort_edges || baseTree.effort_edges || [];
    const baseOrgEffortEdges = manifest.org_effort_edges || baseTree.org_effort_edges || [];
    const effortInterestEdges = manifest.effort_interest_edges || baseTree.effort_interest_edges || [];
    const interestEdges = manifest.interest_interest_edges || baseTree.interest_interest_edges || [];
    const interests = manifest.interests || baseTree.interests || [];

    const asOfDate =
      queryParams?.as_of_date ||
      baseTree.as_of_date ||
      snapshot.meta?.as_of_date ||
      new Date().toISOString().slice(0, 10);

    const req = request || {};
    const slips = req.effort_slips || {};
    const toggles = req.toggle_mitigators || {};
    const allocs = req.add_allocations || [];
    const removeSet = new Set(req.remove_edge_ids || []);
    const cancels = new Set(req.cancelled_effort_ids || []);

    let simOrgEffort = baseOrgEffortEdges.filter((oe) => !removeSet.has(oe.id));
    const skillMismatchWarnings = [];
    const newRisks = [];
    const extraRisksByEffort = new Map();
    let costDelta = 0;

    // 1. Mitigator cost delta
    efforts.forEach((effort) => {
      (effort.mitigators || []).forEach((mit) => {
        const baseEx = Boolean(mit.is_exercised);
        const simEx = mit.id in toggles ? Boolean(toggles[mit.id]) : baseEx;
        if (simEx !== baseEx) {
          const mCost = (mit.additional_requirements || []).reduce((acc, r) => {
            return (
              acc +
              Number(
                r.estimated_cost_usd ?? (String(r.unit || "").toUpperCase() === "USD" ? r.quantity : 0) ?? 0
              )
            );
          }, 0);
          costDelta += simEx ? mCost : -mCost;
        }
      });
    });

    // 2. Evaluate staged allocations & skill mismatches
    allocs.forEach((alloc, idx) => {
      const targetEff = effortsById.get(alloc.effort_id);
      if (!targetEff) return;

      let assignedSkill = alloc.assigned_skill ?? null;
      if (assignedSkill === null && alloc.pool_id && poolsById.has(alloc.pool_id)) {
        assignedSkill = poolsById.get(alloc.pool_id).skill_tag ?? null;
      }

      let matchedReq = null;
      if (alloc.requirement_id) {
        const allReqs = [...(targetEff.resource_requirements || [])];
        (targetEff.mitigators || []).forEach((m) => {
          allReqs.push(...(m.additional_requirements || []));
        });
        matchedReq = allReqs.find((r) => r.id === alloc.requirement_id) || null;
      }

      if (!alloc.is_generic && matchedReq && matchedReq.required_skill && assignedSkill) {
        if (matchedReq.required_skill.trim().toLowerCase() !== assignedSkill.trim().toLowerCase()) {
          const suggestedDays =
            alloc.human_slip_penalty_days !== null && alloc.human_slip_penalty_days !== undefined
              ? Number(alloc.human_slip_penalty_days)
              : 30;
          const risk = {
            id: `risk-mismatch-sim-${idx}`,
            effort_id: alloc.effort_id,
            title: `Skill Mismatch: ${assignedSkill} assigned to ${matchedReq.required_skill}`,
            description: `Non-transferable skill mismatch on requirement '${matchedReq.label}'. Expected '${matchedReq.required_skill}', received '${assignedSkill}'.`,
            severity: suggestedDays >= 21 ? "HIGH" : "MEDIUM",
            likelihood: 0.75,
            potential_slip_days: suggestedDays,
            is_skill_mismatch_risk: true,
            status: "ACTIVE",
            related_requirement_id: matchedReq.id,
          };
          newRisks.push(risk);
          if (!extraRisksByEffort.has(alloc.effort_id)) extraRisksByEffort.set(alloc.effort_id, []);
          extraRisksByEffort.get(alloc.effort_id).push(risk);
          skillMismatchWarnings.push({
            effort_id: alloc.effort_id,
            requirement_id: matchedReq.id,
            required_skill: matchedReq.required_skill,
            assigned_skill: assignedSkill,
            message: `Skill mismatch warning: assigned '${assignedSkill}' does not match required '${matchedReq.required_skill}' on '${matchedReq.label}'. Risk registered.`,
            suggested_slip_penalty_days: suggestedDays,
            generated_risk: risk,
          });
        }
      }

      if (alloc.resourcing_type === "MONEY" || String(alloc.unit || "").toUpperCase() === "USD") {
        costDelta += Number(alloc.amount || 0);
      }

      simOrgEffort.push({
        id: `sim-alloc-${idx}`,
        org_id: alloc.org_id,
        effort_id: alloc.effort_id,
        resourcing_type: alloc.resourcing_type,
        resource_pool_id: alloc.pool_id || null,
        requirement_id: alloc.requirement_id || null,
        allocation_amount: Number(alloc.amount || 0),
        allocation_unit: alloc.unit || "UNITS",
        assigned_skill: assignedSkill,
        is_generic: Boolean(alloc.is_generic),
        confidence: "CONFIRMED",
        provenance_note: "Simulated in Bill of Efforts workbench",
      });
    });

    // 3. Subtract removed edges monetary contribution
    baseOrgEffortEdges.forEach((oe) => {
      if (
        removeSet.has(oe.id) &&
        (oe.resourcing_type === "MONEY" || String(oe.allocation_unit || "").toUpperCase() === "USD")
      ) {
        costDelta -= Number(oe.allocation_amount || 0);
      }
    });

    // 4. Topological order & dependency lookup
    const inDegree = new Map();
    const blockingPreds = new Map();
    const informingPreds = new Map();
    const adjOut = new Map();
    efforts.forEach((e) => {
      inDegree.set(e.id, 0);
      blockingPreds.set(e.id, []);
      informingPreds.set(e.id, []);
      adjOut.set(e.id, []);
    });

    effortEdges.forEach((edge) => {
      if (!effortsById.has(edge.source_effort_id) || !effortsById.has(edge.target_effort_id)) return;
      adjOut.get(edge.source_effort_id).push(edge.target_effort_id);
      inDegree.set(edge.target_effort_id, (inDegree.get(edge.target_effort_id) || 0) + 1);
      if (edge.blocking_mode === "BLOCKING") {
        blockingPreds.get(edge.target_effort_id).push(edge.source_effort_id);
      } else {
        informingPreds.get(edge.target_effort_id).push(edge.source_effort_id);
      }
    });

    const topoQueue = [];
    inDegree.forEach((deg, eid) => {
      if (deg === 0) topoQueue.push(eid);
    });
    const topoOrder = [];
    while (topoQueue.length > 0) {
      const curr = topoQueue.shift();
      topoOrder.push(curr);
      (adjOut.get(curr) || []).forEach((nxt) => {
        const d = inDegree.get(nxt) - 1;
        inDegree.set(nxt, d);
        if (d === 0) topoQueue.push(nxt);
      });
    }
    // Append any remaining IDs cleanly in base order
    baseNodes.forEach((n) => {
      if (!topoOrder.includes(n.effort.id)) topoOrder.push(n.effort.id);
    });

    // 5. Forward forecast pass
    const resolvedMap = new Map();
    topoOrder.forEach((eid) => {
      const effort = effortsById.get(eid);
      const baseNode = baseNodesById.get(eid);
      if (!effort) return;

      const effectiveState = cancels.has(eid) ? "CANCELLED" : effort.state;
      const combinedRisks = [...(effort.risks || []), ...(extraRisksByEffort.get(eid) || [])];
      const activeRisks = combinedRisks.filter((r) => r.status === "ACTIVE");

      const exercisedMits = [];
      const unexercisedMits = [];
      const effectiveReqList = [...(effort.resource_requirements || [])];

      (effort.mitigators || []).forEach((m) => {
        const isEx = m.id in toggles ? Boolean(toggles[m.id]) : Boolean(m.is_exercised);
        if (isEx) {
          exercisedMits.push(m);
          effectiveReqList.push(...(m.additional_requirements || []));
        } else {
          unexercisedMits.push(m);
        }
      });

      const targetedReduction = new Map();
      const targetedFactor = new Map();
      let untargetedSlipReduction = 0;
      exercisedMits.forEach((m) => {
        if (m.risk_id) {
          targetedReduction.set(m.risk_id, (targetedReduction.get(m.risk_id) || 0) + (m.slip_reduction_days || 0));
          targetedFactor.set(
            m.risk_id,
            Math.min(1.0, (targetedFactor.get(m.risk_id) || 0) + (m.risk_reduction_factor || 0))
          );
        } else {
          untargetedSlipReduction += Number(m.slip_reduction_days || 0);
        }
      });

      let residualRiskSlip = 0;
      activeRisks.forEach((r) => {
        let redDays = targetedReduction.get(r.id) || 0;
        if (redDays === 0 && targetedFactor.has(r.id)) {
          redDays = Math.round(Number(r.potential_slip_days || 0) * targetedFactor.get(r.id));
        }
        residualRiskSlip += Math.max(0, Number(r.potential_slip_days || 0) - redDays);
      });

      const externalSlip = Number(slips[eid] || 0);
      const netSlipDays = Math.max(0, residualRiskSlip - untargetedSlipReduction + externalSlip);

      const effortOrgEdges = simOrgEffort.filter((oe) => oe.effort_id === eid);
      const reqCount = effectiveReqList.length;
      const totalEstCost = effectiveReqList.reduce((acc, r) => {
        return acc + Number(r.estimated_cost_usd ?? (String(r.unit || "").toUpperCase() === "USD" ? r.quantity : 0) ?? 0);
      }, 0);

      let coverageRatio = 0;
      if (reqCount === 0) {
        coverageRatio = effortOrgEdges.length > 0 ? 1.0 : 0.0;
      } else {
        const coveredReqIds = new Set(effortOrgEdges.filter((oe) => oe.requirement_id).map((oe) => oe.requirement_id));
        let matched = 0;
        effectiveReqList.forEach((r) => {
          if (
            coveredReqIds.has(r.id) ||
            effortOrgEdges.some((oe) => oe.resourcing_type === r.category && Number(oe.allocation_amount || 0) >= Number(r.quantity || 0))
          ) {
            matched += 1;
          }
        });
        coverageRatio = Math.round(Math.min(1.0, matched / reqCount) * 1000) / 1000;
      }

      const fundingOrgs = Array.from(new Set(effortOrgEdges.map((oe) => oe.org_id)));
      const orgAllocTotals = new Map();
      effortOrgEdges.forEach((oe) => {
        orgAllocTotals.set(oe.org_id, (orgAllocTotals.get(oe.org_id) || 0) + Number(oe.allocation_amount || 0));
      });
      let primaryOrg = baseNode?.primary_org_id || null;
      if (orgAllocTotals.size > 0) {
        primaryOrg = Array.from(orgAllocTotals.entries()).sort((a, b) => b[1] - a[1])[0][0];
      } else if (fundingOrgs.length > 0) {
        primaryOrg = fundingOrgs[0];
      }

      const bPreds = blockingPreds.get(eid) || [];
      let horizonStatus;
      let fStart = null;
      let fEnd = null;
      let relOffset = null;
      let blockedUnknown = [];

      if (effectiveState === "CANCELLED") {
        horizonStatus = "CANCELLED";
      } else if (effectiveState === "COMPLETED") {
        horizonStatus = "COMPLETED_HISTORICAL";
        fStart = effort.start_date || null;
        fEnd =
          effort.end_date ||
          (effort.start_date && effort.estimated_duration_days
            ? addDaysIso(effort.start_date, effort.estimated_duration_days)
            : null);
      } else if (effectiveState === "IN_WORK") {
        if (effort.end_date != null) {
          fStart = effort.start_date || null;
          fEnd = addDaysIso(effort.end_date, netSlipDays);
          horizonStatus = "EXPLICIT_SCHEDULE";
        } else if (effort.start_date != null && effort.estimated_duration_days != null) {
          fStart = effort.start_date;
          fEnd = addDaysIso(effort.start_date, Number(effort.estimated_duration_days) + netSlipDays);
          horizonStatus = "EXPLICIT_SCHEDULE";
        } else if (
          effort.estimated_duration_days != null &&
          !bPreds.some((p) =>
            ["OPEN_ENDED_ACTIVE", "RELATIVE_TO_DEPENDENCY", "UNSCHEDULED_PLAN"].includes(
              resolvedMap.get(p)?.horizon_status
            )
          )
        ) {
          fStart = effort.start_date || asOfDate;
          fEnd = addDaysIso(fStart, Number(effort.estimated_duration_days) + netSlipDays);
          horizonStatus = "EXPLICIT_SCHEDULE";
        } else {
          fStart = effort.start_date || null;
          fEnd = null;
          horizonStatus = "OPEN_ENDED_ACTIVE";
          if (effort.estimated_duration_days != null) {
            relOffset = Number(effort.estimated_duration_days) + netSlipDays;
          }
        }
      } else {
        const incompleteBlocking = bPreds.filter(
          (p) => resolvedMap.get(p)?.horizon_status !== "COMPLETED_HISTORICAL"
        );
        const unknownBlocking = incompleteBlocking.filter((p) => !resolvedMap.get(p)?.forecast_end);

        if (unknownBlocking.length > 0) {
          horizonStatus = "RELATIVE_TO_DEPENDENCY";
          blockedUnknown = unknownBlocking;
          const upstreamMaxRel = Math.max(
            0,
            ...unknownBlocking.map((p) => Number(resolvedMap.get(p)?.relative_offset_days || 0))
          );
          const ownDur = effort.estimated_duration_days ? Number(effort.estimated_duration_days) + netSlipDays : 0;
          relOffset = upstreamMaxRel > 0 || ownDur > 0 ? upstreamMaxRel + ownDur : null;
        } else if (incompleteBlocking.length > 0) {
          const predEnds = incompleteBlocking
            .map((p) => resolvedMap.get(p)?.forecast_end)
            .filter(Boolean)
            .sort();
          const maxPredEnd = predEnds[predEnds.length - 1];
          const earliestStart =
            effort.start_date && effort.start_date > maxPredEnd ? effort.start_date : maxPredEnd;
          fStart = earliestStart;

          if (effort.end_date != null) {
            const shift = effort.start_date ? Math.max(0, diffDaysIso(earliestStart, effort.start_date)) : 0;
            fEnd = addDaysIso(effort.end_date, shift + netSlipDays);
            horizonStatus = "EXPLICIT_SCHEDULE";
          } else if (effort.estimated_duration_days != null) {
            fEnd = addDaysIso(earliestStart, Number(effort.estimated_duration_days) + netSlipDays);
            horizonStatus = "EXPLICIT_SCHEDULE";
          } else {
            horizonStatus = "RELATIVE_TO_DEPENDENCY";
            fEnd = null;
            blockedUnknown = incompleteBlocking;
          }
        } else {
          if (effort.end_date != null) {
            fStart = effort.start_date || null;
            fEnd = addDaysIso(effort.end_date, netSlipDays);
            horizonStatus = "EXPLICIT_SCHEDULE";
          } else if (effort.estimated_duration_days != null) {
            fStart = effort.start_date || asOfDate;
            fEnd = addDaysIso(fStart, Number(effort.estimated_duration_days) + netSlipDays);
            horizonStatus = "EXPLICIT_SCHEDULE";
          } else {
            fStart = effort.start_date || null;
            fEnd = null;
            horizonStatus = "UNSCHEDULED_PLAN";
          }
        }
      }

      resolvedMap.set(eid, {
        ...(baseNode || {}),
        effort: {
          ...effort,
          state: effectiveState,
        },
        horizon_status: horizonStatus,
        forecast_start: fStart,
        forecast_end: fEnd,
        relative_offset_days: relOffset,
        blocked_by_effort_ids: blockedUnknown,
        funding_org_ids: fundingOrgs,
        primary_org_id: primaryOrg,
        total_estimated_cost_usd: Math.round(totalEstCost * 100) / 100,
        resourcing_coverage_ratio: coverageRatio,
        active_risk_count: activeRisks.length,
        exercised_mitigator_count: exercisedMits.length,
        unexercised_mitigator_count: unexercisedMits.length,
      });
    });

    const projectedNodes = topoOrder.map((eid) => resolvedMap.get(eid)).filter(Boolean);
    const poolBalances = computePoolBalancesJs(
      pools,
      efforts,
      simOrgEffort,
      effortInterestEdges,
      interestEdges
    );

    const impactedIds = [];
    projectedNodes.forEach((pNode) => {
      const bNode = baseNodesById.get(pNode.effort.id);
      if (!bNode) {
        impactedIds.push(pNode.effort.id);
        return;
      }
      if (
        pNode.horizon_status !== bNode.horizon_status ||
        pNode.forecast_end !== bNode.forecast_end ||
        pNode.relative_offset_days !== bNode.relative_offset_days ||
        pNode.resourcing_coverage_ratio !== bNode.resourcing_coverage_ratio ||
        pNode.active_risk_count !== bNode.active_risk_count ||
        pNode.exercised_mitigator_count !== bNode.exercised_mitigator_count ||
        cancels.has(pNode.effort.id)
      ) {
        impactedIds.push(pNode.effort.id);
      }
    });

    const baseIntCov = computeInterestCoverageMap(baseNodes, interests, effortInterestEdges);
    const simIntCov = computeInterestCoverageMap(projectedNodes, interests, effortInterestEdges);
    const coverageDeltas = {};
    Object.keys(simIntCov).forEach((iid) => {
      coverageDeltas[iid] = Math.round(((simIntCov[iid] || 0) - (baseIntCov[iid] || 0)) * 1000) / 1000;
    });

    const baseRiskTotal = baseNodes.reduce((acc, n) => acc + Number(n.active_risk_count || 0), 0);
    const simRiskTotal = projectedNodes.reduce((acc, n) => acc + Number(n.active_risk_count || 0), 0);

    return {
      projected_tree: {
        ...baseTree,
        nodes: projectedNodes,
        org_effort_edges: simOrgEffort,
      },
      pool_balances: poolBalances,
      skill_mismatch_warnings: skillMismatchWarnings,
      newly_registered_risks: newRisks,
      impacted_effort_ids: impactedIds,
      interest_coverage_deltas: coverageDeltas,
      total_cost_delta: Math.round(costDelta * 100) / 100,
      net_risk_count_delta: simRiskTotal - baseRiskTotal,
    };
  }

  // Register bridge implementation into window.__BIJOU_BRIDGE__
  global.__BIJOU_BRIDGE__ = async function (method, url, headers, body) {
    const m = (method || "GET").toUpperCase();
    const [pathPart, queryPart] = (url || "").split("?");
    const path = pathPart.startsWith("/") ? pathPart : "/" + pathPart;
    const params = queryPart ? Object.fromEntries(new URLSearchParams(queryPart).entries()) : {};
    const persp = resolveRequestPerspective(headers);
    const includeHier = isHierarchyRollupEnabled(params);

    // 1. Health & Perspective
    if (path === "/api/v1/health") {
      return {
        ok: true,
        status: 200,
        data: snapshot.health || { status: "healthy", engine: "bijou-v2-snapshot" },
      };
    }

    if (path === "/api/v1/perspective" && m === "GET") {
      return {
        ok: true,
        status: 200,
        data: persp,
      };
    }

    if (path === "/api/v1/snapshot/export") {
      return {
        ok: false,
        status: 403,
        data: { detail: "Read-Only Snapshot: Already viewing an exported offline snapshot archive." },
      };
    }

    // 2. Primary Views
    if (path === "/api/v1/views/capability-tree" && m === "GET") {
      const tree = filterCapabilityTree(snapshot.views?.capability_tree, params);
      return { ok: true, status: 200, data: tree };
    }

    if (path === "/api/v1/views/tripartite-flow" && m === "GET") {
      const tri = filterTripartiteFlow(snapshot.views?.tripartite_flow, params);
      return { ok: true, status: 200, data: tri };
    }

    // 3. Focal Dashboards
    const effFocalMatch = path.match(/^\/api\/v1\/views\/efforts\/([^/]+)\/focal$/);
    if (effFocalMatch && m === "GET") {
      const id = decodeURIComponent(effFocalMatch[1]);
      const data = snapshot.focal?.efforts?.[id];
      if (!data) {
        return { ok: false, status: 404, data: { detail: `Effort '${id}' not found in snapshot` } };
      }
      return { ok: true, status: 200, data };
    }

    const orgFocalMatch = path.match(/^\/api\/v1\/views\/organizations\/([^/]+)\/focal$/);
    if (orgFocalMatch && m === "GET") {
      const id = decodeURIComponent(orgFocalMatch[1]);
      const data = snapshot.focal?.organizations?.[id];
      if (!data) {
        return { ok: false, status: 404, data: { detail: `Organization '${id}' not found in snapshot` } };
      }
      return {
        ok: true,
        status: 200,
        data: {
          ...data,
          org_interest_priorities: applyPriorityInheritanceFilter(data.org_interest_priorities, includeHier),
        },
      };
    }

    const intrFocalMatch = path.match(/^\/api\/v1\/views\/interests\/([^/]+)\/focal$/);
    if (intrFocalMatch && m === "GET") {
      const id = decodeURIComponent(intrFocalMatch[1]);
      const data = snapshot.focal?.interests?.[id];
      if (!data) {
        return { ok: false, status: 404, data: { detail: `Interest '${id}' not found in snapshot` } };
      }
      return { ok: true, status: 200, data };
    }

    // 4. Briefings
    if (path === "/api/v1/views/briefing" && m === "GET") {
      const orgId = params.subject_org_id;
      const data = snapshot.briefings?.organizations?.[orgId];
      if (!data) {
        return { ok: false, status: 404, data: { detail: `Briefing for Org '${orgId}' not found in snapshot` } };
      }
      return {
        ok: true,
        status: 200,
        data: {
          ...data,
          active_access_mode: persp.mode,
          include_hierarchy_inheritance: includeHier,
          priority_interests: applyPriorityInheritanceFilter(data.priority_interests, includeHier),
        },
      };
    }

    if (path === "/api/v1/views/briefing/effort" && m === "GET") {
      const effId = params.effort_id;
      const data = snapshot.briefings?.efforts?.[effId];
      if (!data) {
        return { ok: false, status: 404, data: { detail: `Briefing for Effort '${effId}' not found in snapshot` } };
      }
      return {
        ok: true,
        status: 200,
        data: {
          ...data,
          active_access_mode: persp.mode,
        },
      };
    }

    // 5. Entities List & Single Read
    if (path === "/api/v1/organizations" && m === "GET") {
      return { ok: true, status: 200, data: snapshot.organizations || [] };
    }

    const orgSingleMatch = path.match(/^\/api\/v1\/organizations\/([^/]+)$/);
    if (orgSingleMatch && m === "GET") {
      const id = decodeURIComponent(orgSingleMatch[1]);
      const found = (snapshot.organizations || []).find((o) => o.id === id);
      if (!found) {
        return { ok: false, status: 404, data: { detail: `Organization '${id}' not found` } };
      }
      return { ok: true, status: 200, data: found };
    }

    if (path === "/api/v1/resource-pools" && m === "GET") {
      let pools = snapshot.resource_pools || [];
      if (params.org_id) pools = pools.filter((p) => p.org_id === params.org_id);
      return { ok: true, status: 200, data: pools };
    }

    if (path === "/api/v1/interests" && m === "GET") {
      return { ok: true, status: 200, data: snapshot.interests || [] };
    }

    const intrSingleMatch = path.match(/^\/api\/v1\/interests\/([^/]+)$/);
    if (intrSingleMatch && m === "GET") {
      const id = decodeURIComponent(intrSingleMatch[1]);
      const found = (snapshot.interests || []).find((i) => i.id === id);
      if (!found) {
        return { ok: false, status: 404, data: { detail: `Interest '${id}' not found` } };
      }
      return { ok: true, status: 200, data: found };
    }

    if (path === "/api/v1/efforts" && m === "GET") {
      return { ok: true, status: 200, data: snapshot.efforts || [] };
    }

    const effSingleMatch = path.match(/^\/api\/v1\/efforts\/([^/]+)$/);
    if (effSingleMatch && m === "GET") {
      const id = decodeURIComponent(effSingleMatch[1]);
      const found = (snapshot.efforts || []).find((e) => e.id === id);
      if (!found) {
        return { ok: false, status: 404, data: { detail: `Effort '${id}' not found` } };
      }
      return { ok: true, status: 200, data: found };
    }

    if (path === "/api/v1/decisions" && m === "GET") {
      let decs = snapshot.decisions || [];
      if (params.target_effort_id) decs = decs.filter((d) => d.target_effort_id === params.target_effort_id);
      return { ok: true, status: 200, data: decs };
    }

    if (path === "/api/v1/tools" && m === "GET") {
      return { ok: true, status: 200, data: snapshot.tools || [] };
    }

    if (path.startsWith("/api/v1/telemetry/provenance/") && m === "GET") {
      return { ok: true, status: 200, data: [] };
    }

    // 6. Manifest & Diagnostics
    if (path === "/api/v1/manifest/export" && m === "GET") {
      return { ok: true, status: 200, data: snapshot.manifest };
    }

    if (path === "/api/v1/manifest/validate") {
      return { ok: true, status: 200, data: snapshot.diagnostics };
    }

    // 7. Simulation
    if (path === "/api/v1/simulation/bill-of-efforts" && m === "POST") {
      const payload = typeof body === "string" ? JSON.parse(body) : body;
      const sim = simulateTransientBoe(payload, params);
      return { ok: true, status: 200, data: sim };
    }

    if (path === "/api/v1/simulation/bill-of-efforts/commit") {
      return {
        ok: false,
        status: 403,
        data: { detail: "Read-Only Snapshot: Committing scenario changes to the database is disabled in offline snapshot mode." },
      };
    }

    // 8. Block Mutations Gracefully with a Clean Message
    if (m === "POST" || m === "DELETE" || m === "PUT" || m === "PATCH") {
      return {
        ok: false,
        status: 403,
        data: { detail: "Read-Only Snapshot: Modifying entities or relationships is disabled in exported offline snapshot archives." },
      };
    }

    return {
      ok: false,
      status: 404,
      data: { detail: `Endpoint '${path}' not available in offline snapshot mode.` },
    };
  };
})(window);
