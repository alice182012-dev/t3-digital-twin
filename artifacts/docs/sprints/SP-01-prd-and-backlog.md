---
date: 2026-09-23
type: plan
status: active
plan_number: 1
start_date: 2026-09-21
end_date: 2026-10-18
tags: [user-story, sprint-plan]
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[EP-01-frontend-depth-features|frontend-depth-features]]", "[[US-001-depth-forecast-chart|depth-forecast-chart]]", "[[US-017-route-forecast-query|route-forecast-query]]", "[[US-022-truck-routing-profile|truck-routing-profile]]", "[[EP-05-mockup-screen-coverage|mockup-screen-coverage]]", "[[EP-07-carried-over-backlog|carried-over-backlog]]"]
---
# Sprint plan: PRD backlog, 2026-09

Nineteen stories, drawn from [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]] and
[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]], sequenced into four sprints with nothing left unscheduled.
No team roster or calendar is connected for this project, so this plan sizes work by dependency
order and relative estimate, not by tracked capacity in hours or points per person. Revise the
per-sprint story count once real velocity is known.

Each sprint is one week, and the plan covers four sprints, so four weeks (`.claude/CLAUDE.md`, rule 10). The
sprints were re-cut on 2026-09-29 by dependency and need, see the Status history.

## Why these four sprints

Calendar, from `start_date` in the frontmatter. Each plan starts on a Monday and each sprint runs Monday to Sunday.

| Sprint | Start | End | Actual start | Actual end |
| ------ | ----- | --- | ------------ | ---------- |
| 1 | 2026-09-21 | 2026-09-27 |  |  |
| 2 | 2026-09-28 | 2026-10-04 |  | 2026-09-30 |
| 3 | 2026-10-05 | 2026-10-11 | 2026-09-29 | 2026-09-30 |
| 4 | 2026-10-12 | 2026-10-18 | 2026-10-01 |  |

The next plan starts on 2026-10-19.

Four sprints because a plan covers four weeks. The order comes from what each sprint unlocks, most needed first.

- **Sprint 1** built the prerequisites: the point-depth harden-first and raster-load stories, the TimescaleDB
  schema and service, and two frontend stories with no backend dependency. All `Done` or `Reviewed`.
- **Sprint 2** finishes what is started (switching routing to the new task, the tiled rasters, the netcdf table,
  the route-forecast query) and makes `GET /flood/points` fast: connection reuse, then the latency check. Sprint 3's
  per-step depth and depth badges call that endpoint once per route point, so they cannot start on an unmeasured
  endpoint. It also holds the user's decision on what the map shows, which sets the wording of Sprint 3's chart.
- **Sprint 3** builds the frontend depth features on that endpoint, the forecast chart's acceptance, the route to a
  place, and the failed-route fix (a safety gap). It ends with one pass that checks the finished screens against
  the mockup.
- **Sprint 4** runs the flood metric extractor on a real run, which no frontend story waits on, and runs the
  accessibility pass, the loading revalidation, and the per-run speed-up on the finished UI. The TimescaleDB load
  (`US-021`) was dropped on 2026-10-01.

Two rows are carried to the next plan (see that section).

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`.
`Reviewed` means the code is built and read through but its acceptance check has not run yet. Each story carries the
same Status in its epic file, as a `Status:` field on its Priority line or a Status section in a
single-story file. Update both together.

## Sprint 1: backend prerequisites and independent frontend wins

**Dates:** 2026-09-21 to 2026-09-27 (Monday to Sunday)

**Sprint goal:** every prerequisite the rest of the backlog depends on is in place, and the two
frontend stories with no backend dependency ship.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 1
SORT priority ASC, file.name ASC
```

Logged for traceability, outside the table: switching the search geocoder's default locale to `vi`
(see [[EP-02-frontend-polish|frontend-polish]]). It is `Reviewed`: place search works on the live UI and now ranks Vietnam
results correctly ([[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]], resolved 2026-09-28).

## Sprint 2: finish the raster-first pipeline and make point depth fast

