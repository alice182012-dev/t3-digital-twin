---
date: 2026-09-23
type: plan
status: active
plan_number: 1
start_date: 2026-09-21
end_date: 2026-10-18
tags: [user-story, sprint-plan]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[t3-digital-twin-architecture-gaps]]", "[[point-depth-lookup-backend]]", "[[timescaledb-and-flood-metrics]]", "[[frontend-polish]]", "[[frontend-depth-features]]", "[[depth-forecast-chart]]", "[[route-forecast-query]]", "[[truck-routing-profile]]", "[[mockup-screen-coverage]]", "[[carried-over-backlog]]"]
---
# Sprint plan: PRD backlog, 2026-09

Nineteen stories, drawn from [[flood-routing-mockup-frontend-gap]] and
[[t3-digital-twin-architecture-gaps]], sequenced into four sprints with nothing left unscheduled.
No team roster or calendar is connected for this project, so this plan sizes work by dependency
order and relative estimate, not by tracked capacity in hours or points per person. Revise the
per-sprint story count once real velocity is known.

Each sprint is one week, and the plan covers four sprints, so four weeks (`.claude/CLAUDE.md`, rule 10). The
sprints were re-cut on 2026-09-29 by dependency and need, see the Status history.

## Why these four sprints

Calendar, from `start_date` in the frontmatter. Each plan starts on a Monday and each sprint runs Monday to Sunday.

| Sprint | Start | End |
| ------ | ----- | --- |
| 1 | 2026-09-21 | 2026-09-27 |
| 2 | 2026-09-28 | 2026-10-04 |
| 3 | 2026-10-05 | 2026-10-11 |
| 4 | 2026-10-12 | 2026-10-18 |

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
- **Sprint 4** loads the flood metrics into TimescaleDB, which no frontend story waits on, and runs the
  accessibility pass and the loading revalidation on the finished UI.

Two rows are carried to the next plan (see that section).

Each story's Status is `Not started`, `In progress`, `Reviewed`, `Blocked`, or `Done`.
`Reviewed` means the code is built and read through but its acceptance check has not run yet. Each story carries the
same Status in its epic file, as a `Status:` field on its Priority line or a Status section in a
single-story file. Update both together.

## Sprint 1: backend prerequisites and independent frontend wins

**Dates:** 2026-09-21 to 2026-09-27 (Monday to Sunday)

**Sprint goal:** every prerequisite the rest of the backlog depends on is in place, and the two
frontend stories with no backend dependency ship.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| -------- | ------------------------------------------------------------ | -------- | ---- | -------------------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| P0 | Regression-harden `floodmap-backend` before adding new load | M | [[point-depth-lookup-backend]] | None | ![[harden-floodmap-backend-tests.png\|120]] | 1. What: regression tests for `server.py` and `flood_areas.py`.<br />2. How: `test_flood_areas.py` and `test_server.py` run against a real PostGIS and a stub GraphHopper.<br />3. Why: `GET /flood/points` would otherwise land on an unproven backend.<br />4. Effect: unblocks the point-depth stories. The soak period and the Valhalla comparison stay open in `TODOS.md`. | Done |
| P0 | Load `depth.tif` into PostGIS as a raster | M | [[point-depth-lookup-backend]] | None | ![[depth-raster-postgis-load.png\|120]] | 1. What: each timestep's `depth.tif` becomes a row in `flood_depth_raster`.<br />2. How: `raster_load.py` reprojects EPSG:3405 to EPSG:4326 and loads it with `ST_FromGDALRaster`, in DAG task `9b_load_depth_raster`.<br />3. Why: a point lookup needs the exact pixel.<br />4. Effect: unblocks `GET /flood/points`. On the server, the row for run `20260924T153638` matches the source file's size and corner. The DAG task has not run there yet. | Done |
| P1 | Design TimescaleDB's histogram and forecast-series schema | S | [[timescaledb-and-flood-metrics]] | None | ![[timescaledb-schema.png\|120]] | 1. What: three hypertables and a `simulation_cycle` enum.<br />2. How: `create_timescale_tables.py`, with a `CHECK` that ties bars 1 to 6 to `constant_cycle` and bars 7 to 24 to `background_cycle`.<br />3. Why: no migration when `background_cycle` data arrives.<br />4. Effect: Story 4 loads into these tables, and must first choose a segment key, since road segments have no stable ID. | Done |
| P1 | Stand up the TimescaleDB service | S | [[timescaledb-and-flood-metrics]] | Schema design story, same sprint | ![[timescaledb-service.png\|120]] | 1. What: a `timescaledb` container apart from `storage-postgres`.<br />2. How: `compose.yml`, image `timescale/timescaledb:2.30.1-pg17`, bound to `127.0.0.1:5434`.<br />3. Why: the extractor's output needs a time-series store.<br />4. Effect: `compose.yml` requires `TIMESCALE_PASSWORD`, so every compose command fails without it. The image comes from Docker Hub. | Done |
| P2 | Add per-mode travel time under the four mode icons | M | [[frontend-polish]] | None | ![[frontend-per-mode-travel-time.png\|120]] | 1. What: a travel time under each mode icon, with the selected mode in bold. How:`useProfileTimes` sends one route request per profile for each query.<br />2. Why: compare modes without switching.<br />3. Effect: four requests per query. Truck is missing until Sprint 4, and every mode uses the motorbike flood limit ([[flood-routing-vehicle-type-always-motorbike]]). | Done |
| P2 | Add the "Updated `date` `time`" line to the flood legend | S | [[frontend-polish]] | None | ![[frontend-legend-updated-line.png\|120]] | 1. What: an "Updated" line under the legend bands. How:`FloodLegend` formats the selected timestep with `formatTimestepTime`, in the viewer's local time.<br />2. Why: it shows how current the flood data is.<br />3. Effect: the legend is one line taller, and the mobile search panel covers it ([[mobile-flood-legend-covered-by-search-panel]]). | Done |

