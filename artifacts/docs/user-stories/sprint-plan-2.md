---
date: 2026-09-29
type: plan
status: active
plan_number: 2
start_date: 2026-10-19
end_date: 2026-11-15
tags: [user-story, sprint-plan, routing, graphhopper]
related: ["[[time-aware-routing-engine-stories]]", "[[edge-depth-table-stories]]", "[[time-aware-routing-engine]]", "[[edge-depth-table]]", "[[sprint-plan]]", "[[sprint-plan-3]]", "[[routing-not-time-aware]]", "[[carried-over-backlog]]"]
---

# Sprint plan 2: routing engine foundations and the depth table

The first four weeks of the sticky C-lite routing work ([[time-aware-routing-engine]] and [[edge-depth-table]]).
This is a new planning pass. It follows [[sprint-plan]], which covers Sprints 1 to 4, so sprint numbers here continue
at 5. The rest of the work is in [[sprint-plan-3]] (Sprints 9 to 12), because the dependency chain needs six sprints
and a plan covers four (`.claude/CLAUDE.md`, rule 10). No team roster is connected, so the plan orders work by
dependency and sizes it by relative estimate. Each sprint is one week.

## Why these four sprints

Four sprints because a plan covers four weeks. Their order follows one chain of dependencies that cannot be shortened.

1. The edge export needs the Java toolchain, because GraphHopper has no REST endpoint that dumps edges.
2. The depth table needs the export.
3. The engine's real-data checks and the departure timeline both need the table.
4. The rollout needs the engine, the timeline, and the user's latency factor.

That chain is Story R4, then E1, then E3 and E4, then E7 and R5, then R7, R8, R9, and R10. It fills more than four
sprints, so this plan takes the first four links and [[sprint-plan-3]] takes the rest.

Calendar, from `start_date` in the frontmatter:

| Sprint | Start | End | Actual start | Actual end |
| ------ | ----- | --- | ------------ | ---------- |
| 5 | 2026-10-19 | 2026-10-25 |  |  |
| 6 | 2026-10-26 | 2026-11-01 |  |  |
| 7 | 2026-11-02 | 2026-11-08 |  |  |
| 8 | 2026-11-09 | 2026-11-15 |  |  |

- **Sprint 5** has no dependencies. It records baselines, builds the reference and checker, defines the table
  format, and soaks the current backend before the engine builds on it.
- **Sprint 6** builds the Java toolchain and the edge export.
- **Sprint 7** builds and publishes the depth table.
- **Sprint 8** builds the engine on a synthetic table and proves the real table on the server.

