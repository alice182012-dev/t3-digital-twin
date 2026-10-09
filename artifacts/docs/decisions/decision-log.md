---
date: 2026-09-25
type: decision
status: active
tags: [decisions, raster-first, routing, airflow]
related: ["[[raster-first-flood-pipeline]]", "[[raster-first-pipeline-stories]]", "[[flood-on-roads]]", "[[graphhopper-backend]]", "[[sprint-plan]]"]
---
# Decision log

This page records each decision the team makes, with the reason, the alternatives, and what the decision
changes. It is append-only. To change a decision, add a new entry that supersedes the old one and set the
old entry's status to `superseded by D-nnn`. Do not rewrite an old entry.

An entry has these fields: what was decided, why, what else was considered, the evidence, what it affects,
who decided, and how to revisit it. Number entries in order (`D-001`, `D-002`, and so on).

## D-001: Write `flood_road_values` in place

- **Date:** 2026-09-24
- **Status:** active
- **Decided by:** the user
- **Decision:** The flood-on-roads task writes `flood_road_values` directly. A shadow table is used only to
  compare the new output with the old.
- **Why:** Routing reads `flood_road_values` through `flood_areas.py`. Writing in place keeps the table and
  its meaning unchanged, so the reading side needs no change to accept the new rows.
- **Alternatives:** Write a new table and change `flood_areas.py` to read it. Rejected because it touches
  routing for no gain.
- **Affects:** [[raster-first-pipeline-stories]] Stories 3 and 4. New columns (`segment_id`, `depth_max`) are
  added with `ADD COLUMN IF NOT EXISTS`, so the old pipeline keeps working until it is retired.
- **Revisit if:** the comparison shows the new rows cannot share the table with old rows.

## D-002: Depth per road piece is the mean, with the maximum stored beside it

- **Date:** 2026-09-24
- **Status:** superseded by D-006
- **Decided by:** the user chose the mean. Claude added the stored maximum.
- **Decision:** `depth` holds the mean depth over the samples along a road piece, and dry samples count as 0.
  A second column, `depth_max`, holds the deepest sample.
- **Why:** The user chose the mean. The vault records "mean" or "average" only for the route chart's
  route-level value ([[route-forecast-query]]). The old pipeline did no averaging: it cut each road by the flood
  cells, so each row carried one cell's depth. A mean over a 50 m piece can hide a short deep spot: 5 m at
  0.6 m depth inside a mostly dry 50 m piece averages about 0.06 m, under the motorbike's 0.2 m limit. Storing
  the maximum keeps both values, so the choice can be judged with data.
- **Alternatives:** Store only the mean (hides deep spots). Store only the maximum (loses the value the route
  chart needs).
- **Evidence:** [[flood-on-roads]], the comparison on real runs `20260924T164803` and `20260924T170000`.
- **Affects:** `flood_on_roads.compute`, and every reader of `flood_road_values.depth`. See D-005.
- **Revisit if:** the route chart or another consumer needs a different aggregate.

## D-003: Retire `dags/test_dag.py`

- **Date:** 2026-09-24
- **Status:** active
- **Decided by:** the user
- **Decision:** Delete `dags/test_dag.py`, which defines the DAG `flood_forecast_pipeline_test`.
- **Why:** It imports the retired GeoJSON scripts, and it failed every 30 minutes on the server.
- **Alternatives:** Rewrite it on the new tasks. Rejected by the user.
- **Affects:** The DAG disappears from Airflow after the Stage B deploy. No test, compose entry, or doc
  referenced it.
- **Revisit if:** a manual end-to-end test DAG is needed again. `flood_forecast_state_test_dag.py` remains, and since 2026-09-25 it follows the
  production steps and is the end-to-end manual test.

## D-004: Remove the `flood-results-full` bucket

- **Date:** 2026-09-24
- **Status:** active. Configuration is removed on `stage-b`. The server bucket was deleted on 2026-09-25: 15 objects,
  14.7 MB, all `.geojson` (the count had grown from 13 because production cycles ran on 2026-09-24).