Logged for traceability, outside the table: switching the search geocoder's default locale to `vi`
(see [[frontend-polish]]). It is `Reviewed`: place search works on the live UI and now ranks Vietnam
results correctly ([[photon-rejects-vi-locale]], resolved 2026-09-28).

## Sprint 2: finish the raster-first pipeline and make point depth fast

**Dates:** 2026-09-28 to 2026-10-04 (Monday to Sunday)

**Sprint goal:** the raster-first pipeline is finished and verified on the server, and `GET /flood/points` is fast
enough to call once per route point, which Sprint 3's depth stories need.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| P0 | Build `GET /flood/points` | M | [[point-depth-lookup-backend]] | Sprint 1's harden and raster-load stories | ![[flood-points-endpoint.png\|120]] | 1. What:`GET /flood/points` returns the depth at a lat/lon and timestep.<br />2. How: `flood_points.py` reads `flood_depth_raster` with `ST_Value`. A pixel of 0 reads `dry`, and a point outside the raster reads `no_data`.<br />3. Why: the popup and badges need the exact pixel, not a band.<br />4. Effect: unblocks the latency check and the three Sprint 3 point stories. Without `run=`, it returns 404 when the newest run has no raster. On a real `depth.tif`, it matched `gdallocationinfo` at three points. | Done |
| P0 | Load the roads into PostGIS with a stable segment ID | M | [[raster-first-pipeline-stories]] | None | ![[road-segment-server-check.png\|120]] | 1. What: a `road_segment` table with one row per road piece, keyed by `segment_id` such as `way/11835354#0`.<br />2. How: `load_road_segments.py` cuts each of the 12,431 ways into equal pieces of at most 50 m in EPSG:3405 and upserts them in one transaction.<br />3. Why: routing data, TimescaleDB, and the route-forecast query need one stable road ID, and the old mapping step dropped the OSM id.<br />4. Effect: it feeds the DAG tasks and the TimescaleDB key change. On the server (2026-09-25): 35,652 pieces, every way present, worst length error 0.000000000 m, and a second load changed nothing. IDs shift if the roads file or the piece length changes. | Done |
| P0 | Compute flood on roads from the raster into a shadow table | L | [[raster-first-pipeline-stories]] | Stories 1 and 2 of the new epic | ![[flood-on-roads-server-check.png\|120]] | 1. What: a task that computes each road piece's flood depth from the raster tiles into `flood_road_values`. `depth` is the deepest 1 m sample (D-006).<br />2. How: `flood_on_roads.compute` samples every metre along each piece that touches a wet tile, reads the wet pixels once per tile, and writes one row per piece per timestep in one transaction.<br />3. Why: the old chain sampled one pixel per 20 m cell on the server (`SAMPLE_RATE=20`), so about half of its wet slivers are dry along the road.<br />4. Effect: on the server (2026-09-25), run `20260924T164803` wrote 8,444 rows into a shadow table in 18.8 s, identical to the local result in rows, wet pieces, and depth sums, while the real table stayed untouched. Routing, the extractor, and the metrics read the same `depth`. Writing in place and a full cycle remain in Story 4. | Done |
| P0 | Switch routing to the new task and retire the GeoJSON tasks | M | [[raster-first-pipeline-stories]] | Story 3 of the new epic | ![[graded-routing-server-check.png\|120]] | 1. What: the DAG no longer builds GeoJSON. It loads roads and computes flood on roads into `flood_road_values`, the table routing reads.<br />2. How: `stage-b` removes tasks 4 to 8, `dags/test_dag.py`, and the `flood-results-full` configuration, and adds the `load_road_segments` and `flood_on_roads` tasks. On the server the bucket (15 objects, 14.7 MB) and the old `flood_depth_raster` table (122 MB) were deleted, and `flood_on_roads` was written in place for run `20260924T164803`.<br />3. Why: one path from the depth rasters to routing, with the raster as the source of truth.<br />4. Effect: routing now reads the new rows. Graded routes detour around flooded pieces (for example 111 m becomes 6,262 m around a 2.76 m piece), and two test routes have no connection once the flood applies. Still open: a full DAG cycle, the frontend on a live event (the state-test DAG will provide one, see D-007), deleting the old scripts, and removing the test shadow table. | In progress |
| P0 | Store depth rasters as tiles and read them through a spatial index | M | [[raster-first-pipeline-stories]] | None | ![[raster-tiles-server-check.png\|120]] | 1. What: each timestep's depth raster is stored as 256 by 256 tiles in `flood_depth_raster_tile`, read through a spatial index, and runs older than the newest 3 are pruned.<br />2. How: `load_run` reprojects to EPSG:4326 and cuts tiles with `ST_Tile` in one delete-and-insert transaction. `GET /flood/points` selects the tile under the point, then runs `ST_Value`.<br />3. Why: the whole-raster lookup unpacked 209 MB per request and took 80 to 280 ms on the server.<br />4. Effect: deployed on 2026-09-24 (commit `6155f09`). On the server a tile lookup takes a median of 0.56 ms in the database, and a full request about 81 ms, because each request opens a new connection ([[flood-points-connection-per-request]]). Retention has not run on the server, since only one run has tiles, so the story stays `Reviewed`. | Reviewed |
| P1 | Build the route-forecast query (`POST /flood/forecast`, from the raster tiles) | M | [[route-forecast-query]] | Sprint 1's harden-first story | None yet | 1. What: `POST /flood/forecast` returns the mean depth along a route per 15-minute column.<br />2. How: `flood_forecast.py` samples the polyline (at most 200 samples) and reads `flood_depth_raster_tile`, taking each column from the newest run that has it.<br />3. Why: the raster is the source of truth, and it needs no stable road segment ID.<br />4. Effect: [[depth-forecast-chart]] no longer waits on it. On the server a 5-point route returned 13 columns in 1.5 s. The endpoint tests have not run against a real PostGIS, and no hand-checked column or screenshot exists. | Reviewed |
| P1 | Reuse database connections in `floodmap-backend` | S | [[flood-points-connection-per-request]] (`TODOS.md` item) | None. The tiled raster story it needed is deployed | None yet | - | Not started |
| P0 | Validate `GET /flood/points`'s latency under concurrent taps | S | [[point-depth-lookup-backend]] Story 4 | The connection row above, and a latency budget the user sets | None yet | - | Not started |
| P2 | Decide what the map shows by default, and close or schedule the latency work | S | [[carried-over-backlog]] Story 5 | None. Needs the user's decision | None yet | - | Not started |
| P2 | Create the netcdf table in the schema task | S | [[raster-first-pipeline-stories]] | None | None yet | 1. What: the netcdf tables are created by the schema task.<br />2. How: `task_ensure_schema` calls `create_netcdf_tables.create_tables()`, which is idempotent.<br />3. Why: `3b_upload_netcdf_postgres` failed with `relation "netcdf_files" does not exist`, which marked every run `failed`.<br />4. Effect: on the server the three netcdf tables now exist, created by hand on 2026-09-25 with the same function (run twice). The story stays `Reviewed` until a real cycle shows task 3b succeeding. | Reviewed |