The engine is the safety fix, so it has priority over the advice. The advice waits for the table because option C reads
depth by edge id. The user chose exactness over speed on 2026-09-29. The frontend's failed-route display, which the
first draft of this plan held as Story R3, is now [[frontend-polish]] Story 4 in [[sprint-plan]] Sprint 3, so it lands
before this plan starts.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`. `Reviewed` means the
code is built and read through but the acceptance check has not passed. Each story carries the same Status in
its epic file. Update both together. A story reaches `Done` only with evidence and details in both places.

## Sprint 5: baselines, reference, format, and the backend soak

**Dates:** 2026-10-19 to 2026-10-25 (Monday to Sunday)

**Sprint goal:** every later story has a real baseline and a reference to compare against, the depth-table format is
fixed, and the current backend has soaked before the engine builds on it.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-046 | P0 | Record the routing baselines on the server | S | [[time-aware-routing-engine-stories]] R1 | None | None yet | - | Not started |
| US-047 | P0 | Build the synthetic scenarios, the offline reference, and the offline checker | M | [[time-aware-routing-engine-stories]] R2 | None | None yet | - | Not started |
| US-040 | P0 | Define the table format and write the Python reader and writer | S | [[edge-depth-table-stories]] E2 | None | None yet | - | Not started |
| US-034 | P2 | Soak the flood-road backend and compare it with the earlier backend | M | [[carried-over-backlog]] Story 3 | None. Gate: the user sets the soak length and the route set before the sprint starts | None yet | - | Not started |

## Sprint 6: Java toolchain and edge export

**Dates:** 2026-10-26 to 2026-11-01 (Monday to Sunday)

**Sprint goal:** a Java module builds against the pinned GraphHopper version and runs in our image, and the
graph's edges are exported with a hash.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-049 | P0 | Build the Java module skeleton, the image, and the CI job | L | [[time-aware-routing-engine-stories]] R4 | Story R1 | None yet | - | Not started |
| US-039 | P0 | Export the graph's edges | M | [[edge-depth-table-stories]] E1 | Story R4, same sprint | None yet | - | Not started |

## Sprint 7: the depth table

**Dates:** 2026-11-02 to 2026-11-08 (Monday to Sunday)

**Sprint goal:** every run produces one depth table by edge id, published without a partial read, and the
re-import procedure is written.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-041 | P0 | Build the Airflow task that writes each run's table | L | [[edge-depth-table-stories]] E3 | Stories E1, E2 | None yet | - | Not started |
| US-042 | P0 | Publish the table atomically and keep the newest three runs | S | [[edge-depth-table-stories]] E4 | This sprint's E3 | None yet | - | Not started |
| US-044 | P1 | Document the graph re-import procedure and detect a stale table | S | [[edge-depth-table-stories]] E6 | This sprint's E3 | None yet | - | Not started |

## Sprint 8: the engine core and the table proof

**Dates:** 2026-11-09 to 2026-11-15 (Monday to Sunday)

**Sprint goal:** the time-aware search passes the four scenarios on a synthetic table, the Java reader refuses
a wrong table, and the real table is measured on the server.

| Item | Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| ---- | -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| US-050 | P0 | Build the time-aware weighting and search for `motorbike` and `car` | L | [[time-aware-routing-engine-stories]] R5 | Stories R2, R4, E2. Gate: the user confirms the sticky-from-departure wording | None yet | - | Not started |
| US-043 | P0 | Build the Java reader with a hash check and reload without restart | M | [[edge-depth-table-stories]] E5 | Stories E2, R4 | None yet | - | Not started |
| US-045 | P0 | Prove the table on the server | M | [[edge-depth-table-stories]] E7 | Stories E3, E4. Gate: the user sets the build-time limit | None yet | - | Not started |

## Carried to plan 3

Stories R6, R7, R8, R9, and R10 need the engine from Sprint 8 and go to [[sprint-plan-3]]. The gates on Stories R5 and E7
stay here. If a gate is not met by the start of its sprint, the story moves to the backlog in [[sprint-plan-3]] with the
gate as its blocking risk. Story R5 waits for the sticky-from-departure confirmation. Story E7 waits for the build-time
limit. The soak row in Sprint 5 waits for the soak length and the route set.

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| The pinned image lacks the extension points the module needs, or its source revision cannot be found | Sprint 6 stalls and the engine work moves | Story R1 finds the revision first. If the points are missing, fall back to Tier A-prime and revise this plan. |
| The LM admissibility test fails | The search runs without LM and latency rises | Story R4 runs the test early. Story R10 in [[sprint-plan-3]] measures the real latency against the factor. |
| The table build takes too long on the server | Runs slow down, or the DAG blocks | Story E4 keeps the task non-blocking. Story E7 measures it. The user sets the limit. |
| The sticky-from-departure wording is not confirmed | The engine and the advice use a different rule than the user intends | Confirm before Sprint 8. The wording is an assumption in [[time-aware-routing-engine]]. |
| A graph re-import happens between sprints | The table hash mismatches and routing falls back to today's model | Story E6 documents the procedure. The response flag and the alert message make the fallback visible. |
| Latency is unmeasured | The engine may be too slow for the map | Story R1 sets the baseline in Sprint 5, and Story R10 checks against the user's factor. |
| The soak length and route set are not set | The soak row moves out of Sprint 5 | Ask the user before Sprint 5 starts. The row then moves to the backlog with that reason. |

## Definition of done for a story

- The acceptance criteria in its epic file pass, on the server where the criteria say so.
- Tests for the story's branches are written and pass.
- The concept page for the touched subsystem is updated, and its `last_updated` is bumped.
- A screenshot or rendered output is saved under `artifacts/docs/user-stories/evidence/` and embedded in the
  epic file and in this plan, together with numbered details.

## Status history

- **2026-09-29, active.** Written from [[time-aware-routing-engine]] and [[edge-depth-table]]. No story has started.
- **2026-09-29, active.** Re-cut into a four-sprint plan at the user's request, under the cadence in `.claude/CLAUDE.md` rule 10:
  Sprints 5 to 8 stay here, dated 2026-10-19 to 2026-11-15, and Sprints 9 and 10 moved to [[sprint-plan-3]]. Story R3 left the plan because the
  same fix is [[frontend-polish]] Story 4 in [[sprint-plan]] Sprint 3, which the user scheduled. The backend soak
  from [[sprint-plan]]'s carried rows joined Sprint 5, so it runs before the engine builds on the backend.
- **2026-09-30, active.** Every row in the sprint tables now starts with an `Item` column that holds the story's ID (`US-nnn`).
