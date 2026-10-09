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

- **2026-09-29, active.** Written from [[PRD-004-time-aware-routing-engine|time-aware-routing-engine]] and [[PRD-003-edge-depth-table|edge-depth-table]]. No story has started.
- **2026-09-29, active.** Re-cut into a four-sprint plan at the user's request, under the cadence in `.claude/CLAUDE.md` rule 10:
  Sprints 5 to 8 stay here, dated 2026-10-19 to 2026-11-15, and Sprints 9 and 10 moved to [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. Story R3 left the plan because the
  same fix is [[EP-02-frontend-polish|frontend-polish]] Story 4 in [[SP-01-prd-and-backlog|sprint-plan]] Sprint 3, which the user scheduled. The backend soak
  from [[SP-01-prd-and-backlog|sprint-plan]]'s carried rows joined Sprint 5, so it runs before the engine builds on the backend.
- **2026-09-30, active.** Every row in the sprint tables now starts with an `Item` column that holds the story's ID (`US-nnn`).
- **2026-10-01, active.** `US-034` dropped its Valhalla comparison and now checks GraphHopper against the vehicle depth limits, because the Valhalla model was wrong when it ran. The user set the soak length to 48 hours. The gate on the soak row and its risk row are removed. See [[EP-07-carried-over-backlog|carried-over-backlog]] Story 3.
- **2026-10-01, active.** Sprint 5 started on 2026-10-01, 18 days before its planned start, at the user's request. `US-037` (Sprint 4) is still open. No row here lists it as a dependency. Two rows share the server with the pipeline, so they wait for the `US-037` knob to settle: the latency numbers of `US-046`, and the 48-hour clock of `US-034`. See [[sprint-5-baselines-reference-format-and-soak]].
- **2026-10-01, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E2 (`US-040`) moved from `Not started` to `Done`. The reader and writer pass 25 tests, and the table format has a reference page, [[edge-depth-table-format]]. Output rendered as `us-040-table-check-output.png`. Sprint 5 has 1 `Done` row and 3 `Not started`.
- **2026-10-01, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R2 (`US-047`) moved from `Not started` to `Done`: the reference and checker pass 54 tests, and all 16 scenario runs on real Hanoi roads match the sticky column with no crossing. The story's throwaway PostGIS is not used, because the scenarios need no spatial query. Sprint 5 has 2 `Done` rows, `US-046` is next, and `US-034` waits for the `US-037` knob.
- **2026-10-01, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R1 (`US-046`) is `In progress`. Measured today: 67,833 edges (the PRD guessed 2 million), a real run has 8 steps of 15 minutes (the PRD assumed 9 steps over 2 hours), and the image's source revision is GraphHopper commit `d7dc1b06`. The p50 and p95 of `POST /route` wait for the `US-037` knob. The reference's scenarios now use 8 steps.
- **2026-10-02, active.** Added `US-062` ([[US-062-map-refresh-requirement-research|map-refresh-requirement-research]]) to Sprint 5 as P2, size M, In progress, at the user's request for "todos for today". The user does not know the shortest time in which a person must react to the map, so research is needed. The plan is [[map-refresh-requirement-research-plan]], written with the deep-research skill (Phase 1). Phase 2 waits for the user's confirmation.
- **2026-10-02, active.** `US-062` moved from `In progress` to `Reviewed`: the research is done ([[flood-map-reaction-time-findings]]), and the story needs the user's decision on the refresh interval before it can be `Done`. The user had ruled out interviews and asked for English and Vietnamese sources and real Hanoi rates.
- **2026-10-02, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R1 (`US-046`) moved from `In progress` to `Done`. The `US-037` knob settled on 2026-10-02, so the latency numbers were taken: GraphHopper alone 8 to 21 ms at the p50, with the flood model 153 to 1,857 ms. Sprint 5 has 3 `Done` rows. Evidence: `us-046-baselines-check-output.png`.
- **2026-10-02, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 3 (`US-034`) moved from `Not started` to `In progress`. The soak window is 2026-10-02 00:45 +07 to 2026-10-04 00:45 +07, the start the user gave. At 2 hours 28 minutes the logs hold no 5xx response and no error line, and the known-answer check passed 86 of 92 pairs and skipped 6. The row stays off `Done` until `run_soak.sh` exits with 0 after the window ends.
- **2026-10-02, active.** The user stopped the pipeline, because the constant 50 mm/h test rain is not a real event. Two things follow. The `US-034` soak window of 2026-10-02 00:45 +07 is void, and the soak restarts under the replay of `US-063` and ends 48 hours after the replay starts. [[EP-07-carried-over-backlog|carried-over-backlog]] Story 6 (`US-037`) is `In progress` again and is retested under the same replay. Docker on the server returned HTTP 500 at 13:53 +07. It works again since about 15:00, and every container was recreated ([[2026-10-02-disk-cleanup-and-d-drive-move]]).
- **2026-10-02, active.** Added `US-063` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 8) to Sprint 5 as P2, size S, `In progress`, at the user's request. The user named the event, the Hanoi rain of 2025-10-05 to 2025-10-08, and asked for a 48-hour cut. The cut is 2025-10-05T22:30Z to 2025-10-07T22:30Z (246.8 mm, peak 56.48 mm/h). The code and tests are written. Sprint 5 has 3 `Done` rows (`US-040`, `US-046`, `US-047`), 2 `In progress` rows (`US-034`, `US-063`), and 1 `Reviewed` row (`US-062`). Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]].
- **2026-10-02, active.** The user asked for a plan of everything that needs no server, and said the server stays untouched for now. Added `US-064` (the soak check must fail when Docker or a log read fails, P1, S) and `US-065` (a margin report over every run of the replay, P2, M) to Sprint 5. `US-063` also gets a schedule preview. The pipeline's own gate gives 104 simulating runs of 192 at 5 mm/h, not 98. Sprint 5 has 3 `Done` rows, 2 `In progress` (`US-034`, `US-063`), 2 `Not started` (`US-064`, `US-065`), and 1 `Reviewed` (`US-062`). Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]].
- **2026-10-02, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 9 (`US-064`) moved from `Not started` to `Done`. The soak check now fails on an unreadable server, and it checks container start times, which it promised but did not do. 42 tests pass. Evidence: `us-064-soak-check-output.png`. Sprint 5 has 4 `Done` rows, 2 `In progress` (`US-034`, `US-063`), 1 `Not started` (`US-065`), and 1 `Reviewed` (`US-062`). `US-034` can now use the script.
- **2026-10-02, active.** Docker on the server is back. A stopped `com.docker.service` caused the HTTP 500, and the disk cleanup log records the restart, the move of `./data` and the `airflow-logs` volume to `D:`, and 18 healthy services at 15:09 +07 ([[2026-10-02-disk-cleanup-and-d-drive-move]]). The server steps of `US-063`, `US-037`, and `US-034` now wait for the user's go, not for Docker. The server itself was not rechecked in this session.
- **2026-10-02, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 8 (`US-063`) is deployed to the server, and the `US-034` soak window is 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07. The server's rain gate is 0.01 mm/h, so all 192 runs of the replay simulate, not the 104 of a 5 mm/h gate. The pipeline starts when the user unpauses `flood_mapping_full`.
- **2026-10-02, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 10 (`US-065`) moved from `Not started` to `Done`, and the schedule preview of Story 8 (`US-063`) is built. The report, run on 50 real runs of the 50 mm/h storm, shows the margin turning negative from the 03:00 hour on, which backs the reopening of `US-037`. Evidence: `us-065-margin-report-check-output.png`. Sprint 5 has 5 `Done` rows (`US-040`, `US-046`, `US-047`, `US-064`, `US-065`), 2 `In progress` (`US-034`, `US-063`), and 1 `Reviewed` (`US-062`).
- **2026-10-02, active.** [[US-062-map-refresh-requirement-research|map-refresh-requirement-research]] (`US-062`) moved from `Reviewed` to `Done`. The user decided to keep the 15-minute refresh for now. The map-age label and a faster pipeline were not chosen. Evidence: `us-062-decision-check-output.png`. Sprint 5 has 6 `Done` rows (`US-040`, `US-046`, `US-047`, `US-062`, `US-064`, `US-065`) and 2 `In progress` (`US-034`, `US-063`).
- **2026-10-02, active.** The replay is running on the server. The user unpaused `flood_mapping_full` at about 15:54 +07, the 16:00 slot read the replay and started, and the `US-034` soak and the `US-037` retest run until 2026-10-04 16:00 +07. A killed first attempt left a 3Di simulation running, and the retry got HTTP 429 (no sessions) once before it succeeded.
- **2026-10-02, active.** The user decided on the open items. The trigger task keeps its one retry, with no change during the test. The loose ends (the geocoder story in [[EP-02-frontend-polish|frontend-polish]] still `Reviewed`, the `flood_road_values_shadow` table on the server, and `US-061` in the backlog of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]) wait until after Sprint 6, and their sprint is set then (rule 9). The end-of-test evidence scripts for `US-034`, `US-037`, and `US-063` are written and dry-run.
- **2026-10-02, active.** The user cleared the gates. `US-050` (Story R5): the sticky-from-departure wording is confirmed. `US-045` (Story E7): the build-time limit is that the table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`. The latency factor of 2, for `US-055` in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], is set too. No row of Sprints 5 to 8 has an open gate.
- **2026-10-02, active.** Sprint 6 is planned in [[sprint-6-java-toolchain-and-edge-export]], with no server change. It starts when Sprint 5's three open rows are `Done`, which is the user's call. The plan found that the stock GraphHopper web server cannot be told to run a `GraphHopper` subclass, so `US-049` needs its own application class. It lists three decisions for the user: a JDK on the Mac, where CI runs, and when the sprint starts.
- **2026-10-02, active.** The user decided the Sprint 6 approach. Java runs in Docker on the server and in GitHub Actions, with no JDK on the Mac. Sprint 6 starts after the 48-hour test, when Sprint 5's three open rows are `Done`. No Java build runs on the server before then. `US-049` takes a classpath shadow of the 62-line `GraphHopperManaged` to run a `GraphHopper` subclass. The todo list is in [[sprint-6-java-toolchain-and-edge-export]].
- **2026-10-04, active.** `US-066` (narrow and compress `netcdf_values` onto TimescaleDB) added to Sprint 5. It came out of the same soak test this sprint already runs (`US-034`): `netcdf_values` had no retention policy and reached 56 GB during it ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]). Nothing in this plan depends on it or blocks it, so it goes in the earliest sprint with room, which is the current one.
- **2026-10-05, active.** `US-066` moved from `Reviewed` to `Done`. Criteria 1 to 3 re-verified live and still hold: `mesh_elements` at exactly 63,339 rows, both the compression and retention policies active with `last_run_status = Success`, and `file_id` 245 at 1,302,146 rows across all 6 variables. Evidence: `us-066-netcdf-timescale-verify.png`. Criterion 4 run as a spot-check: the old table's only backfilled file_ids, 241 and 242, match row for row; the other 110 were never copied, and of their rows, 84,471,989 are still inside the new table's 48-hour window and 55,436,350 are already past it. Nothing in the codebase reads `netcdf_values` outside the ingestion and backfill scripts. Recommendation is to drop the old table; the statement is ready but not run, pending the user's go. Full finding in [[2026-10-05-us-066-criterion-4-spot-check]]. Sprint 5 has 7 `Done` rows (`US-040`, `US-046`, `US-047`, `US-062`, `US-064`, `US-065`, `US-066`) and 2 `In progress` (`US-034`, `US-063`).
- **2026-10-05, active.** `US-063` moved from `In progress` to `Done`. On the server, `dag_run` shows 137 of the window's 192 runs completed (136 `success`, 1 `failed`) between 2026-10-02T09:00:00Z and the 2026-10-04 disk-full incident that cut the chain short ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]). The task log confirms the exact replay line and start time at the first slot and the exact peak rate (56.48 mm/h) at the event's recorded peak slot. All 137 completed runs took the simulate branch; the dry-skip branch was never exercised live at the server's 0.01 mm/h gate, only in the offline tests. Closing on behavior proven correct for every slot that ran, not on the full run count, is a judgment call flagged for the user to confirm. `US-037` and `US-034`, which need the fuller window, stay open. Evidence: `us-063-rain-replay-server-check.png`.
- **2026-10-05, active.** `US-067` (prune old runs' `flood_extent_polygon` rows on every publish, [[US-067-prune-flood-extent-polygon-rows|prune-flood-extent-polygon-rows]]) added to Sprint 5 and marked `Done`. It is the other table the same incident found with no retention policy ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]), unrelated to `US-066`'s `netcdf_values` work. Nothing in this plan depends on it, so it goes in the current sprint. 21 tests pass. Evidence: `us-067-prune-polygon-rows-check-output.png`.
- **2026-10-05, active.** `US-066` criterion 4 fully exercised: on the user's go, `DROP TABLE netcdf_values;` ran on `storage-postgres`. Confirmed before (56 GB, 142,548,685 rows) and after (`to_regclass` null, `minio_custom` 70 GB to 14 GB, the `storage-postgres-data` volume 76.61 GB to 16.01 GB). The container stayed healthy, no restart needed. This frees space inside the Docker volume, not yet on the Windows host; the `wsl --shutdown` + `diskpart compact vdisk` pass stays open in [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]].
- **2026-10-05, active.** Added `US-068` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 11) to Sprint 5 as P2, size S, `Not started`, at the user's request. `1_trigger_simulation` pushes only `sim_id`. The story adds a `rain_ingested` summary of what is sent to 3Di. It has no dependency and needs no server to build.
- **2026-10-05, active.** The user said the replay is running again, to be checked after 48 hours. Added `US-069` ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 12) to Sprint 5 as P1, size S, `Not started`, at the user's request: read the storage at the start, at 24 hours, and at 48 hours. It reads the same window as `US-034` and `US-037`, so the sprint cannot close before it.
- **2026-10-05, active.** The user closed `US-034` and `US-037` as `Done` on the 137 runs of the replay and asked to move on to Sprint 6. Neither has its end check or a new screenshot, and the user waived the evidence. Both rows say so in their Details. Sprint 5 ended on 2026-10-05, 20 days before its planned end of 2026-10-25. `US-068` and `US-069` are `Not started` and carry to the `TODOS.md` Backlog, and neither gates Sprint 6. Sprint 6 started on 2026-10-05. No blocker stops Sprint 7 (`US-041`, `US-042`, `US-044`). The server steps of Sprint 6 wait for the replay still running ([[todos-2026-10-05-us-068-and-sprint-5-closeout]]).
- **2026-10-05, active.** The user paused `flood_mapping_full`, so the replay stopped and the server is free. The Sprint 6 server steps no longer wait. `US-069` (storage check) has no 24-hour or 48-hour window to read until the DAG is unpaused, and stays `Not started` in the Backlog.
- **2026-10-05, active.** `US-069` (storage check) moved from Sprint 5 to Sprint 8 at the user's request: not testing now, continue after Sprint 7. It needs the DAG unpaused for 48 hours. Sprint 8 already holds `US-050`, `US-043`, and `US-045`, so move a row if the sprint is too full (rule 10).
- **2026-10-05, active.** `US-068` is `Reviewed`: `rain_ingested` is pushed from `1_trigger_simulation` (6 new tests, 22 pass in `test/test_create_simulation_cycle.py`). The acceptance check on a real run and its screenshot wait for the DAG to be unpaused.
- **2026-10-05, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R4 (`US-049`) moved from `Not started` to `Reviewed`. The module, image files, and CI workflow are written, and 9 tests pass locally. Result for the LM question: LM stays valid for a raise-only weighting. Waiting on the first CI run (needs the user's approval to push) and the image build on the server.
- **2026-10-05, active.** `US-049` first CI run passed (run 1, commit `ef5ef4c`, job `test`, 1 minute 34 seconds: the pinned GraphHopper built, then `mvn test`). Still `Reviewed`: the image build and start on the server, and the screenshots, are not done.
- **2026-10-05, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R4 (`US-049`) moved from `Reviewed` to `Done`. CI run 1 passed, and the image smoke test passed on the server: `TimeAwareGraphHopper active` in the log and 12 of 12 routes equal to the live service. Evidence: `us-049-image-smoke-test-output.png`, rendered from output the user pasted. `US-039` has its dependency.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E1 (`US-039`) moved from `Not started` to `Reviewed`. The export is built and tested (18 tests pass in the module) and checked on an Andorra graph. Not done: the run on the server graph and its screenshot (`java/time-aware-routing/export-edges.sh`).
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E1 (`US-039`) moved from `Reviewed` to `Done`. The export ran on the live graph on the server, read-only: 67,833 rows for 67,833 edges, identical on two runs, one hash. Evidence: `us-039-edge-export-server-output.png`, rendered from output the user pasted. Both Sprint 6 rows (`US-049`, `US-039`) are `Done`.
- **2026-10-05, active.** Timeline set to the real dates. Sprint 5 ran 2026-10-01 to 2026-10-05, and Sprint 6 started and ended on 2026-10-05 (27 days before its planned end of 2026-11-01), because both of its rows, `US-049` and `US-039`, were `Done` the same day. Sprint 7 started on 2026-10-05, 28 days before its planned start of 2026-11-02. An earlier line here said Sprint 5 ended 14 days early. The right number is 20.
- **2026-10-05, active.** Sprint 7 starts with `US-041` (the Airflow task that writes the table), which needs the export of `US-039` and the format of `US-040`, both done. `US-042` and `US-044` need `US-041`. No blocker stops Sprint 8 (`US-050`, `US-043`, `US-045`, `US-069`), checked on 2026-10-05 against the unresolved blockers.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E3 (`US-041`) moved from `Not started` to `Reviewed`. The task, the export loader, the sampler, and the spot check are built and tested against a throwaway PostGIS. Not done: the run on the server graph, the 20-edge spot check, and the duration against the 5-minute limit. Plan: [[edge-depth-table-airflow-task]].
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E3 (`US-041`) moved from `Reviewed` to `Done`. On the server, for run `20261005T120000`: 67,833 edges by 8 steps, 1,085,487 bytes, built in 42.0 s, and all 160 values of the 20-edge spot check equal a direct `ST_Value` reading. Evidence: `us-041-edge-depth-table-server-output.png`, rendered from output the user pasted. Built through the Airflow worker, not a DAG run, because the DAG is paused. `US-042` and `US-044` can start.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E4 (`US-042`) moved from `Not started` to `Reviewed`. Atomic publish, retention, and the storage choice (the Docker volume `edge-depth-tables`) are built and tested (83 tests in `scripts/edge_depth/`, 18 in the DAG graph test). Not done: the volume on the server, and `publish_check.py` there. Plan: [[edge-depth-table-publish]].
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E4 (`US-042`) moved from `Reviewed` to `Done`. On the server, with the new volume `edge-depth-tables`: a reader in its own process made 11,878 reads while 41 tables published, none failed, and it saw all 41 pointer moves. Retention left 3 tables. Evidence: `us-042-atomic-publish-server-output.png`, rendered from output the user pasted. `US-044` can start.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`) moved from `Not started` to `Reviewed`. Built: the page [[graph-reimport-procedure]], the Python stale-table guard, and `check_tables.py` (99 tests pass). Not done: the run on the server, and the Java refusal at request time, which is the acceptance of `US-043` in Sprint 8. The user is asked to confirm that split. Plan: [[graph-reimport-procedure-and-stale-table-check]].
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`): the server check passed. With the export, `graph_edge`, and the `latest` table on hash `8c13d884...` the check says `FRESH`, and against another hash it says `STALE`, names both hashes, and exits 1. Evidence: `us-044-stale-table-check-server-output.png`, rendered from output the user pasted. The status stays `Reviewed` until the user confirms the split with `US-043` (the request-time refusal is the Java reader's), and then it moves to `Done`.
- **2026-10-05, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 11 (`US-068`) moved from `Reviewed` to `Done`. The first run of the replay on the server pushed `rain_ingested` with 9 points, 1.096 mm/h at most, and 0.881 mm in total, equal to what the event file gives. Evidence: `us-068-rain-ingested-xcom.png`, rendered from output the user pasted.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E6 (`US-044`) moved from `Reviewed` to `Done`. The user confirmed the split: the page, the Python guard, and the operator check are closed here, and the refusal at request time in the Java reader is the acceptance of `US-043` (Sprint 8). Evidence: `us-044-stale-table-check-server-output.png`. All three Sprint 7 rows (`US-041`, `US-042`, `US-044`) are `Done`, so Sprint 7 ended on 2026-10-05, 34 days before its planned end of 2026-11-08. `US-068` is still `Reviewed` in the Backlog, and `US-069` is in Sprint 8.
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E5 (`US-043`) moved from `Not started` to `Reviewed`. Built tests first: `EdgeDepthTable` (memory-mapped, same checks as the Python reader), `LatestTableSource` (follows `latest`, refuses a damaged or stale table and keeps the valid one, polls every 5 s and never over 30 s), `GraphHash` (extracted from `ExportEdges`, and the hash of the tiny test graph is pinned so the refactor cannot change it), `EdgeDepthTableTool`, and `reader-check.sh`. The shared fixture (`scripts/edge_depth/golden_fixture.py`) is read by Python and Java. 57 module tests, and a mutation that skips the hash check fails 2 tests. Left: run `reader-check.sh` on the server for the evidence. Plan: [[edge-depth-table-java-reader]].
- **2026-10-05, active.** [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E5 (`US-043`) moved from `Reviewed` to `Done`. `reader-check.sh` passed on the server: the real table matched the live graph hash, another hash was refused with both named (exit 1), and a new `latest` was loaded without a restart. Evidence: `us-043-java-reader-server-output.png`, rendered from output the user pasted. Sprint 8 has `US-050`, `US-045`, and `US-069` left.
- **2026-10-05, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R5 (`US-050`) moved from `Not started` to `Reviewed`. Built tests first: `StickyClosure`, `TimeAwareDijkstra` (labels of weight and time, with a dominance rule), `StickyChecker`, `TimeAwareRouter` (hooks into `route()` for a request with the hint `td_departure` on a profile with `td_limit_cm`), and `ScenarioReport` with `scenario-check.sh`. 98 module tests. Skipping the dominance rule, never closing, dropping the virtual-edge mapping, a fixed limit, and an excluded window end each fail a test. Left: `scenario-check.sh` on the server for the evidence. Out of scope here and in `US-052`: the server flag, the request clock, the fallback flag, and wiring the table source. Plan: [[time-aware-weighting-and-search]].
- **2026-10-05, active.** [[EP-09-time-aware-routing-engine|time-aware-routing-engine-stories]] Story R5 (`US-050`) moved from `Reviewed` to `Done`. `scenario-check.sh` passed on the server: 16 of 16 runs match the sticky column with 0 crossings. Evidence: `us-050-scenario-check-server-output.png`, rendered from output the user pasted. Sprint 8 has `US-045` and `US-069` left, and both need the DAG unpaused.
- **2026-10-05, active.** Sprint 8 ended on 2026-10-05, 41 days before its planned end of 2026-11-15, as Sprints 5 to 7 did. `US-043` and `US-050` are `Done`. `US-045` and `US-069` are carried to the Backlog in `TODOS.md`, because both need the DAG unpaused for the 48-hour replay (start `2026-10-05T15:15:00Z`, 22:15 +07), which the user will switch on after the build wave. Their rows here keep their status. The timing report for `US-045` (`table_timing.ps1`) and the storage reader for `US-069` (`read_storage.ps1`) are built, and the 0-hour storage reading is taken. Sprint 9 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] started the same day.
- **2026-10-05, active.** Sprint 8 started on 2026-10-05, 35 days before its planned start of 2026-11-09, at the user's request. Its rows are `US-050` (the time-aware weighting and search), `US-043` (the Java reader with the hash check), `US-045` (prove the table on the server), and `US-069` (the storage check, which needs the DAG unpaused for 48 hours). `US-045` also needs a live DAG run of the new tasks to measure the table task against the 5-minute limit, so it needs the DAG unpaused too. No blocker stops Sprint 9 (`US-052`, `US-051`, `US-053` in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]), checked on 2026-10-05.
- **2026-10-08, active.** `US-069` is checked on the 12-hour replay, from hour 6 to hour 12, not on 24 and 48 hours (D-015, the user's decision). Its row and acceptance are unchanged otherwise.
- **2026-10-09, active.** `US-045` is `Done`. The 12-hour replay gave 45 runs with a gap of 2.69 to 3.91 minutes after `3_calculate_depth`, spot check 160 of 160. Details in the row above and in [[EP-08-edge-depth-table|edge-depth-table-stories]].