## Sprint 3: frontend depth features

**Dates:** 2026-10-05 to 2026-10-11 (Monday to Sunday)

**Sprint goal:** the frontend shows depth in the popup (done), in each turn step, on the route, and in the forecast
chart, matching the mockup, and a failed route request no longer leaves another mode's route on the map.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| P0 | Place-depth popup on map tap | M | [[frontend-depth-features]] | `GET /flood/points` (done), Sprint 2's latency check (not started), and a reverse-geocoding source | ![[frontend-place-depth-popup-wet.png\|120]] | 1. What: a card at the tapped point in Flood mode with place name, address, coordinates, and the water depth, plus `GET /places/reverse`.<br />2. How: `ContextMenu.tsx` passes a plain click to `PlaceDepthPopup`, which calls `GET /flood/points` (selected step and run) and `GET /places/reverse` independently.<br />3. Why: a user can judge water at any point, not only along a route.<br />4. Effect: on the server a wet point read 205 cm, matching the endpoint's 2.048 m. Map mode keeps the context menu. Place lookup takes about 1.1 to 1.4 s (Photon). The latency check story has not run, and the route button is a separate story. | Done |
| P0 | Per-step depth in turn-by-turn instructions | S | [[frontend-depth-features]] | `GET /flood/points` (done), and Sprint 2's connection and latency rows | None yet | - | Not started |
| P0 | Per-point depth badges along the route polyline | M | [[frontend-depth-features]] | Sprint 2's connection and latency rows | None yet | - | Not started |
| P0 | Depth-versus-time forecast chart | M | [[depth-forecast-chart]] | Sprint 2's route-forecast query story (built) | None yet | 1. What: `DepthForecastChart` in the route panel, in 15-minute columns with the "now" column highlighted and a dashed line at the now depth.<br />2. How: `RoutingResults.tsx` renders it in flood mode, from `POST /flood/forecast`.<br />3. Why: a user can see whether depth along the route rises or falls, and decide whether to leave now or wait.<br />4. Effect: it replaces the 30-minute columns of the mockup with 15-minute ones. The chart renders on the server (2026-09-26), but no screenshot is saved, so the story stays `Reviewed`. | Reviewed |
| P1 | Show no route and a clear message when the selected mode has none | S | [[frontend-polish]] Story 4 | A small backend change: pass GraphHopper's error body through ([[failed-route-shows-previous-mode-route]]) | None yet | - | Not started |
| P1 | Route to a place from the place popup | S | [[mockup-screen-coverage]] | The place-depth popup story (Done) | None yet | - | Not started |
| P3 | Tap a turn step to highlight its segment on the map | XS | [[frontend-depth-features]] Story 4 | This sprint's per-step depth story | None yet | - | Not started |
| P2 | Verify the first-load, empty-panel, and autofill screens against the mockup | S | [[mockup-screen-coverage]] | This sprint's UI stories, so one pass checks the finished screens. Needs the frontend rebuilt on the remote host | None yet | - | Not started |

