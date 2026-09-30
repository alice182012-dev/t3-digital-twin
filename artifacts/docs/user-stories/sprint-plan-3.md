---
date: 2026-09-29
type: plan
status: active
plan_number: 3
start_date: 2026-11-16
end_date: 2026-12-13
tags: [user-story, sprint-plan, routing, graphhopper]
related: ["[[time-aware-routing-engine-stories]]", "[[edge-depth-table-stories]]", "[[time-aware-routing-engine]]", "[[sprint-plan-2]]", "[[sprint-plan]]", "[[carried-over-backlog]]", "[[routing-not-time-aware]]"]
---

# Sprint plan 3: the engine in the backend, the advice, and the rollout

The last links of the sticky C-lite chain, plus one carried item. This plan follows [[sprint-plan-2]] (Sprints 5 to 8),
so its sprint numbers continue at 9. It covers four weeks (`.claude/CLAUDE.md`, rule 10). It depends on
[[sprint-plan-2]] finishing: Story R5 (the engine) and Story E5 (the Java reader) must be `Done` before Sprint 9.

## Why these four sprints

Four sprints because a plan covers four weeks. Sprints 9 and 10 hold the remaining engine work. Sprint 11 holds a
carried, dependency-free item. Sprint 12 is spare capacity for slips, and no story is placed there yet.

Calendar, from `start_date` in the frontmatter:

| Sprint | Start | End |
| ------ | ----- | --- |
| 9 | 2026-11-16 | 2026-11-22 |
| 10 | 2026-11-23 | 2026-11-29 |
| 11 | 2026-11-30 | 2026-12-06 |
| 12 | 2026-12-07 | 2026-12-13 |

- **Sprint 9** adds the other two profiles, the backend switch with its fallback, and the departure endpoint.
- **Sprint 10** shows the advice in the alert and rolls the engine out.
- **Sprint 11** writes `DESIGN.md` from the shipped UI.
- **Sprint 12** is spare.

The advice waits for the table because option C reads depth by edge id. That puts the "wait until" alert in Sprint 10,
later than an approach that joined route pieces by geometry would have. The user chose exactness over speed on
2026-09-29.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`. Each story carries the same
Status in its epic file. Update both together. A story reaches `Done` only with evidence and details in both places.

## Sprint 9: profiles, backend switch, and the departure endpoint

**Dates:** 2026-11-16 to 2026-11-22 (Monday to Sunday)

**Sprint goal:** all four modes route through the time-aware engine behind a flag with a safe fallback, and
`POST /route/departures` returns the earliest clear departure.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-052 | P0 | Integrate the engine into the backend with a flag and a fallback | M | [[time-aware-routing-engine-stories]] R7 | Stories R5, E5 (both from [[sprint-plan-2]]) | None yet | - | Not started |
| US-051 | P1 | Add the `truck` and `foot` time-aware profiles | S | [[time-aware-routing-engine-stories]] R6 | Story R5 | None yet | - | Not started |
| US-053 | P1 | Build `POST /route/departures` | M | [[time-aware-routing-engine-stories]] R8 | Stories E2, E3, E4, and this sprint's R7 | None yet | - | Not started |

## Sprint 10: the advice in the alert, and the rollout

**Dates:** 2026-11-23 to 2026-11-29 (Monday to Sunday)

**Sprint goal:** the alert shows "wait until", the engine passes its checks on the server inside the latency
factor, and the flag goes on with evidence.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-054 | P1 | Show "wait until" in the no-route alert | S | [[time-aware-routing-engine-stories]] R9 | Story R8, and [[frontend-polish]] Story 4 ([[sprint-plan]] Sprint 3) | None yet | - | Not started |
| US-055 | P0 | Prove the engine on the server and roll it out | M | [[time-aware-routing-engine-stories]] R10 | Stories R6, R7, R9, E7. Gate: the user sets the latency factor | None yet | - | Not started |

## Sprint 11: DESIGN.md

**Dates:** 2026-11-30 to 2026-12-06 (Monday to Sunday)

**Sprint goal:** the project has one versioned file of design tokens extracted from the shipped UI.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-033 | P3 | Write a project `DESIGN.md` with real design tokens | M | [[carried-over-backlog]] Story 2 | None | None yet | - | Not started |

## Sprint 12: spare capacity

**Dates:** 2026-12-07 to 2026-12-13 (Monday to Sunday)

**Sprint goal:** absorb slips from Sprints 9 to 11. No story is placed here yet.

## Backlog


Nothing here has a sprint number.

| Item | Why it has no sprint | Linked risk |
| ---- | -------------------- | ----------- |
| Measure how many routes arrival-only closure would change | Needs the engine shipped first. A number, not a decision. | [[sticky-c-lite-routing]], roadmap phase 7 |
| Sweep alternative routes across departures | Build only if the timeline often says "blocked" while a detour exists. | [[departure-time-advice-research]], step 2 |
| Precompute per-run piece windows for the timeline | Build only if the request-time query proves slow. | [[departure-time-advice-research]] |
| Saved routes and push alerts | Need accounts and an alert channel, which do not exist. | [[departure-time-advice-research]] |
| Enable `osm_way_id` in the graph | A second route to the same key. Revisit only if edge geometry sampling proves wrong. | [[edge-depth-table]] |

Story R10 is scheduled with a gate. If the user has not set the latency factor by the start of Sprint 10, the story moves
to this backlog with the gate as its blocking risk. The gates on Stories R5 and E7 are in [[sprint-plan-2]].

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Plan 2 slips, so Story R5 or E5 is not `Done` when Sprint 9 starts | Sprint 9 cannot start its rows | Sprint 12 absorbs one week of slip. Beyond that, start a new plan and move rows. |
| The fallback is today's single-step model | A fallback response can still send a traveller into rising water | The response carries a flag and the frontend says "timing check unavailable". Track how often the fallback runs. |
| The chart and the engine show different depths | Two numbers for one route on one screen | Both sample the same tiles. Note the spacing difference in the chart's documentation. |
| The user has not set the latency factor | Story R10 has no pass mark | Ask before Sprint 10. The row moves to the backlog if the factor is not set. |

## Definition of done for a story

The same as [[sprint-plan-2]]: acceptance criteria pass on the server where they say so, tests pass, the concept page is
updated with `last_updated` bumped, and a screenshot or rendered output plus numbered details are recorded in the epic
file and in this plan.

## Status history

- **2026-09-29, active.** Split from the first draft of [[sprint-plan-2]], which had six sprints, so each plan covers four
  weeks. Sprints 9 and 10 moved here with the backlog and the plan-3 risks. The carried `DESIGN.md` row from [[sprint-plan]]
  is in Sprint 11, and Sprint 12 is spare.
- **2026-09-30, active.** Every row in the sprint tables now starts with an `Item` column that holds the story's ID (`US-nnn`).