- **Decided by:** the user
- **Decision:** Remove the bucket from compose, `.env.example`, the README, the docs, and the tests. Delete the
  bucket and its 13 objects (12 MB) on the server at the Stage B deploy.
- **Why:** Only the retired tasks 7 and 8 used it, and nothing else reads it. MinIO itself stays for the flood
  tiles, because the Airflow worker and the frontend run on separate hosts in production (decided 2026-09-22,
  see [[calculate-depth-threedidepth-cli]] and [[minio-flood-extent-pipeline]]).
- **Alternatives:** Keep the objects and only stop the uploads. The user chose to remove the bucket.
- **Affects:** Deleting on the server waits until the DAG no longer references the bucket, because the old task
  `7_upload_minio` recreates a missing bucket.
- **Revisit if:** the GeoJSON files are needed as an archive. They are not needed for routing, tiles, or points.

## D-005: Routing filters on `depth_max`, and `depth` stays the mean

- **Date:** 2026-09-25
- **Status:** superseded by D-006
- **Decided by:** the user, on Claude's recommendation
- **Decision:** `flood_areas.py` decides whether a road piece is impassable for a vehicle by comparing
  `depth_max` to the vehicle's limit. Rows written by the old pipeline have no `depth_max`, so routing falls
  back to `depth` for them. `depth` stays the mean, which serves the route chart's average depth.
- **Why:** A road cannot be passed if any stretch of it is too deep, so the deepest sample is the right test.
  The comparison of the new task with the raster along the roads (four vehicle limits, two real runs, four
  timesteps each) found pieces where the road reaches the limit but the new value stays under it:

  | Vehicle (limit)    | Mean, run 164803 | Maximum | Mean, run 170000 | Maximum |
  | ------------------ | ---------------- | ------- | ---------------- | ------- |
  | Motorbike (0.20 m) | 168              | 0       | 110              | 4       |
  | Car (0.30 m)       | 101              | 5       | 67               | 0       |
  | Truck (0.35 m)     | 78               | 0       | 60               | 0       |
  | Foot (0.40 m)      | 63               | 0       | 39               | 0       |

  The maximum's few misses all sit beside a piece boundary.
- **Alternatives:** Route on the mean (misses 39 to 168 pieces per vehicle and run). Put the maximum in `depth`
  (loses the mean the route chart wants).
- **Evidence:** [[flood-on-roads]]. The old rows are not a reliable benchmark: the server runs `SAMPLE_RATE=20`,
  so each old depth is the top-left pixel of a 20 m cell, and about half of the old wet slivers are dry along the
  road itself.
- **Affects:** `flood_areas.py`, its tests, and [[graphhopper-backend]]. Routing becomes more cautious than the
  old pipeline: the maximum closes more pieces (for example 1,084 more for the motorbike in run 164803),
  because the old data was sparse. The flood metric extractor and the TimescaleDB metrics still read `depth`,
  and which depth they should use is not decided (see the open decisions).
  While building it, Claude found that every routing band grades on `depth_max`, not only the impassable one.
  If only the impassable band used the maximum, a piece with a mean at 0.9 times the limit and a maximum at 1.1
  times the limit would fall in two bands and draw two overlay polygons. So the penalty bands (b2 and b3) also
  grade on the maximum. Deploy order: run `scripts/database/create_geojson_tables.py` (it added `depth_max`; renamed `create_flood_road_tables.py`)
  before the backend is rebuilt, because a query on a table without the column raises `UndefinedColumn`.
- **Revisit if:** users report routes that avoid roads that are passable. The filter is one condition in
  `flood_areas.py`.

## D-006: Depth per road piece is the maximum, stored in `depth`

- **Date:** 2026-09-25
- **Status:** active. Supersedes D-002 and D-005.
- **Decided by:** the user
- **Decision:** `flood_road_values.depth` holds the deepest 1 m sample along a road piece. There is no separate
  `depth_max` column, and the mean is not stored. Routing reads plain `depth` again.
- **Why:** The user chose the maximum for every use, from now on. The comparison on two real runs (D-005) found
  that the mean misses 39 to 168 pieces per vehicle and run where the road reaches the limit, and the maximum
  misses 0 to 5 (9 in total across all vehicles and runs, all beside a piece boundary). One column with one meaning is simpler than two, and routing, the flood metric extractor, and
  the TimescaleDB metrics then read the same value. That also closes the open decision in this log on which
  depth the metrics use.