**Dates:** 2026-09-28 to 2026-10-04 (Monday to Sunday)

**Sprint goal:** the raster-first pipeline is finished and verified on the server, and `GET /flood/points` is fast
enough to call once per route point, which Sprint 3's depth stories need.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 2
SORT priority ASC, file.name ASC
```

## Sprint 3: frontend depth features

**Dates:** 2026-10-05 to 2026-10-11 (Monday to Sunday)

**Sprint goal:** the frontend shows depth in the popup (done), in each turn step, on the route, and in the forecast
chart, matching the mockup, and a failed route request no longer leaves another mode's route on the map.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 3
SORT priority ASC, file.name ASC
```

## Sprint 4: flood metrics, accessibility, and loading

**Dates:** 2026-10-12 to 2026-10-18 (Monday to Sunday)

**Sprint goal:** the flood metric extractor has run on a real run, and the flood map's controls work
by keyboard and screen reader. The empty routing panel and the autofill rows moved to Sprint 3, so that pass covers the final components. The truck routing profile shipped earlier and is `Done`.

```dataview
TABLE title AS "Story", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 4
SORT priority ASC, file.name ASC
```

## Carried to the next plans

These two rows did not fit in four weeks and block nothing in this plan. They are placed in the plans that follow (dates in each plan).

| Item | Priority | Story | Estimate | Epic | Placed in | Why it waits |
| ---- | -------- | ----- | -------- | ---- | --------- | ------------ |
| US-034 | P2 | Soak the flood-road backend and check it against known answers | M | [[EP-07-carried-over-backlog|carried-over-backlog]] Story 3 | [[SP-02-routing-engine-foundations|sprint-plan-2]] Sprint 5 (2026-10-19 to 2026-10-25) | It should soak the backend after Sprint 3's changes. The user set the soak length to 48 hours on 2026-10-01. |
| US-033 | P3 | Write a project `DESIGN.md` with real design tokens | M | [[EP-07-carried-over-backlog|carried-over-backlog]] Story 2 | No sprint yet. Carried to plan 5 ([[SP-04-frontend-recheck|sprint-plan-4]]), moved from Sprint 12 on 2026-10-08 | P3, and it blocks nothing. The finished UI of Sprint 3 gives it real components to extract from. |

## Dropped

| Item | Story | Epic | Dropped | Why |
| ---- | ----- | ---- | ------- | --- |
| US-021 | Populate TimescaleDB from the extractor's output | [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Story 4 | 2026-10-01 | The pipeline does not run `background_cycle`, and the story's acceptance check needs it (D-009 in [[decision-log]]). The row left Sprint 4. The ID is not reused. |

## Risks