## Sprint 4: flood metrics in TimescaleDB, and accessibility

**Dates:** 2026-10-12 to 2026-10-18 (Monday to Sunday)

**Sprint goal:** the flood metrics are written to TimescaleDB from a real run, and the flood map's controls work
by keyboard and screen reader. The truck routing profile shipped earlier and is `Done`.

| Priority | Story | Estimate | Epic | Dependencies | Evidence | 1. Details | Status |
| -------- | ----- | -------- | ---- | ------------ | -------- | ---------- | ------ |
| P1 | Build the flood metric extractor | L | [[timescaledb-and-flood-metrics]] | None (reads`calculate_depth.py` output directly) | None yet | 1. What: the flood metric extractor, covered by 19 unit tests.<br />2. How: a pure function turns one segment's depth series into its metrics, and `extract_run.py` reads `flood_road_values` for a run and writes `flood_segment_metrics`.<br />3. Why: real flood-impact metrics (time to peak, recession onset, passability restoration, T+1h and T+2h depth, pre-closure time) instead of raw depth rasters alone.<br />4. Effect: it has not run against a real run, and it cannot run in Airflow until [[airflow-cannot-import-flood-utils]] is fixed. | Reviewed |
| P1 | Populate TimescaleDB from the extractor's output | M | [[timescaledb-and-flood-metrics]] | Sprint 1's schema and service stories, this sprint's extractor story, the `segment_id` story of the new epic, [[airflow-cannot-import-flood-utils]] | None yet | - | Not started |
| P2 | Make the map toggle, legend, and route tabs usable by keyboard and screen reader | S | [[carried-over-backlog]] Story 1 | Sprint 3's UI changes settle first, so the pass covers the final components | None yet | - | Not started |
| P3 | Revalidate "loading is very slow" | S | [[carried-over-backlog]] Story 4 | Sprint 2's connection reuse and Sprint 3's features, so it measures the app as it ships | None yet | - | Not started |
| P2 | Show the truck routing profile in the frontend | S | [[truck-routing-profile]] | None | ![[frontend-truck-profile.png\|120]] | 1. What: `truck: {}` in `config-local.js.example`, so the profile row offers four modes.<br />2. How: rebuilt and recreated `flood-routing-frontend` on the server. The served `/config.js` lists `truck`.<br />3. Why: GraphHopper already serves `truck`, and truck drivers need the truck depth limit.<br />4. Effect: on the live UI the row shows four modes, and a truck route of 918 m returned. The per-mode travel time row now sends four requests per query. | Done |

