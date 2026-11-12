# Bijou v2 User Guide

Comprehensive guide to modeling, analyzing, and navigating organizational interests, resource pools, and stateful capability efforts with **Bijou v2**.

---

## 1. Domain Ontology

Bijou models strategic portfolios across four core building blocks and six typed relationship families:

1. **Organizations (`OrganizationDTO`)**: Commands, agencies, directorates, or teams (`echelon_level`, optional `is_managed` owner boundary for Resource Pools).
2. **Resource Pools (`ResourcePoolDTO`)**: Color-of-Money budgets, staffing FTE, compute hours, or material inventories restricted to designated Interests (inherited down the Interest DAG).
3. **Interests (`InterestDTO`)**: Mission goals, NIPF priorities, intelligence gaps, threat vectors, customers, or broad strategic categories organized into a taxonomic DAG (`InterestInterestEdge`).
4. **Stateful Efforts (`EffortDTO`)**: Programs, projects, or discovery tasks carrying:
   - **Execution State**: `COMPLETED`, `IN_WORK`, `PLANNED`, `BACKLOGGED`, `DISCOVERY_PENDING`, `CANCELLED`
   - **Flexible Timing Modes**: Explicit calendar dates, duration-only, or unknown/discovery-dependent (`COMPLETED_HISTORICAL`, `OPEN_ENDED_ACTIVE`, `RELATIVE_TO_DEPENDENCY`, `UNSCHEDULED_PLAN`)
   - **Resource Requirements, Delivery Risks, & Mitigators** (exercised or unexercised options)
5. **Six Typed Edges with Pedigree**:
   - `Org ↔ Org` (`HIERARCHICAL_PARENT`, `FORMAL_SUPPORTING`, `COLLABORATIVE_ADJACENT`, `CO_SPONSOR`)
   - `Org ↔ Interest` (stance + normalized priority rank + optional hierarchy rollup)
   - `Interest ↔ Interest` (`SPECIALIZES`, `CONTRIBUTES_TO`, `RELATED_TO`)
   - `Org ↔ Effort` (direct resourcing: money/staff/compute/material with skill-mismatch warning support)
   - `Effort ↔ Interest` (direct solution, indirect enabler, funded for, partial alignment)
   - `Effort ↔ Effort` (`BLOCKING` critical-path dependency vs `NON_BLOCKING_INFORMS` insight dependency)

---

## 2. Primary Workspace & Views (`A` / `B` / `G`)

- **View A — Capability Progression Tree**: Stratified left-to-right DAG grouping `COMPLETED` → `IN_WORK` → future/discovery Efforts with SPOF flags and slack calculations.
- **View B — Tri-Partite Architectural Flow**: Connects **Organizations & Resource Pools ↔ Efforts ↔ Interest Taxonomy**, illuminating indirect shared-interest benefits and partnership opportunities.
- **View G — Global Neural Graph**: Free-floating non-overlapping topology showing all three node kinds together:
  - Toggle visibility of **Orgs**, **Efforts**, and **Interests**
  - Filter by specific **Organization(s)** and/or **Interest(s)**
  - Right-click any node → **`Isolate "<name>" & Connections`**
  - Use the **Breadcrumb History Bar** (`← Back`, clickable trail pills, `Reset Graph`) to navigate filter steps
  - Scroll mouse wheel over the canvas to zoom smoothly; drag nodes to pin custom positions; drag `●` ports between cards to create relationships using plain-English statements.

---

## 3. Bill of Efforts Scenario Dock & Lenses

- **Bill of Efforts Cart Dock**: Slide-out workbench over Views `A`, `B`, and `G` to toggle mitigators, stage new allocations (catching Color-of-Money and skill-mismatch risks), test slip/cancellation shocks, and commit approved decisions.
- **Executive Briefing**: Generates a printable 1-slide landscape briefing for any Organization.
- **Entity & Graph Studio**: Form-driven full CRUD for Organizations, Resource Pools, Interests, Efforts, Typed Edges, Pre-Flight Diagnostics, and Manifest JSON import/export.

---

## 4. Command-Line Usage

```bash
# Start full standalone server (API + Web UI + OpenAPI docs at /docs)
bijou --mode standalone --port 8000

# Batch import a YAML/JSON manifest & JSONL telemetry file
bijou-ingest --server-url http://0.0.0.0:8000 \
  --manifest datasets/joint_isr_architecture.yaml \
  --telemetry datasets/satellite_cascade_telemetry.jsonl \
  --replace-all --validate-first
```
