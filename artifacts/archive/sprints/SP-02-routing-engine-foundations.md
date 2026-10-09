---
date: 2026-09-29
type: plan
status: active
plan_number: 2
start_date: 2026-10-19
end_date: 2026-11-15
tags: [user-story, sprint-plan, routing, graphhopper]
related: ["[[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]", "[[PRD-003-edge-depth-table|edge-depth-table]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[BL-011-routing-not-time-aware|routing-not-time-aware]]", "[[EP-07-carried-over-backlog|carried-over-backlog]]", "[[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]", "[[2026-10-05-us-066-criterion-4-spot-check]]", "[[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]"]
---

# Sprint plan 2: routing engine foundations and the depth table

The first four weeks of the sticky C-lite routing work ([[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] and [[PRD-003-edge-depth-table|edge-depth-table]]).
This is a new planning pass. It follows [[SP-01-prd-and-backlog|sprint-plan]], which covers Sprints 1 to 4, so sprint numbers here continue
at 5. The rest of the work is in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] (Sprints 9 to 12), because the dependency chain needs six sprints
and a plan covers four (`.claude/CLAUDE.md`, rule 10). No team roster is connected, so the plan orders work by
dependency and sizes it by relative estimate. Each sprint is one week.

## Why these four sprints

Four sprints because a plan covers four weeks. Their order follows one chain of dependencies that cannot be shortened.

1. The edge export needs the Java toolchain, because GraphHopper has no REST endpoint that dumps edges.
2. The depth table needs the export.
3. The engine's real-data checks and the departure timeline both need the table.
4. The rollout needs the engine, the timeline, and the user's latency factor.

That chain is Story R4, then E1, then E3 and E4, then E7 and R5, then R7, R8, R9, and R10. It fills more than four
sprints, so this plan takes the first four links and [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] takes the rest.

Calendar, from `start_date` in the frontmatter:

| Sprint | Start | End | Actual start | Actual end |
| ------ | ----- | --- | ------------ | ---------- |
| 5 | 2026-10-19 | 2026-10-25 | 2026-10-01 | 2026-10-05 |
| 6 | 2026-10-26 | 2026-11-01 | 2026-10-05 | 2026-10-05 |
| 7 | 2026-11-02 | 2026-11-08 | 2026-10-05 | 2026-10-05 |
| 8 | 2026-11-09 | 2026-11-15 | 2026-10-05 | 2026-10-05 |

- **Sprint 5** has no dependencies. It records baselines, builds the reference and checker, defines the table
  format, and soaks the current backend before the engine builds on it.
- **Sprint 6** builds the Java toolchain and the edge export.
- **Sprint 7** builds and publishes the depth table.
- **Sprint 8** builds the engine on a synthetic table and proves the real table on the server.

The engine is the safety fix, so it has priority over the advice. The advice waits for the table because option C reads
depth by edge id. The user chose exactness over speed on 2026-09-29. The frontend's failed-route display, which the
first draft of this plan held as Story R3, is now [[EP-02-frontend-polish|frontend-polish]] Story 4 in [[SP-01-prd-and-backlog|sprint-plan]] Sprint 3, so it lands
before this plan starts.

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`. `Reviewed` means the
code is built and read through but the acceptance check has not passed. Each story carries the same Status in
its epic file. Update both together. A story reaches `Done` only with evidence and details in both places.

## Sprint 5: baselines, reference, format, and the backend soak

**Dates:** 2026-10-19 to 2026-10-25 (Monday to Sunday)

**Sprint goal:** every later story has a real baseline and a reference to compare against, the depth-table format is
fixed, and the current backend has soaked before the engine builds on it.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 5
SORT priority ASC, file.name ASC
```

## Sprint 6: Java toolchain and edge export

**Dates:** 2026-10-26 to 2026-11-01 (Monday to Sunday)

**Sprint goal:** a Java module builds against the pinned GraphHopper version and runs in our image, and the
graph's edges are exported with a hash.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 6
SORT priority ASC, file.name ASC
```

## Sprint 7: the depth table

**Dates:** 2026-11-02 to 2026-11-08 (Monday to Sunday)

**Sprint goal:** every run produces one depth table by edge id, published without a partial read, and the
re-import procedure is written.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 7
SORT priority ASC, file.name ASC
```

## Sprint 8: the engine core and the table proof

**Dates:** 2026-11-09 to 2026-11-15 (Monday to Sunday)