- **Alternatives:** Keep both columns, with the maximum for routing (D-005). Rejected: the mean has no consumer
  once the maximum is the value everywhere, so storing it is dead weight.
- **Affects:** `flood_on_roads.compute` (writes the maximum into `depth`), `create_flood_road_tables.py`, renamed from `create_geojson_tables.py` (no
  `depth_max` column), `flood_areas.py` (back to `v.depth`, without the COALESCE), and the tests and concept
  notes that named the mean. Deploy order gets simpler: routing no longer reads a new column, so nothing
  breaks if the backend and the schema change in either order. The route chart's "average depth" becomes the
  average over a route's pieces of each piece's maximum. Old rows are unchanged: their `depth` is the sparse
  20 m pixel value.
- **Costs:** Routing is more cautious than the old pipeline (for example 1,084 more closed pieces for the
  motorbike in run 164803, because the old data was sparse), and the mean of a piece cannot be recovered later
  without recomputing from the tiles.
- **Revisit if:** users report routes that avoid roads that are passable. The tiles are the source of truth, so
  another aggregate can be recomputed from them.

## D-007: The two test events publish under one run name

- **Date:** 2026-09-25
- **Status:** active. Approved by the user on 2026-09-25.
- **Decided by:** the user asked for the test DAG to keep two consecutive events and to show in the frontend. Claude proposed the
  run naming, and the user approved it.
- **Decision:** In `flood_forecast_state_test_dag.py`, event 1 and event 2 both publish their tiles, raster tiles, and road
  values under one run name: the stamp of event 1's earliest depth file.
- **Why:** The frontend's timeline lists the timesteps of the newest single run only. With a run name per event, event 1
  would vanish from the timeline as soon as event 2 published. Event 2 hotstarts from event 1's saved state and starts when
  event 1 ends, so one run name gives one continuous four-hour scenario. Every step keys its rows by (run, timestep), so a
  second publish under the same run name adds timesteps without touching the first event's.
- **Alternatives:** One run name per event. Rejected: the frontend would show only event 2.
- **Affects:** [[flood-on-roads]], `raster_load.load_run` (needs a `keep_runs` argument so a test run cannot prune real
  runs), and the state-test DAG. The test DAG writes `flood_road_values` in place on purpose, so routing shows the test event.
- **Guard:** the DAG refuses to publish event 2 if event 2's earliest depth timestamp is at or before event 1's last one, because a
  timestep written by both events would keep leftovers of event 1 (tiles are overwritten file by file and polygons band by band). At
  the defaults it cannot happen: `calculate_depth` skips step 0, and `SIMULATION_DURATION` (7,200 s) equals event 1's rain window.
- **Revisit if:** the frontend gains a run picker that can show two runs at once.

## D-008: The app opens in Flood mode until further notice

- **Date:** 2026-09-30
- **Status:** active. Decided by the user on 2026-09-30.
- **Decided by:** the user, after the mockup screen check ([[mockup-screen-coverage]] Story 2) found that screen 2a opens
  with Map on and Flood off, and the app opens in Flood mode.
- **Decision:** The app opens in Flood mode, with the flood layer and the legend, until the user says otherwise. It does not
  follow screen 2a's Map-first opening for now.
- **Why:** The app is in its building phase, and Flood mode is the mode being built and shown, so it opens straight into it.
- **Alternatives:** Follow the mockup, opening in Map mode with Flood off and no legend. Or let `defaultMapMode` choose by
  data recency, which opens in Flood mode only when the selected step is within 45 minutes of now. Both are kept in the code
  path and can be switched back on.
- **Evidence:** `floodmap/graphhopper-maps/src/floodmap/FloodStore.ts` starts with `mapMode: 'flood'` and
  `userChoseMapMode: true`, commented as a demo default. Because `userChoseMapMode` is true, the first
  `FloodTimestepsReceived` does not recompute the mode, so `defaultMapMode` has no effect at load. On 2026-09-30 the live app
  opened in Flood mode with data from 02:15 while the clock read about 12:30, so the mode does not depend on how fresh the data is.