| Risk                                                                                                                                                                                                                                                          | Impact                                                                                                                                                                                                       | Mitigation                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /flood/points`'s latency under concurrent taps (Sprint 2) comes back too slow for a live raster query.                                                                                                                                                 | Sprint 3's three stories would need a pre-computed lookup grid instead, a larger change than currently scoped, pushing Sprint 3 out.                                                                         | Run the latency validation story early in Sprint 2, not last, so a redesign decision has runway before Sprint 3 starts.                                     |
| The flood metric extractor (Sprint 4, estimated L) runs long, since it computes five distinct metrics (time-to-peak, recession onset, per-vehicle passability restoration, T+1h and T+2h forecast depth, pre-closure time) per road segment per vehicle type. | The extractor's real-run check slips, which does not block Sprint 3 (frontend work depends on`GET /flood/points`, not on the extractor), but slips [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]'s own definition of done. The extractor ran on a real run on 2026-10-01, so this risk is closed.                                        | Tracked as its own story, so a slip was visible and isolated instead of hiding inside a bundled estimate. |
| No team roster or velocity data is connected to this plan.                                                                                                                                                                                                    | Sprint boundaries above are dependency-ordered, not capacity-checked, so a sprint could be over- or under-loaded for the actual team size.                                                                   | Revise the per-sprint story count once real velocity from Sprint 1 is known, rather than trusting the estimate column blind.                                |
| The route-forecast query is built on the raster, not `flood_road_values`, so segment matching no longer applies. Its mean depth has not been checked against a hand calculation.                                                                          | The chart could show a plausible but wrong average, a wrong number that does not look like a failure.                                                                                                        | Check one column against `flood_depth_raster_tile` by hand before either story moves to `Done`.                                                            |
| The three point-depth stories in Sprint 3 need many `GET /flood/points` calls per route, and each call opens a new database connection ([[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]]). The latency check ([[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 4) has not run. | A route with dozens of steps and badges could be slow enough to fail the interactive budget, and no budget is set.                                                                                           | Fix the connection cost, run the Story 4 check on a 40-point route, and add a batch endpoint only if it fails. See [[frontend-todos-and-backend-dependencies]]. |

## Definition of done

A story is `Done` only when its row carries evidence and details, and its epic file carries the same.
**Evidence** is a screenshot of that story working, saved under `evidence/` next to this file. A UI
story gets a screenshot of the running UI. A backend story with no UI gets a screenshot of the real
output: the endpoint's response in a browser, or the verbatim command output rendered to an image
whose caption says so and gives the capture time and host. Capture it where the acceptance criteria
name, the server when they say server. **Details** are a numbered list: 1. what was built, 2. how, 3. why,
4. what it changes for dependent stories and open blockers, and more points if needed. In an epic
file, write a real numbered list. In a table cell, separate the items with `<br />`. A built story without evidence stays `Reviewed`.

Per sprint, the same as each story's own acceptance criteria (see each epic file), plus: the
story's `status` frontmatter moves to `done`, and a dated bullet is added to its epic file's
Status history.

## Status history

Story-level progress lines up to 2026-10-10 are in [[SP-01-prd-and-backlog-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-23, active.** Drafted from [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]] and
  [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]'s Goals sections.
- **2026-09-23, active.** Moved [[US-001-depth-forecast-chart|depth-forecast-chart]] out of the backlog into Sprint 3, and
  added [[US-017-route-forecast-query|route-forecast-query]] to Sprint 2: `flood_road_values` already holds the forecast
  chart's data, reversing the earlier "no data source" conclusion. See
  [[lessons#L-009|verify-table-capability-against-write-path-not-summary-or-current-query]].
- **2026-09-23, active.** Added a Status column to every sprint table. Marked the harden-first
  story and the raster-load story (commit `118e04a`) `Done`. Every other story is `Not started`.
- **2026-09-23, active.** Added the `Reviewed` status. Marked the TimescaleDB schema and service
  stories `Reviewed`, pending the remote-host check.
- **2026-09-23, active.** Added Sprint 4 with [[US-022-truck-routing-profile|truck-routing-profile]], at the user's request.
  This extends the plan instead of starting `sprint-plan-2.md`, to keep every story's Status in
  one file.
- **2026-09-24, active.** Mapped mockup screens 2a to 2f to stories in [[EP-05-mockup-screen-coverage|mockup-screen-coverage]].
  Added two stories: a verification story in Sprint 2 and the popup's route button in Sprint 3.
  No existing story was duplicated.
- **2026-09-24, active.** Added an Evidence column and a Details column to every sprint table, and
  the evidence rule to the definition of done. Backfilled evidence for the seven stories that were
  `Done`. The geocoder locale story in [[EP-02-frontend-polish|frontend-polish]] moved to `Blocked`, because its evidence
  check found that place search fails on the live UI ([[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]).
- **2026-09-24, active.** Changed Details to a numbered list (1. what, 2. how, 3. why, 4. effect),
  joined with `<br />` in table cells and written as a real list in each epic file.
- **2026-09-24, active.** Added five stories to Sprint 2 from [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]]: roads
  in PostGIS, tiled rasters, flood on roads, retiring the GeoJSON tasks, and the netcdf schema fix.
  Sprint 2 is now the largest sprint. Rebalance if capacity is short.
- **2026-09-25, active.** [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Story 3 now stores the maximum in `depth` (D-006). The `depth_max` column is dropped.
- **2026-09-25, active.** [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Story 4 (still `In progress`): bucket and old table deleted on the server, `flood_on_roads` written in place for one run, graded routing confirmed.
- **2026-09-28, active.** [[EP-02-frontend-polish|frontend-polish]]'s geocoder locale story moved from `Blocked` to
  `Reviewed`: the backend now biases and filters `/geocode` results to Vietnam
  ([[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]], resolved).
- **2026-09-29, active.** [[EP-01-frontend-depth-features|frontend-depth-features]] Story 1 (place-depth popup, Sprint 3) is `Done`, with server
  evidence. It added `GET /places/reverse`. See [[place-depth-popup-on-map-tap]].
- **2026-09-29, active.** Sprint 3 now starts with two backend rows: reuse database connections in `floodmap-backend`
  (from `TODOS.md`, previously unscheduled) and the `GET /flood/points` latency check ([[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]
  Story 4, moved from Sprint 2, where it never started). The per-step depth and depth badge stories depend on both.
  See [[frontend-todos-and-backend-dependencies]], todo 9.
- **2026-09-29, active.** Re-cut Sprints 2 to 4 by dependency and need, at the user's request. Moved to Sprint 2:
  connection reuse and the latency check (from Sprint 3). Moved to Sprint 3: the verification of the first-load,
  empty-panel, and autofill screens (from Sprint 2), so one pass checks the finished screens. Moved to Sprint 4: the
  metric extractor and the TimescaleDB population (from Sprint 2, since no frontend story waits on them), the
  accessibility pass, and the loading revalidation. Carried to the next plan: the backend soak and comparison, and
  `DESIGN.md`. Sprint 2 now holds 10 rows, 3 `Done`.
- **2026-09-29, active.** Scheduled the remaining unscheduled `TODOS.md` items at the user's request. Sprint 2 gained five
  rows from a new epic, [[EP-07-carried-over-backlog|carried-over-backlog]]: accessibility, the soak and comparison, the "what the map shows"
  decision, `DESIGN.md`, and revalidating "loading is very slow". Sprint 3 gained the failed-route story
  ([[EP-02-frontend-polish|frontend-polish]] Story 4) and tap-a-turn-step ([[EP-01-frontend-depth-features|frontend-depth-features]] Story 4). Tap-a-turn-step could not go
  in Sprint 2 because it needs per-step depth. The "Not scheduled" table is gone. Sprint 2 is now the largest sprint.
- **2026-09-29, active.** Added an unscheduled story, [[EP-02-frontend-polish|frontend-polish]] Story 4, for
  [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]]. Fix deferred by the user.
- **2026-09-29, active.** Reconciled the plan with the code at `main` (`88070cd`). [[US-017-route-forecast-query|route-forecast-query]]
  (Sprint 2) and [[US-001-depth-forecast-chart|depth-forecast-chart]] (Sprint 3) were built on 2026-09-26 as `POST /flood/forecast`
  and `DepthForecastChart`, from the raster in 15-minute columns, not from `flood_road_values` in
  30-minute columns. Both move from `Not started` to `Reviewed`, with no evidence yet. The three
  point-depth stories in Sprint 3 stay `Not started`: no frontend code calls `GET /flood/points`. Their
  dependencies now name the latency check and the many-points decision. The risk row on segment
  matching is replaced, and a risk row on point-depth latency is added. The "Updated" line in
  [[EP-02-frontend-polish|frontend-polish]] Story 2 now reads "As of" or "Forecast for" in the code. See
  [[frontend-todos-and-backend-dependencies]].
- **2026-09-29, active.** Added dates. Sprint 1 starts on 2026-09-21, a Monday, and each sprint runs Monday to Sunday, so Sprint 2 is 2026-09-28 to 2026-10-04,
  Sprint 3 is 2026-10-05 to 2026-10-11, and Sprint 4 is 2026-10-12 to 2026-10-18. Sprint 1 started two days before this plan was drafted on 2026-09-23. The user can move
  the start date, and every date shifts with it.
- **2026-09-29, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 5 is `Reviewed`, not `Done`, until a screenshot of the recorded decision is saved as evidence (rule 8): the user decided to keep narrowing the
  1.5 to 3 minute publish delay ([[five-minute-tile-freshness]] option D) rather than accept it or commit to
  option E. Added Story 6 (the option D work) to Sprint 4.
- **2026-09-29, active.** Sprint 2 is effectively closed: six rows moved to `Done` in one live-server
  session with direct access to the running containers (`docker ps` on the default context, not the
  `remote-server` SSH context CLAUDE.md describes, since this session runs directly on the host that
  context would have pointed at). Switch routing/retire GeoJSON, tiled rasters, the route-forecast
  query, connection pooling, the latency validation, and the netcdf table all moved from
  `In progress`/`Reviewed`/`Not started` to `Done`, each with fresh server evidence
  (`raster-first-pipeline-sprint2-verification.png`,
  `connection-pooling-and-forecast-verification.png`). Only "decide what the map shows by default"
  remains `Not started` on this branch specifically; it was decided on a separate branch
  ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 5, `decide-map-default-freshness-option`) not yet merged here.
- **2026-09-30, active.** Added [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 5 to Sprint 2 as `Reviewed`: the pooled backend
  returns HTTP 400 at 30 concurrent requests, past the 10 concurrent requests that the latency row measured. The fix is deployed
  and measured on the server (all 200 at 30 and 60 concurrent). Sprint 2 now holds 11 rows.
- **2026-09-30, active.** Added [[EP-02-frontend-polish|frontend-polish]] Story 5 to Sprint 3 as P0, In progress: a route whose description is a list blanks the whole app ([[BL-017-route-description-list-blanks-app|route-description-list-blanks-app]]), found while checking the place popup's route button.
- **2026-09-30, active.** [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 1 (route to a place) and [[EP-02-frontend-polish|frontend-polish]] Story 5 (blank app on a list description) are `Reviewed`: built, tested, and checked on a preview build on the server. Both move to `Done` once the frontend is deployed.
- **2026-09-30, active.** Rule 11 (`.claude/CLAUDE.md`) applied to [[BL-019-test-server-tile-edge-check-fails|test-server-tile-edge-check-fails]]: it blocks no story of Sprint 4, since none reads `test_server.py`, so a subagent fixes it while work continues. Added as [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 6 in Sprint 3, P3, In progress. It would matter to the Sprint 5 backend soak, and the fix lands well before then.
- **2026-09-30, active.** Added [[EP-07-carried-over-backlog|carried-over-backlog]] Story 7 to Sprint 3 as P3, In progress: the README rewrite found `.env.example`, a dead link name, a self-contradicting concept page, and a stale `PINNED_COMMIT.md` ([[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]]). Rule 11 case: it blocks no further build, so a subagent fixes it.
- **2026-09-30, active.** The user placed [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Stories 3 and 4 (`US-025`, `US-026`) in Sprint 4, as P3 and size S each, ahead of the accessibility story (`US-032`), which now waits for them so it covers the final labels. Sprint 4 now holds 8 rows, 1 `Done`.
- **2026-09-30, active.** Added [[EP-02-frontend-polish|frontend-polish]] Story 6 (`US-057`) to Sprint 3 as P2, XS, In progress. The user asked to drop the red "Connection between locations not found" bar, since the yellow "No safe route available" box already says it. It refines `US-009`.
- **2026-09-30, active.** Added [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 5 (`US-058`) to Sprint 3 as P2, S, Not started. The user described a tap-only flow: tap a point, click the popup arrow to set the destination (`US-023`), tap another point, and it fills From. It follows `US-023` like `US-057` follows `US-009`, so it sits in Sprint 3. Move it if you want another sprint.
- **2026-09-30, active.** The user moved [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Stories 3 and 4 (`US-025`, `US-026`) from Sprint 4 to Sprint 3, both P3 and size S, Not started. Sprint 3 now has 10 `Done` rows, 1 `Reviewed` row (`US-038`), and 3 `Not started` rows (`US-058`, `US-025`, `US-026`). Sprint 4 keeps `US-032`, which still waits on them.
- **2026-09-30, active.** Added [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 6 (`US-059`) to Sprint 3 as P2, XS, Not started: after the arrow empties From, the panel shows the yellow "No safe route available" box. It is a follow-up to `US-058` like `US-057` to `US-009`. Blocker: [[BL-016-no-safe-route-box-shown-with-empty-start|no-safe-route-box-shown-with-empty-start]]. Rule 11: it blocks no story of Sprint 4, since none reads the routing panel's empty state, so it can be fixed in Sprint 3 without gating other work.
- **2026-09-30, active.** Blocker check for Sprints 4 to 12: no logged blocker stops a story. Added [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Story 5 (`US-060`) to Sprint 4 as P1, XS, Not started, ahead of `US-021`: the extractor (`US-020`) has never run on real data, and the server holds retained runs to run it on. [[EP-07-carried-over-backlog|carried-over-backlog]] Story 4 (`US-035`) now also times the routing panel's wait for a no-connection pair. [[BL-011-routing-not-time-aware|routing-not-time-aware]] has a dated entry with its four gates.
- **2026-09-30, active.** Added Actual start and Actual end columns to the timeline table. Sprint 2 ended on 2026-09-30 with all 11 rows `Done`. Sprint 3 started on 2026-09-29, when the plan was re-cut and its first backend rows opened. Sprint 1 and Sprint 2 start dates were not recorded.
- **2026-10-01, active.** The carried row `US-034` dropped its Valhalla comparison and now checks GraphHopper against the vehicle depth limits, because the Valhalla model was wrong when it ran. The user set the soak length to 48 hours. See [[EP-07-carried-over-backlog|carried-over-backlog]] Story 3 and [[SP-02-routing-engine-foundations|sprint-plan-2]] Sprint 5.
- **2026-10-01, active.** Sprint 4 started on 2026-10-01, 11 days before its planned start. [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Stories 5 and 3 (`US-060`, `US-020`) moved to `Done`: `extract_run.py` ran on the 2026-09-30 02:00:00 run in the Airflow worker, and `us-060-extractor-check.sh` shows 5,831 segments equal to the run's distinct `geom_4326` values and `peak_depth_m` equal to the source maximum for all of them. The output is rendered as `us-060-extractor-check-output.png`. Sprint 4 has 2 `Done` rows and 4 open.
- **2026-10-01, active.** [[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]] Story 4 (`US-021`) is `Dropped`, replacing the `Blocked` entry above. The user said the pipeline no longer runs `background_cycle`, so the story cannot pass (D-009 in [[decision-log]]). The row left the Sprint 4 table and is listed under "Dropped". The Sprint 4 title, goal, and one risk row no longer mention loading TimescaleDB. Sprint 4 now has 6 rows: 3 `Done` (`US-020`, `US-060`, `US-022`), 1 `In progress` (`US-032`), and 2 not started (`US-035`, `US-037`).
- **2026-10-01, active.** [[SP-02-routing-engine-foundations|sprint-plan-2]] Sprint 5 started today while `US-037` is still `In progress`. Sprint 4's Actual end stays empty until `US-037` is `Done`. `US-037` blocks no Sprint 5 row. Sprint 4 has 5 `Done` rows and 1 open.
- **2026-10-02, active.** Sprint 4 is finished. All 6 rows are `Done`, and the Actual end in the timeline table is 2026-10-02, against a planned end of 2026-10-18. Sprint 5 is already running since 2026-10-01 ([[SP-02-routing-engine-foundations|sprint-plan-2]]).
- **2026-10-02, active.** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 6 (`US-037`) moved from `Done` back to `In progress`. The user stopped the pipeline, because the constant 50 mm/h test rain is not a real event, and the first pass covers only the first hour of such a storm. Sprint 4 has 5 `Done` rows and 1 open, so its Actual end of 2026-10-02 is cleared. The retest runs the 48-hour rain replay of `US-063` ([[SP-02-routing-engine-foundations|sprint-plan-2]] Sprint 5). The first measurement stays in the row's Details.