**Sprint goal:** the time-aware search passes the four scenarios on a synthetic table, the Java reader refuses
a wrong table, and the real table is measured on the server.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 8
SORT priority ASC, file.name ASC
```

## Carried to plan 3

Stories R6, R7, R8, R9, and R10 need the engine from Sprint 8 and go to [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. The gates on Stories R5 and E7
were cleared on 2026-10-02: the user confirmed the sticky-from-departure wording and set the build-time limit. No story of
this plan has an open gate. The soak row in Sprint 5 has no gate, because the user set the soak length to 48 hours on 2026-10-01.

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| The pinned image lacks the extension points the module needs, or its source revision cannot be found | Sprint 6 stalls and the engine work moves | Story R1 finds the revision first. If the points are missing, fall back to Tier A-prime and revise this plan. |
| The LM admissibility test fails | The search runs without LM and latency rises | Story R4 runs the test early. Story R10 in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] measures the real latency against the factor. |
| The table build takes too long on the server | Runs slow down, or the DAG blocks | Story E4 keeps the task non-blocking. Story E7 measures it against the limit the user set on 2026-10-02 (5 minutes after `3_calculate_depth`). |
| The sticky-from-departure wording was not confirmed | Closed on 2026-10-02. The user confirmed it | Recorded in [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]]. |
| A graph re-import happens between sprints | The table hash mismatches and routing falls back to today's model | Story E6 documents the procedure. The response flag and the alert message make the fallback visible. |
| Latency is unmeasured | The engine may be too slow for the map | Story R1 sets the baseline in Sprint 5, and Story R10 checks against the user's factor. |

## Definition of done for a story

- The acceptance criteria in its epic file pass, on the server where the criteria say so.
- Tests for the story's branches are written and pass.
- The concept page for the touched subsystem is updated, and its `last_updated` is bumped.
- A screenshot or rendered output is saved under `artifacts/docs/stories/evidence/` and embedded in the
  epic file and in this plan, together with numbered details.

## Status history

Story-level progress lines up to 2026-10-10 are in [[SP-02-routing-engine-foundations-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-29, active.** Written from [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] and [[PRD-003-edge-depth-table|edge-depth-table]]. No story has started.
- **2026-09-29, active.** Re-cut into a four-sprint plan at the user's request, under the cadence in `.claude/CLAUDE.md` rule 10:
  Sprints 5 to 8 stay here, dated 2026-10-19 to 2026-11-15, and Sprints 9 and 10 moved to [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. Story R3 left the plan because the
  same fix is [[EP-02-frontend-polish|frontend-polish]] Story 4 in [[SP-01-prd-and-backlog|sprint-plan]] Sprint 3, which the user scheduled. The backend soak
  from [[SP-01-prd-and-backlog|sprint-plan]]'s carried rows joined Sprint 5, so it runs before the engine builds on the backend.
- **2026-10-01, active.** `US-034` dropped its Valhalla comparison and now checks GraphHopper against the vehicle depth limits, because the Valhalla model was wrong when it ran. The user set the soak length to 48 hours. The gate on the soak row and its risk row are removed. See [[EP-07-carried-over-backlog|carried-over-backlog]] Story 3.
- **2026-10-01, active.** Sprint 5 started on 2026-10-01, 18 days before its planned start, at the user's request. `US-037` (Sprint 4) is still open. No row here lists it as a dependency. Two rows share the server with the pipeline, so they wait for the `US-037` knob to settle: the latency numbers of `US-046`, and the 48-hour clock of `US-034`. See [[sprint-5-baselines-reference-format-and-soak]].
- **2026-10-02, active.** Added `US-062` ([[US-062-map-refresh-requirement-research|map-refresh-requirement-research]]) to Sprint 5 as P2, size M, In progress, at the user's request for "todos for today". The user does not know the shortest time in which a person must react to the map, so research is needed. The plan is [[map-refresh-requirement-research-plan]], written with the deep-research skill (Phase 1). Phase 2 waits for the user's confirmation.
- **2026-10-02, active.** Added `US-063` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 8) to Sprint 5 as P2, size S, `In progress`, at the user's request. The user named the event, the Hanoi rain of 2025-10-05 to 2025-10-08, and asked for a 48-hour cut. The cut is 2025-10-05T22:30Z to 2025-10-07T22:30Z (246.8 mm, peak 56.48 mm/h). The code and tests are written. Sprint 5 has 3 `Done` rows (`US-040`, `US-046`, `US-047`), 2 `In progress` rows (`US-034`, `US-063`), and 1 `Reviewed` row (`US-062`). Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]].
- **2026-10-02, active.** The user asked for a plan of everything that needs no server, and said the server stays untouched for now. Added `US-064` (the soak check must fail when Docker or a log read fails, P1, S) and `US-065` (a margin report over every run of the replay, P2, M) to Sprint 5. `US-063` also gets a schedule preview. The pipeline's own gate gives 104 simulating runs of 192 at 5 mm/h, not 98. Sprint 5 has 3 `Done` rows, 2 `In progress` (`US-034`, `US-063`), 2 `Not started` (`US-064`, `US-065`), and 1 `Reviewed` (`US-062`). Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]].
- **2026-10-02, active.** The user decided on the open items. The trigger task keeps its one retry, with no change during the test. The loose ends (the geocoder story in [[EP-02-frontend-polish|frontend-polish]] still `Reviewed`, the `flood_road_values_shadow` table on the server, and `US-061` in the backlog of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]) wait until after Sprint 6, and their sprint is set then (rule 9). The end-of-test evidence scripts for `US-034`, `US-037`, and `US-063` are written and dry-run.
- **2026-10-04, active.** `US-066` (narrow and compress `netcdf_values` onto TimescaleDB) added to Sprint 5. It came out of the same soak test this sprint already runs (`US-034`): `netcdf_values` had no retention policy and reached 56 GB during it ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]). Nothing in this plan depends on it or blocks it, so it goes in the earliest sprint with room, which is the current one.
- **2026-10-05, active.** `US-067` (prune old runs' `flood_extent_polygon` rows on every publish, [[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]) added to Sprint 5 and marked `Done`. It is the other table the same incident found with no retention policy ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]), unrelated to `US-066`'s `netcdf_values` work. Nothing in this plan depends on it, so it goes in the current sprint. 21 tests pass. Evidence: `us-067-prune-polygon-rows-check-output.png`.
- **2026-10-05, active.** Added `US-068` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 11) to Sprint 5 as P2, size S, `Not started`, at the user's request. `1_trigger_simulation` pushes only `sim_id`. The story adds a `rain_ingested` summary of what is sent to 3Di. It has no dependency and needs no server to build.
- **2026-10-05, active.** The user said the replay is running again, to be checked after 48 hours. Added `US-069` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 12) to Sprint 5 as P1, size S, `Not started`, at the user's request: read the storage at the start, at 24 hours, and at 48 hours. It reads the same window as `US-034` and `US-037`, so the sprint cannot close before it.
- **2026-10-05, active.** The user closed `US-034` and `US-037` as `Done` on the 137 runs of the replay and asked to move on to Sprint 6. Neither has its end check or a new screenshot, and the user waived the evidence. Both rows say so in their Details. Sprint 5 ended on 2026-10-05, 20 days before its planned end of 2026-10-25. `US-068` and `US-069` are `Not started` and carry to the `TODOS.md` Backlog, and neither gates Sprint 6. Sprint 6 started on 2026-10-05. No blocker stops Sprint 7 (`US-041`, `US-042`, `US-044`). The server steps of Sprint 6 wait for the replay still running ([[todos-2026-10-05-us-068-and-sprint-5-closeout]]).
- **2026-10-05, active.** `US-069` (storage check) moved from Sprint 5 to Sprint 8 at the user's request: not testing now, continue after Sprint 7. It needs the DAG unpaused for 48 hours. Sprint 8 already holds `US-050`, `US-043`, and `US-045`, so move a row if the sprint is too full (rule 10).
- **2026-10-05, active.** Timeline set to the real dates. Sprint 5 ran 2026-10-01 to 2026-10-05, and Sprint 6 started and ended on 2026-10-05 (27 days before its planned end of 2026-11-01), because both of its rows, `US-049` and `US-039`, were `Done` the same day. Sprint 7 started on 2026-10-05, 28 days before its planned start of 2026-11-02. An earlier line here said Sprint 5 ended 14 days early. The right number is 20.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`) moved from `Not started` to `Reviewed`. Built: the page [[graph-reimport-procedure]], the Python stale-table guard, and `check_tables.py` (99 tests pass). Not done: the run on the server, and the Java refusal at request time, which is the acceptance of `US-043` in Sprint 8. The user is asked to confirm that split. Plan: [[graph-reimport-procedure-and-stale-table-check]].
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`): the server check passed. With the export, `graph_edge`, and the `latest` table on hash `8c13d884...` the check says `FRESH`, and against another hash it says `STALE`, names both hashes, and exits 1. Evidence: `us-044-stale-table-check-server-output.png`, rendered from output the user pasted. The status stays `Reviewed` until the user confirms the split with `US-043` (the request-time refusal is the Java reader's), and then it moves to `Done`.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`) moved from `Reviewed` to `Done`. The user confirmed the split: the page, the Python guard, and the operator check are closed here, and the refusal at request time in the Java reader is the acceptance of `US-043` (Sprint 8). Evidence: `us-044-stale-table-check-server-output.png`. All three Sprint 7 rows (`US-041`, `US-042`, `US-044`) are `Done`, so Sprint 7 ended on 2026-10-05, 34 days before its planned end of 2026-11-08. `US-068` is still `Reviewed` in the Backlog, and `US-069` is in Sprint 8.
- **2026-10-05, active.** Sprint 8 started on 2026-10-05, 35 days before its planned start of 2026-11-09, at the user's request. Its rows are `US-050` (the time-aware weighting and search), `US-043` (the Java reader with the hash check), `US-045` (prove the table on the server), and `US-069` (the storage check, which needs the DAG unpaused for 48 hours). `US-045` also needs a live DAG run of the new tasks to measure the table task against the 5-minute limit, so it needs the DAG unpaused too. No blocker stops Sprint 9 (`US-052`, `US-051`, `US-053` in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]), checked on 2026-10-05.