## Carried to the next plans

These two rows did not fit in four weeks and block nothing in this plan. They are placed in the plans that follow (dates in each plan).

| Priority | Story | Estimate | Epic | Placed in | Why it waits |
| -------- | ----- | -------- | ---- | --------- | ------------ |
| P2 | Soak the flood-road backend and compare it with the earlier backend | M | [[carried-over-backlog]] Story 3 | [[sprint-plan-2]] Sprint 5 (2026-10-19 to 2026-10-25) | It needs the user's soak length and route set, and it should soak the backend after Sprint 3's changes. |
| P3 | Write a project `DESIGN.md` with real design tokens | M | [[carried-over-backlog]] Story 2 | [[sprint-plan-3]] Sprint 11 (2026-11-30 to 2026-12-06) | P3, and it blocks nothing. The finished UI of Sprint 3 gives it real components to extract from. |

## Risks

| Risk                                                                                                                                                                                                                                                          | Impact                                                                                                                                                                                                       | Mitigation                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /flood/points`'s latency under concurrent taps (Sprint 2) comes back too slow for a live raster query.                                                                                                                                                 | Sprint 3's three stories would need a pre-computed lookup grid instead, a larger change than currently scoped, pushing Sprint 3 out.                                                                         | Run the latency validation story early in Sprint 2, not last, so a redesign decision has runway before Sprint 3 starts.                                     |
| The flood metric extractor (Sprint 4, estimated L) runs long, since it computes five distinct metrics (time-to-peak, recession onset, per-vehicle passability restoration, T+1h and T+2h forecast depth, pre-closure time) per road segment per vehicle type. | TimescaleDB population slips, which does not block Sprint 3 (frontend work depends on`GET /flood/points`, not on TimescaleDB), but slips [[timescaledb-and-flood-metrics]]'s own definition of done.                                        | Track it as its own story rather than folding it into the TimescaleDB story, so a slip is visible and isolated instead of hiding inside a bundled estimate. |
| No team roster or velocity data is connected to this plan.                                                                                                                                                                                                    | Sprint boundaries above are dependency-ordered, not capacity-checked, so a sprint could be over- or under-loaded for the actual team size.                                                                   | Revise the per-sprint story count once real velocity from Sprint 1 is known, rather than trusting the estimate column blind.                                |
| The route-forecast query is built on the raster, not `flood_road_values`, so segment matching no longer applies. Its mean depth has not been checked against a hand calculation.                                                                          | The chart could show a plausible but wrong average, a wrong number that does not look like a failure.                                                                                                        | Check one column against `flood_depth_raster_tile` by hand before either story moves to `Done`.                                                            |
| The three point-depth stories in Sprint 3 need many `GET /flood/points` calls per route, and each call opens a new database connection ([[flood-points-connection-per-request]]). The latency check ([[point-depth-lookup-backend]] Story 4) has not run. | A route with dozens of steps and badges could be slow enough to fail the interactive budget, and no budget is set.                                                                                           | Fix the connection cost, run the Story 4 check on a 40-point route, and add a batch endpoint only if it fails. See [[frontend-todos-and-backend-dependencies]]. |

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

- **2026-09-23, active.** Drafted from [[flood-routing-mockup-frontend-gap]] and
  [[t3-digital-twin-architecture-gaps]]'s Goals sections.
- **2026-09-23, active.** Moved [[depth-forecast-chart]] out of the backlog into Sprint 3, and
  added [[route-forecast-query]] to Sprint 2: `flood_road_values` already holds the forecast
  chart's data, reversing the earlier "no data source" conclusion. See
  [[verify-table-capability-against-write-path-not-summary-or-current-query]].
- **2026-09-23, active.** Added a Status column to every sprint table. Marked the harden-first
  story and the raster-load story (commit `118e04a`) `Done`. Every other story is `Not started`.
- **2026-09-23, active.** Added the `Reviewed` status. Marked the TimescaleDB schema and service
  stories `Reviewed`, pending the remote-host check.
- **2026-09-23, active.** Marked both [[frontend-polish]] stories `Reviewed`, pending a run
  against the live backend.
- **2026-09-23, active.** Added Sprint 4 with [[truck-routing-profile]], at the user's request.
  This extends the plan instead of starting `sprint-plan-2.md`, to keep every story's Status in
  one file.
- **2026-09-23, active.** Marked `GET /flood/points` and the flood metric extractor `Reviewed`,
  pending checks against real data and a real database.
- **2026-09-24, active.** Mapped mockup screens 2a to 2f to stories in [[mockup-screen-coverage]].
  Added two stories: a verification story in Sprint 2 and the popup's route button in Sprint 3.
  No existing story was duplicated.
- **2026-09-24, active.** Marked five stories `Done` after checks on the remote host: both TimescaleDB
  stories, both [[frontend-polish]] stories, and `GET /flood/points`. The flood metric extractor
  stays `Reviewed`.
- **2026-09-24, active.** Added an Evidence column and a Details column to every sprint table, and
  the evidence rule to the definition of done. Backfilled evidence for the seven stories that were
  `Done`. The geocoder locale story in [[frontend-polish]] moved to `Blocked`, because its evidence
  check found that place search fails on the live UI ([[photon-rejects-vi-locale]]).
- **2026-09-24, active.** Changed Details to a numbered list (1. what, 2. how, 3. why, 4. effect),
  joined with `<br />` in table cells and written as a real list in each epic file.
- **2026-09-24, active.** Added five stories to Sprint 2 from [[raster-first-pipeline-stories]]: roads
  in PostGIS, tiled rasters, flood on roads, retiring the GeoJSON tasks, and the netcdf schema fix.
  Sprint 2 is now the largest sprint. Rebalance if capacity is short.
- **2026-09-24, active.** TimescaleDB's Story 4 now also waits for the `segment_id` story of
  [[raster-first-pipeline-stories]] and for [[airflow-cannot-import-flood-utils]].
- **2026-09-24, active.** [[raster-first-pipeline-stories]] Story 1 (`road_segment`) is `Reviewed`.
- **2026-09-24, active.** [[raster-first-pipeline-stories]] Story 2 (tiled rasters) is `Reviewed`.
- **2026-09-24, active.** Stage A deployed to the server. [[raster-first-pipeline-stories]] Story 2 now has server evidence and stays `Reviewed` until pruning is seen there.
- **2026-09-24, active.** [[raster-first-pipeline-stories]] Story 3 (flood on roads) is `Reviewed` on `stage-b`. Decision open: whether routing filters on `depth_max`.
- **2026-09-25, active.** [[raster-first-pipeline-stories]] Story 4 is `In progress` on `stage-b`: the code is built and merged, the server deploy is not done.
- **2026-09-25, active.** [[raster-first-pipeline-stories]] Story 3 now stores the maximum in `depth` (D-006). The `depth_max` column is dropped.
- **2026-09-25, active.** Stage B checked on the server. [[raster-first-pipeline-stories]] Stories 1 and 3 are `Done` with server evidence, and Story 5 is `Reviewed`.
- **2026-09-25, active.** [[raster-first-pipeline-stories]] Story 4 (still `In progress`): bucket and old table deleted on the server, `flood_on_roads` written in place for one run, graded routing confirmed.
- **2026-09-28, active.** [[frontend-polish]]'s geocoder locale story moved from `Blocked` to
  `Reviewed`: the backend now biases and filters `/geocode` results to Vietnam
  ([[photon-rejects-vi-locale]], resolved).
- **2026-09-29, active.** [[truck-routing-profile]] (Sprint 4) is `Done`: four modes show in the live UI
  and a truck route returns. Evidence is `frontend-truck-profile.png`.
- **2026-09-29, active.** [[frontend-depth-features]] Story 1 (place-depth popup, Sprint 3) is `Done`, with server
  evidence. It added `GET /places/reverse`. See [[place-depth-popup-on-map-tap]].
- **2026-09-29, active.** Sprint 3 now starts with two backend rows: reuse database connections in `floodmap-backend`
  (from `TODOS.md`, previously unscheduled) and the `GET /flood/points` latency check ([[point-depth-lookup-backend]]
  Story 4, moved from Sprint 2, where it never started). The per-step depth and depth badge stories depend on both.
  See [[frontend-todos-and-backend-dependencies]], todo 9.
- **2026-09-29, active.** Re-cut Sprints 2 to 4 by dependency and need, at the user's request. Moved to Sprint 2:
  connection reuse and the latency check (from Sprint 3). Moved to Sprint 3: the verification of the first-load,
  empty-panel, and autofill screens (from Sprint 2), so one pass checks the finished screens. Moved to Sprint 4: the
  metric extractor and the TimescaleDB population (from Sprint 2, since no frontend story waits on them), the
  accessibility pass, and the loading revalidation. Carried to the next plan: the backend soak and comparison, and
  `DESIGN.md`. Sprint 2 now holds 10 rows, 3 `Done`.
- **2026-09-29, active.** The user set the cadence: one week per sprint and four sprints, four weeks, per plan. This plan
  already has four sprints. Sprint 2 held 15 rows, 12 still open, which looked like more than one week. The re-cut entry above fixes it. Moves go to Sprint 3 or 4, or to the next plan, and no row moves without asking.
- **2026-09-29, active.** Scheduled the remaining unscheduled `TODOS.md` items at the user's request. Sprint 2 gained five
  rows from a new epic, [[carried-over-backlog]]: accessibility, the soak and comparison, the "what the map shows"
  decision, `DESIGN.md`, and revalidating "loading is very slow". Sprint 3 gained the failed-route story
  ([[frontend-polish]] Story 4) and tap-a-turn-step ([[frontend-depth-features]] Story 4). Tap-a-turn-step could not go
  in Sprint 2 because it needs per-step depth. The "Not scheduled" table is gone. Sprint 2 is now the largest sprint.
- **2026-09-29, active.** Added an unscheduled story, [[frontend-polish]] Story 4, for
  [[failed-route-shows-previous-mode-route]]. Fix deferred by the user.
- **2026-09-29, active.** Reconciled the plan with the code at `main` (`88070cd`). [[route-forecast-query]]
  (Sprint 2) and [[depth-forecast-chart]] (Sprint 3) were built on 2026-09-26 as `POST /flood/forecast`
  and `DepthForecastChart`, from the raster in 15-minute columns, not from `flood_road_values` in
  30-minute columns. Both move from `Not started` to `Reviewed`, with no evidence yet. The three
  point-depth stories in Sprint 3 stay `Not started`: no frontend code calls `GET /flood/points`. Their
  dependencies now name the latency check and the many-points decision. The risk row on segment
  matching is replaced, and a risk row on point-depth latency is added. The "Updated" line in
  [[frontend-polish]] Story 2 now reads "As of" or "Forecast for" in the code. See
  [[frontend-todos-and-backend-dependencies]].
- **2026-09-29, active.** Added dates. Sprint 1 starts on 2026-09-21, a Monday, and each sprint runs Monday to Sunday, so Sprint 2 is 2026-09-28 to 2026-10-04,
  Sprint 3 is 2026-10-05 to 2026-10-11, and Sprint 4 is 2026-10-12 to 2026-10-18. Sprint 1 started two days before this plan was drafted on 2026-09-23. The user can move
  the start date, and every date shifts with it.
- **2026-09-29, active.** The two carried rows have sprints: the backend soak is in [[sprint-plan-2]] Sprint 5, so it runs before the routing
  engine builds on the backend, and `DESIGN.md` is in [[sprint-plan-3]] Sprint 11. The routing work was re-cut into two four-sprint plans.