- **Affects:** [[mockup-screen-coverage]] screen 2a, which now differs from the app on purpose. With old data the map still opens in
  Flood mode, and the legend's "As of" line shows the age of the data. [[map-shows-forecast-not-now]] covers what the map
  shows over time.
- **Revisit if:** the user ends the building phase or asks for the mockup's opening. To follow the mockup, start `FloodStore`
  in Map mode. To choose by data recency, start with `userChoseMapMode: false`.

## D-009: The `background_cycle` is not run, and its stories are dropped

- **Date:** 2026-10-01
- **Status:** active
- **Decided by:** the user
- **Decision:** The pipeline does not run a `background_cycle` forecast. Every story that needs `background_cycle`
  output is dropped. That is `US-021` (load the extractor's output into TimescaleDB as 24 hourly bars). `US-018`
  (the schema) was built earlier and stays `Done`.
- **Why:** The user said so on 2026-10-01. The pipeline runs one cycle, the 15-minute `flood_mapping_full`, and
  no DAG ever produced `background_cycle` data.
- **Alternatives:** Build a forecast run every 3 to 6 hours with its own rain input (option C in
  [[timescaledb-load-has-no-source-for-histogram-bars]]). Rejected by this decision.
- **Affects:** The 24-bar institution histogram of the architecture doc (section 4.9) cannot be built as
  specified, because bars 7 to 24 come from `background_cycle`. [[t3-digital-twin-architecture-gaps]] Goal 2 and
  its second Definition of done bullet are removed. The `background_cycle` enum value, the
  `background_forecast_depth` table, and the bars 7 to 24 CHECK in `create_timescale_tables.py` stay in the
  schema and stay unused. The raw architecture doc still describes `background_cycle`, and it is read-only.
- **Revisit if:** the user wants a forecast beyond the 2-hour window of the 15-minute cycle.

## D-010: The legend keeps "As of", and the "Powered by GraphHopper" line and links are removed

- **Date:** 2026-10-07
- **Status:** active. Decided by the user on 2026-10-07.
- **Decided by:** the user, after the frontend recheck against the mockup ([[frontend-mockup-recheck-and-sprint-11-start]], differences G4 and G5).
- **Decision:** The legend keeps "As of `time`" for a step at or before now and "Forecast for `time`" for a later step. It does not
  return to the mockup's "Updated". The "Powered by GraphHopper" line is deleted from the empty routing panel if the license allows it. The settings box's links to `graphhopper.com` (info, imprint, privacy, terms) are deleted too, as the user confirmed the same day.
- **Why:** The timestep shows when the data is valid, not when it was updated ([[map-shows-forecast-not-now]]). The mockup shows
  neither a "Powered by" line nor GraphHopper's name.
- **Alternatives:** Return to "Updated" to match the mockup. Keep "Powered by" as a credit.
- **Evidence:** `timestepLabel.ts` produces "As of" and "Forecast for". `sidebar/PoweredBy.tsx` renders the line. The GraphHopper Maps
  source is Apache 2.0 (`floodmap/graphhopper-maps/NOTICE.md`), which does not require a badge in the UI. It does require the license and
  notice files to stay with the code, so `NOTICE.md` and `LICENSE.txt` stay. This is a reading of the license by Claude, not legal advice.
- **Affects:** [[frontend-mockup-recheck-stories]] Stories 4 (`US-079`) and 5 (`US-080`). The legend part of [[map-shows-forecast-not-now]] is settled.
- **Revisit if:** the project is published outside the team, or the user wants the mockup's "Updated" wording back.

## D-011: Build all of Sprint 11 before the next server run, and deploy once

- **Date:** 2026-10-07
- **Status:** active. Decided by the user on 2026-10-07.
- **Decided by:** the user, when asked to continue after `US-071` to `US-075` were scoped.
- **Decision:** All Sprint 11 stories are built and tested locally on the branch `modular` before any further 48-hour run. The server gets one deploy of the engine stories and Sprint 11 together, and one short DAG run (about one hour) instead of a second replay.
- **Why:** A 48-hour run costs a lot, and every story that needs the server can share one run. The ordering is in [[sprint-11-server-rollout]].
- **Alternatives:** Deploy `US-055` alone on the old DAG shape and the Sprint 11 stories later. That costs a second deploy.
- **Evidence:** `modular` holds `US-051` to `US-054` and `US-071` to `US-075`, each `Reviewed`. `rollout.ps1` only checks that the core DAG is paused, and `table_timing.ps1` was rewritten for `routing_adapter`, so the old shape is not required.
- **Affects:** [[sprint-plan-3]] Sprints 9 to 11, and the stories that wait on `US-055`.
- **Revisit if:** the first run of `rollout.ps1` fails because of the role or the DAG move, which would argue for the two-deploy order.

## D-012: A rain replay runs for 12 hours

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, when the storm of 2026-09-16 and 2026-09-17 was chosen as the test event.
- **Decision:** A test replay covers 12 hours of rain, not the 48 hours of the October 2025 event. The event file is the wettest 12 hours of the satellite series.
- **Why:** Every simulating run is a real 3Di simulation, and the cost grows with the number of runs. The 12-hour event has 42 simulating runs at a gate of 5 mm/h.
- **Alternatives:** Replay the full two-day series, or the 48-hour October event again. Both cost more runs.
- **Evidence:** `scripts/rain_events/hanoi_20260916_storm.csv` has 24 rows, 53.88 mm, and a peak of 8.73 mm/h. `rain_replay.py check` at gate 5 lists 42 of 46 runs in 2 chains. The server read it back from inside the worker on 2026-10-08.
- **Affects:** [[rain-replay-test-environment]], [[rain-replay-test-environment-stories]], and the stories that wait for a replay: `US-045`, `US-069`, `US-070`, and `US-073`. `US-069` names a 24-hour to 48-hour storage comparison that 12 hours cannot show.
- **Revisit if:** a story needs a longer window, such as the `US-069` pass condition.

## D-013: Rain forecast comes from Tomorrow.io, not NCHMF

- **Date:** 2026-10-08, recorded after the fact. The date of the switch itself is not recorded in the vault.
- **Status:** active. Confirmed by the user on 2026-10-08.
- **Decided by:** the user.
- **Decision:** The pipeline reads its rain forecast from the Tomorrow.io API. The original design named the NCHMF (Trung tâm dự báo KTTV Quốc Gia) forecast.
- **Why:** NCHMF did not approve access to its API.
- **Alternatives:** Wait for NCHMF approval, or read NCHMF files by hand. Neither gives an automated forecast every cycle.
- **Evidence:** `scripts/create_simulation.py` lines 27 and 148 (`TOMORROW_API_KEY`, `api.tomorrow.io/v4/timelines`). `grep -ri nchmf dags scripts compose.yml` returns nothing.
- **Affects:** [[3di-simulation-orchestration]], the architecture doc, and any paper text that names the rain source.
- **Revisit if:** NCHMF grants API access.

## D-014: The simulation cycle is 15 minutes

- **Date:** 2026-10-08, recorded after the fact. The cycle was already running at 15 minutes.
- **Status:** active. Approved by the user on 2026-10-08.
- **Decided by:** the user.
- **Decision:** `flood_mapping_full` runs one cycle every 15 minutes. The original design said about 30 minutes.
- **Why:** The reaction-time research found that a 15-minute refresh covers the nowcast skill window for convective storms and is more than enough for multi-hour storms. See [[flood-map-reaction-time-findings]].
- **Alternatives:** A 30-minute cycle, which matches Hanoi's own flooding-point monitor, or a 5-minute cycle, which adds little unless the rain input also updates every 5 minutes ([[five-minute-tile-freshness]]).
- **Evidence:** `dags/flood_mapping_dag.py` schedule, and [[3di-simulation-orchestration]].
- **Affects:** the architecture doc (ADR-006), the replay gate, and Paper B.
- **Revisit if:** a rain input with a finer update interval becomes available.

## D-015: US-069 is checked on the 12-hour replay, from hour 6 to hour 12

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, who said `US-069` needs only 12 hours of running and the comparison should use those 12 hours.
- **Decision:** The storage check of `US-069` reads the numbers at the start of the 12-hour replay, at hour 6, and at hour 12, and compares hour 6 with hour 12. It replaces the 24-hour to 48-hour comparison. The other conditions stay: `flood_extent_polygon` holds rows for no more than the newest `keep_runs` runs, and no container is auto-paused for lack of space.
- **Why:** D-012 set a replay to 12 hours, so the 24-hour and 48-hour readings cannot exist.
- **Alternatives:** Define the pass as "capped tables stop growing at their cap". That says nothing about the uncapped tables.
- **Evidence:** the replay runs from about 15:05 +07 on 2026-10-08 to the last simulating run at 03:00 +07 on 2026-10-09. The only start reading is partial (15:17 +07 on 2026-10-08: C: free, `docker_data.vhdx`, `minio_custom`, `flood_extent_polygon`), so the pass rests on hour 6 against hour 12.
- **Affects:** [[carried-over-backlog]] Story 12 (`US-069`), `TODOS.md`. The user confirmed the pass mark on 2026-10-08: growth of 10 percent or less per database object between hour 6 and hour 12.
- **Revisit if:** the server cannot be read at hour 6 (about 21:05 +07).

## D-016: Archive `results_3di.nc` to the D: drive on the server, only with real rain

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, after asking where the data of a past storm would be found.
- **Decision:** Each simulating run keeps its `results_3di.nc` in an archive folder on the server's D: drive. Archiving starts only when the pipeline reads the real rain forecast (Tomorrow.io), not the test rain (`FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` set).
- **Why:** After a storm, the system keeps rasters and tiles for about 2 hours, `netcdf_values` for 48 hours, and the NetCDF files for 24 hours. No store holds the storm for later analysis. The NetCDF file is the source of truth: the depth rasters, polygons, and road depths can be rebuilt from it and the model.
- **Alternatives:** Keep `flood_road_values` (about 18 MB per run). Re-download results from 3Di by `sim_id`, which is unverified because the local 3Di docs do not state how long 3Di keeps results.
- **Evidence:** `results` holds 14 files of 98 MB in total on the worker, about 7 MB per run. `flood_road_values` is 6,955 MB for 377 run timestamps.
- **Affects:** `dags/flood_mapping_dag.py` (the 24-hour `cleanup_dirs` that now deletes `RESULT_DIR`), `compose.yml` (a D: mount), [[3di-simulation-orchestration]], Paper B. A run record (`sim_id`, rain input, model revision, graph hash, run timestamp) is part of the archive. Stories: `US-094` (Sprint 10) in [[US-094-095-archive-and-netcdf-retirement-stories]], and `US-086` depends on it.
- **Revisit if:** D: free space falls, or 3Di is found to keep results long enough to re-download.

## D-017: `flood_road_values` is pruned after 24 hours

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user.
- **Decision:** `US-086` removes rows of `flood_road_values` older than 24 hours, in place of keeping the newest N runs.
- **Why:** The table grows about 18 MB per run with no cap (6,955 MB on 2026-10-08), and the raw archive of D-016 keeps the storm for analysis.
- **Alternatives:** Keep the newest N runs, which would hold less than 24 hours during dense runs.
- **Evidence:** the size reading in [[core-output-hygiene-stories]] Story 1.
- **Affects:** `US-086`, [[core-output-contract]], and anything that reads `flood_road_values` older than 24 hours (the flood metric extractor, if it is ever scheduled).
- **Revisit if:** the archive of D-016 is not working when the first prune runs.

## D-018: Retire the `netcdf_values` ingest

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, who said to retire it in Sprint 11.
- **Decision:** Remove task `3b_upload_netcdf_postgres`, the TimescaleDB tables `netcdf_values`, `mesh_elements`, and `netcdf_variable_catalog`, and the scripts and tests that use them. Do it only after the archive of D-016 is proven, so no data is lost. The other three TimescaleDB tables (`institution_histogram_bar`, `background_forecast_depth`, `depth_history`) stay.
- **Why:** `netcdf_values` is 2,428 MB with a 48-hour retention policy, and `3b` takes about 81 s per run. The archived NetCDF file of D-016 is the source of truth, so the ingest holds nothing the archive lacks.
- **Alternatives:** Keep the ingest beside the archive. Rejected by the user.
- **Evidence:** dependency check of 2026-10-08. The only foreign key is `netcdf_values.variable_id` to `netcdf_variable_catalog(id)`, so drop `netcdf_values` first. No views or continuous aggregates exist. The code references are listed in `US-095`.
- **Affects:** `US-095` (Sprint 11) in [[US-094-095-archive-and-netcdf-retirement-stories]], `US-066` and `US-069` (the storage check reads `netcdf_values`), [[3di-simulation-orchestration]], the architecture doc. Whether to retire the `timescaledb` container afterward is a separate decision and is not made here.
- **Revisit if:** `US-094` does not hold a real storm before Sprint 11 ends.

## D-019: Deploy the `flood_road_values` prune before `US-094` is proven

- **Date:** 2026-10-09
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** `US-086` deploys on 2026-10-09, before the archive of `US-094` is proven on real rain.
- **Why:** The growth of `9c` (44.8 to 90.3 s within a chain, `US-070`) points at this table, and `US-094` waits for a forecast above 5 mm/h that may not come for weeks.
- **Alternatives:** Keep the deploy behind `US-094`, as D-017 assumed.
- **Evidence:** the 9c readings of 2026-10-09 in `TODOS.md` (`US-070`).
- **Affects:** `US-086`, `US-070`, [[9c-sampling-step-runs-over-770-seconds]]. Until the archive works, depth history older than 24 hours is gone from this table and not archived. The raw `netcdf_values` keeps 48 hours under its own policy.
- **Revisit if:** a result older than 24 hours is needed before `US-094` runs.

## D-020: The second replay runs after Sprint 12

- **Date:** 2026-10-09
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** the second 12-hour replay, with `EDGE_TABLE_KEEP_RUNS` raised, runs after Sprint 12. `US-091` and `US-093` build their harness on the 3 tables copied on 2026-10-09 and report storm stages after the replay. `replay.ps1 stop` does not run before then.
- **Why:** the 12-hour replay kept only 3 of 45 edge depth tables, and the storm stages need the whole storm.
- **Alternatives:** Run the replay inside Sprint 12.
- **Affects:** `US-091`, `US-092`, `US-093`, `US-069`, `US-089`, [[sprint-12-finish-the-routing]].
- **Revisit if:** Sprint 12 ends with `US-091` and `US-093` unable to close without the storm stages.

## D-021: Detour at half the vehicle limit and keep the hard-limit route as a second option

- **Date:** 2026-10-09
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** each vehicle has a precaution depth of 50 percent of its hard limit (motorbike 10 cm, car 15 cm, truck 17.5 cm, foot 20 cm). The recommended route is planned with the precaution depth as the closing depth. The route planned with the hard limit stays available as a second option. If no route exists under the precaution depth, the hard-limit route is recommended and flagged as passing through water. The fraction is one setting.
- **Why:** the flood model is not validated, so the app protects assets before the modelled depth reaches the limit, and it does not hide the route a driver may need.
- **Alternatives:** a graded cost band (rejected: the engine has no cost term, the model is too uncertain to justify a curve, and the FIFO proof would need a recheck).
- **Evidence:** none yet. The sweep of the fraction in `US-092` measures the detour and the share of pairs without a precaution route.
- **Affects:** `US-097`, `US-098`, `US-092`, [[engine-has-no-depth-band-cost]], [[sticky-closure-proof]].
- **Revisit if:** the sweep shows that 50 percent leaves many pairs without a precaution route, or the flood model is validated.

## Open decisions

1. What the map shows by default: the situation now, or the nearest forecast timestep. No t0 raster exists today, and routing and
   the histogram do not yet handle the forecast side. The options and questions are in the blocker [[map-shows-forecast-not-now]].
   Decide this before the route-forecast query and the chart are built, because it changes both.

The question of which depth the flood metric extractor and TimescaleDB metrics use is settled by D-006: they read `depth`, which
is the maximum.
