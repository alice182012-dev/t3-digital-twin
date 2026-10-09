---
date: 2026-09-29
type: plan
status: active
tags: [plan, prd, user-story, sprint-plan, routing]
related: ["[[BL-011-routing-not-time-aware|routing-not-time-aware]]", "[[sticky-c-lite-routing]]", "[[departure-time-advice-research]]", "[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[PRD-003-edge-depth-table|edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# Turn the sticky C-lite decision into PRDs, stories, and a sprint plan

The user decided on 2026-09-29 to do two things. First, upgrade the routing engine to sticky C-lite.
Second, make the routing graph read depth from a per-edge depth table keyed by GraphHopper edge id.
This plan lists the documents that turn those two decisions into schedulable work.

## Steps

1. Write [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] (PRD). Scope: the engine, the profiles, the backend switch and
   fallback, the request-time rule, and the "wait until" advice.
2. Write [[PRD-003-edge-depth-table|edge-depth-table]] (PRD). Scope: the edge export, the table format, the Airflow task, the
   publish and retention rules, and the readers.
3. Write one epic file of user stories for each PRD, with Priority, Estimate, and Sprint on each row.
4. Write [[SP-02-routing-engine-foundations|sprint-plan-2]], a new planning pass, with sprint count set by dependencies.
5. Add a status line to [[BL-011-routing-not-time-aware|routing-not-time-aware]] that links the new pages.

## Input facts

- The design, cost-benefit, and roadmap are in [[sticky-c-lite-routing]].
- The advice design is in [[departure-time-advice-research]].
- Verified on the server on 2026-09-29 (GraphHopper 12.0): `edge_id` and `time` path details return, and
  `osm_way_id` does not.
- The frontend dependency is todo 13 in [[frontend-todos-and-backend-dependencies]].

## Status history

- **2026-09-29, active.** Plan written before drafting the PRDs.
