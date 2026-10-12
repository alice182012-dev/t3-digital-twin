---
date: 2026-09-25
type: decision
status: active
tags: [decisions, raster-first, routing, airflow]
related: ["[[raster-first-flood-pipeline]]", "[[EP-06-raster-first-pipeline|raster-first-pipeline-stories]]", "[[flood-on-roads]]", "[[graphhopper-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
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
- **Affects:** [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Stories 3 and 4. New columns (`segment_id`, `depth_max`) are
  added with `ADD COLUMN IF NOT EXISTS`, so the old pipeline keeps working until it is retired.
- **Revisit if:** the comparison shows the new rows cannot share the table with old rows.

## D-002: Depth per road piece is the mean, with the maximum stored beside it

- **Date:** 2026-09-24
- **Status:** superseded by D-006
- **Decided by:** the user chose the mean. Claude added the stored maximum.
- **Decision:** `depth` holds the mean depth over the samples along a road piece, and dry samples count as 0.
  A second column, `depth_max`, holds the deepest sample.
- **Why:** The user chose the mean. The vault records "mean" or "average" only for the route chart's
  route-level value ([[US-017-route-forecast-query|route-forecast-query]]). The old pipeline did no averaging: it cut each road by the flood
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
- **Decided by:** the user, after the mockup screen check ([[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 2) found that screen 2a opens
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
- **Affects:** [[EP-05-mockup-screen-coverage|mockup-screen-coverage]] screen 2a, which now differs from the app on purpose. With old data the map still opens in
  Flood mode, and the legend's "As of" line shows the age of the data. [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] covers what the map
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
  [[BL-020-timescaledb-load-has-no-source-for-histogram-bars|timescaledb-load-has-no-source-for-histogram-bars]]). Rejected by this decision.
- **Affects:** The 24-bar institution histogram of the architecture doc (section 4.9) cannot be built as
  specified, because bars 7 to 24 come from `background_cycle`. [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] Goal 2 and
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
- **Why:** The timestep shows when the data is valid, not when it was updated ([[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]). The mockup shows
  neither a "Powered by" line nor GraphHopper's name.
- **Alternatives:** Return to "Updated" to match the mockup. Keep "Powered by" as a credit.
- **Evidence:** `timestepLabel.ts` produces "As of" and "Forecast for". `sidebar/PoweredBy.tsx` renders the line. The GraphHopper Maps
  source is Apache 2.0 (`floodmap/graphhopper-maps/NOTICE.md`), which does not require a badge in the UI. It does require the license and
  notice files to stay with the code, so `NOTICE.md` and `LICENSE.txt` stay. This is a reading of the license by Claude, not legal advice.
- **Affects:** [[EP-11-frontend-mockup-recheck|frontend-mockup-recheck-stories]] Stories 4 (`US-079`) and 5 (`US-080`). The legend part of [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] is settled.
- **Revisit if:** the project is published outside the team, or the user wants the mockup's "Updated" wording back.

## D-011: Build all of Sprint 11 before the next server run, and deploy once

- **Date:** 2026-10-07
- **Status:** active. Decided by the user on 2026-10-07.
- **Decided by:** the user, when asked to continue after `US-071` to `US-075` were scoped.
- **Decision:** All Sprint 11 stories are built and tested locally on the branch `modular` before any further 48-hour run. The server gets one deploy of the engine stories and Sprint 11 together, and one short DAG run (about one hour) instead of a second replay.
- **Why:** A 48-hour run costs a lot, and every story that needs the server can share one run. The ordering is in [[sprint-11-server-rollout]].
- **Alternatives:** Deploy `US-055` alone on the old DAG shape and the Sprint 11 stories later. That costs a second deploy.
- **Evidence:** `modular` holds `US-051` to `US-054` and `US-071` to `US-075`, each `Reviewed`. `rollout.ps1` only checks that the core DAG is paused, and `table_timing.ps1` was rewritten for `routing_adapter`, so the old shape is not required.
- **Affects:** [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] Sprints 9 to 11, and the stories that wait on `US-055`.
- **Revisit if:** the first run of `rollout.ps1` fails because of the role or the DAG move, which would argue for the two-deploy order.

## D-012: A rain replay runs for 12 hours

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, when the storm of 2026-09-16 and 2026-09-17 was chosen as the test event.
- **Decision:** A test replay covers 12 hours of rain, not the 48 hours of the October 2025 event. The event file is the wettest 12 hours of the satellite series.
- **Why:** Every simulating run is a real 3Di simulation, and the cost grows with the number of runs. The 12-hour event has 42 simulating runs at a gate of 5 mm/h.
- **Alternatives:** Replay the full two-day series, or the 48-hour October event again. Both cost more runs.
- **Evidence:** `scripts/rain_events/hanoi_20260916_storm.csv` has 24 rows, 53.88 mm, and a peak of 8.73 mm/h. `rain_replay.py check` at gate 5 lists 42 of 46 runs in 2 chains. The server read it back from inside the worker on 2026-10-08.
- **Affects:** [[rain-replay-test-environment]], [[EP-13-rain-replay-test-environment|rain-replay-test-environment-stories]], and the stories that wait for a replay: `US-045`, `US-069`, `US-070`, and `US-073`. `US-069` names a 24-hour to 48-hour storage comparison that 12 hours cannot show.
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
- **Affects:** [[EP-07-carried-over-backlog|carried-over-backlog]] Story 12 (`US-069`), `TODOS.md`. The user confirmed the pass mark on 2026-10-08: growth of 10 percent or less per database object between hour 6 and hour 12.
- **Revisit if:** the server cannot be read at hour 6 (about 21:05 +07).

## D-016: Archive `results_3di.nc` to the D: drive on the server, only with real rain

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user, after asking where the data of a past storm would be found.
- **Decision:** Each simulating run keeps its `results_3di.nc` in an archive folder on the server's D: drive. Archiving starts only when the pipeline reads the real rain forecast (Tomorrow.io), not the test rain (`FLOOD_TEST_RAIN_CSV` or `FLOOD_TEST_RAIN_MM_HR` set).
- **Why:** After a storm, the system keeps rasters and tiles for about 2 hours, `netcdf_values` for 48 hours, and the NetCDF files for 24 hours. No store holds the storm for later analysis. The NetCDF file is the source of truth: the depth rasters, polygons, and road depths can be rebuilt from it and the model.
- **Alternatives:** Keep `flood_road_values` (about 18 MB per run). Re-download results from 3Di by `sim_id`, which is unverified because the local 3Di docs do not state how long 3Di keeps results.
- **Evidence:** `results` holds 14 files of 98 MB in total on the worker, about 7 MB per run. `flood_road_values` is 6,955 MB for 377 run timestamps.
- **Affects:** `dags/flood_mapping_dag.py` (the 24-hour `cleanup_dirs` that now deletes `RESULT_DIR`), `compose.yml` (a D: mount), [[3di-simulation-orchestration]], Paper B. A run record (`sim_id`, rain input, model revision, graph hash, run timestamp) is part of the archive. Stories: `US-094` (Sprint 10) in [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]], and `US-086` depends on it.
- **Revisit if:** D: free space falls, or 3Di is found to keep results long enough to re-download.

## D-017: `flood_road_values` is pruned after 24 hours

- **Date:** 2026-10-08
- **Status:** active. Decided by the user on 2026-10-08.
- **Decided by:** the user.
- **Decision:** `US-086` removes rows of `flood_road_values` older than 24 hours, in place of keeping the newest N runs.
- **Why:** The table grows about 18 MB per run with no cap (6,955 MB on 2026-10-08), and the raw archive of D-016 keeps the storm for analysis.
- **Alternatives:** Keep the newest N runs, which would hold less than 24 hours during dense runs.
- **Evidence:** the size reading in [[EP-12-core-output-hygiene|core-output-hygiene-stories]] Story 1.
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
- **Affects:** `US-095` (Sprint 11) in [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]], `US-066` and `US-069` (the storage check reads `netcdf_values`), [[3di-simulation-orchestration]], the architecture doc. Whether to retire the `timescaledb` container afterward is a separate decision and is not made here.
- **Revisit if:** `US-094` does not hold a real storm before Sprint 11 ends.

## D-019: Deploy the `flood_road_values` prune before `US-094` is proven

- **Date:** 2026-10-09
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** `US-086` deploys on 2026-10-09, before the archive of `US-094` is proven on real rain.
- **Why:** The growth of `9c` (44.8 to 90.3 s within a chain, `US-070`) points at this table, and `US-094` waits for a forecast above 5 mm/h that may not come for weeks.
- **Alternatives:** Keep the deploy behind `US-094`, as D-017 assumed.
- **Evidence:** the 9c readings of 2026-10-09 in `TODOS.md` (`US-070`).
- **Affects:** `US-086`, `US-070`, [[BL-023-9c-sampling-step-runs-over-770-seconds|9c-sampling-step-runs-over-770-seconds]]. Until the archive works, depth history older than 24 hours is gone from this table and not archived. The raw `netcdf_values` keeps 48 hours under its own policy.
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
- **Affects:** `US-097`, `US-098`, `US-092`, [[BL-025-engine-has-no-depth-band-cost|engine-has-no-depth-band-cost]], [[sticky-closure-proof]].
- **Revisit if:** the sweep shows that 50 percent leaves many pairs without a precaution route, or the flood model is validated.

## Open decisions

1. What the map shows by default: the situation now, or the nearest forecast timestep. No t0 raster exists today, and routing and
   the histogram do not yet handle the forecast side. The options and questions are in the blocker [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]].
   Decide this before the route-forecast query and the chart are built, because it changes both.

The question of which depth the flood metric extractor and TimescaleDB metrics use is settled by D-006: they read `depth`, which
is the maximum.

## D-022: Drop the netcdf tables before `US-094` is proven on real rain

- **Date:** 2026-10-10
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** the five netcdf tables are dropped on 2026-10-10 after the deploy of `US-095`, before the archive of `US-094` is proven on a real forecast above 5 mm/h. The three empty TimescaleDB tables stay.
- **Why:** `US-094` waits for rain that may not come for weeks, and `netcdf_values` held 5,378 MB in TimescaleDB and grew about 13 MB per run. D-018 said to retire the ingest, and the user waived its condition "only after `US-094` is proven".
- **Alternatives:** Wait for `US-094` to run on real rain, as the story said.
- **Evidence:** `us-095-drop-check-output.png`, and the readings in `US-095`.
- **Affects:** `US-095`, `US-094`, `US-066`. Until the archive runs on real rain, no copy of the per-timestep 3Di values is kept, because the replay results are deleted by the 24-hour cleanup of task `9`.
- **Revisit if:** a result of a replay run is needed after its raw output is deleted.

## D-023: Keep sticky closure as the engine's rule

- **Date:** 2026-10-10
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** the engine keeps sticky closure. A road is closed for an arrival if any forecast step from the start of the window to 10 minutes after entry reaches the vehicle's limit, and it stays closed even if the water recedes later. The engine does not move to the arrival-only rule of option A.
- **Why:** the user wants to protect the asset and the person conservatively and not risk any chance of a vehicle being flooded halfway along a road. Arrival-only reads the depth at the moment of entry only, so a vehicle can be inside a road when its depth reaches the limit (case 1 in `us-100-closure-reading-output.png`).
- **Alternatives:** (1) Move to arrival-only. It finds more routes, but the vehicle can be on a road when it floods. (2) Arrival-only plus a check of every step during the traversal. It would handle case 1 and keep receding roads open, and it is not built or proven.
- **Evidence:** `us-100-closure-reading-output.png` and [[sticky-closure-proof]]. On the four-node grid sticky closure has no route in 128 of 654 cases where option A has one, and it arrives later in 64.
- **Affects:** `US-100` (`Done`), `US-093` (option A stays the comparison reference, and its sticky-longer rate is the price of this safety), [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], and the paper's closure rule. No code changes.
- **Revisit if:** the real-graph cost in `US-093` shows that sticky loses routes a traveller needs, or the interval check of alternative 2 is built and proven.


## D-024: Adopt the Scrum framework and retire the four-sprint plans and the PRDs

- **Date:** 2026-10-10
- **Status:** active, except that the sprint length of one week is superseded by D-026. Decided by the user.
- **Decided by:** the user.
- **Decision:** The project follows Scrum with one-week sprints (Monday to Sunday, changed to two weeks by D-026), as described in [[scrum-framework]]. The user is the product owner. Claude sessions are the development team. A sprint is picked at sprint planning, one sprint at a time. Each sprint ends with a review and a retrospective. Velocity comes from the points of `Done` stories ([[Velocity]]). The 16 epics become 4 (`EP-17` to `EP-20`). PRDs are retired, and each epic holds its goal, reason, assumptions, and definition of done. Spikes (`kind: spike`) hold experiments, and they end with an answer and a decision.
- **Why:** The old rules planned four sprints ahead and put stories in them by dependency. In practice sprints 5 to 12 started and ended early, so a sprint no longer meant a week, and there was no sprint review, no retrospective, no velocity, and several places that held the same fact. Atlassian's Scrum guide plans one sprint at a time from an ordered backlog, keeps the length fixed so estimates improve, and puts review and retrospective inside the sprint.
- **Alternatives:** (1) Keep the four-sprint plans and add a review and a retrospective. It keeps the plan that the dates already broke. (2) Kanban, with no sprints. The project has a goal per week and an evidence rule per story, which suit sprints better. The user chose full Scrum.
- **Evidence:** the readings in `docs/concepts/project-management/`, and the user's answers on 2026-10-10: "ok" to restart the calendar at a Monday, "fresh" for Sprint 13, and "yes and retire the prds" for the epics.
- **Affects:** `.claude/CLAUDE.md` (the rules for sprints, stories, and PRDs), `Home.md`, `TODOS.md`, the templates (`sprint.md` and `epic.md` are new, `prd.md` is archived), `archive/prds/`, `archive/epics/`, `archive/sprints/`, every story's `epic` and `sprint` fields, and [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|Sprint 13]], which starts on 2026-10-12.
- **Revisit if:** two sprints in a row end below half of the forecast, or the product owner wants a different sprint length. Atlassian advises trying every event for two sprints before changing them.

## D-025: Retire the plan folder, shrink the logs, and add a definition of ready and a WIP limit

- **Date:** 2026-10-10
- **Status:** active. Decided by the user.
- **Decided by:** the user ("go, and keep the previous-day summary rule").
- **Decision:** (1) The `claude-plan/` folder is retired. Four plans that describe how a subsystem works became concept pages (`raster-first-flood-pipeline`, `rain-replay-test-environment`, `routing-first-consumer-contract`, `fifteen-minute-cycle-tiles-and-histogram`), and the other 18 are in `archive/plans/`. Multi-day work with no story gets a story, or a spike. (2) The concept pages stay. Their update rule is now part of the Definition of done. `timescaledb-schema` is `parked`, because its population was dropped in D-009. (3) The daily log stays, capped at about 20 lines, and keeps the previous-day summary. It drops the pickup list. (4) A story is `Ready` only when it passes INVEST. (5) At most two stories are `In progress`. (6) `US-021` is `Superseded`.
- **Why:** The Lean principles treat unread documents as waste. 21 of 23 plans said `active` although their work was done, 7 had no inbound link, and the plan duplicated what the story and the epic hold. Atlassian's Definition of Ready gives the pull step a checkable entry rule.
- **Alternatives:** Keep the plan folder and mark finished plans `done`. It keeps a second home for the plan of each story. Drop the previous-day summary rule. The user chose to keep it.
- **Evidence:** the readings "What are the Lean Principles?" and "What is Definition of Ready" in `docs/concepts/project-management/`.
- **Affects:** `.claude/CLAUDE.md`, `Home.md`, `templates/daily-log.md`, `templates/user-story.md`, `scrum-framework`, the refresh-artifacts skill, and `US-021`.
- **Revisit if:** a multi-day piece of work has no good home in a story, a spike, or a concept page.

## D-026: Make the sprint two weeks and fill it by story points

- **Date:** 2026-10-10
- **Status:** active. Decided by the user.
- **Decided by:** the user ("our sprint will be for 2 weeks, and we will allocate stories based on story points not weeks").
- **Decision:** A sprint is two weeks, from a Monday to the Sunday of the next week. Sprint planning is on the first Monday and takes 4 hours at most. A refinement is on the Friday of week 1. The review (1 hour) and the retrospective (30 minutes) are on the last Sunday. Planning picks `Ready` stories until the sum of their `estimate` points reaches the forecast from [[Velocity]]. The calendar sets the dates and not the number of stories. Sprint 13 runs 2026-10-12 to 2026-10-25, and Sprint 14 starts 2026-10-26.
- **Why:** The user wants capacity measured by work and not by time. A story fits a sprint by its size, and a sprint holds as many points as the team's velocity shows. Atlassian's guide allows two weeks as the usual length and sets planning at 2 hours for each week of the sprint.
- **Alternatives:** Keep one week (D-024). It left less room for the 12-hour replays and for work that waits on an outside event.
- **Evidence:** the user's instruction on 2026-10-10, and the sprint-planning guide in `docs/concepts/project-management/`.
- **Affects:** `.claude/CLAUDE.md` (rules 2, 3, and 11), `scrum-framework`, `Velocity`, `Home.md`, `TODOS.md`, `templates/sprint.md`, and `SPR-013`.
- **Revisit if:** two sprints in a row end below half of the forecast, or the user wants another length.

## D-027: Run the flood tile build as its own DAG, started by an asset that announces the depth folder

- **Date:** 2026-10-10
- **Status:** active for the split. The input is `files` by default, and the choice between `files` and `postgis` waits for [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]]. The code is on the branch `us-103-flood-tiles-dag` and is not on the server yet.
- **Decided by:** the user for the split ("separate the visualization part into a separate DAG", as prep for a future 3D view and a building cost estimate). The development team chose the input.
- **Decision:** Task `9_build_flood_tiles` leaves `flood_mapping_full` and becomes the one task of the DAG `flood_tiles`. A new task `3b_publish_depth_files` emits the asset `flood_depth_files` with `run_ts` and `depth_dir` in the event's `extra`, after `3_calculate_depth`, `2c_archive_done`, and `0b_ensure_schema`. `flood_tiles` runs on that asset. When events fold into one run, every run in them gets tiles. The age-based cleanup of the local result and depth folders stays in `publish_run`, so `flood_tiles` owns it, and a later consumer must not delete the depth folder. No 3D view and no cost estimate are built yet.
- **Why:** A tile failure or a tile code change no longer touches the simulation DAG, and a new consumer of the depth rasters is its own DAG on the same asset, as `routing_adapter` is on `flood_depth_raster_tile`. A failure of `flood_tiles` does not turn a core run red.
- **Alternatives:** (1) Read the PostGIS raster `flood_depth_raster_tile` and run on `FLOOD_DEPTH_RASTER`. It drops the shared local folder, but the tile build would wait for `9b` and first export each step back to a GeoTIFF in EPSG:4326. The code supports it with `FLOOD_TILES_INPUT=postgis` (`scripts/flood_extent/raster_export.py`), and the user asked to test both. (2) One shared "visualization" DAG for tiles, 3D, and cost. It couples three consumers that have different inputs and outputs.
- **Evidence:** [[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]] and the tests `test/test_flood_tiles_dag.py` and `test/test_flood_mapping_dag_graph.py`. The server check is open.
- **Affects:** `dags/flood_mapping_dag.py`, `dags/flood_tiles_dag.py`, `dags/core_assets.py`, `dags/core_paths.py`, `minio-flood-extent-pipeline`, `3di-simulation-orchestration`, `core-output-contract`, and the README.
- **Revisit if:** a second consumer of the depth files needs the files after the 24-hour cleanup, or the worker and the tile build move to different hosts.

## D-028: Keep the latest forecast of each road piece and moment, for years

- **Date:** 2026-10-10
- **Status:** active for the rule. The retention of several years is superseded by [[decision-log|D-032]], which sets one year. The way a consumer tells dry from unknown is set in D-032, and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] builds the store.
- **Decided by:** the user ("no lets do first row"), after the development team showed the sizing of three options.
- **Decision:** The flood history for the industry applications is `depth_history` in TimescaleDB, one row per road piece and moment, where the run with the later `issued_at` wins. It is kept for several years, with TimescaleDB compression and a policy that drops old data. No table keeps every forecast of every run. The history is the model's own forecast values, since no gauge observation enters the pipeline.
- **Why:** The latest-wins series is about 278,000 rows on a storm day, about 13 GB a year uncompressed even if every day were a storm day. Keeping every forecast is about 2.2 million rows a day, and no analysis asked for it. One month, the retention of 3Di results, is too short for a history of past floods.
- **Alternatives:** (1) Keep every forecast for 30 days in a second table, for analyses of forecast error and lead time. Rejected for now, and a new story adds it if such an analysis is asked for. (2) Keep one month of the latest-wins series, like 3Di results. Rejected, because the series is small enough to keep for years.
- **Evidence:** the sizing in `US-105`, read on the server on 2026-10-10. The row size and the compression ratio are estimates until `US-106` measures them.
- **Affects:** `US-105`, `US-106`, [[EP-21-industry-analysis-on-the-flood-data|EP-21]], and [[timescaledb-schema]].
- **Revisit if:** an industry application needs forecast error or lead time, if compression on the real TimescaleDB server is far below 10 times, or if the gauge hot start adds observed depth.

## D-029: Give vault edits to a Haiku subagent

- **Date:** 2026-10-10
- **Status:** active. Decided by the user.
- **Decided by:** the user.
- **Decision:** Every edit under `artifacts/` goes to the `vault-writer` agent (`.claude/agents/vault-writer.md`), which runs on Haiku in the same Claude Code terminal.
  The main session keeps code, DAGs, and scripts.
  The brief to the agent is short: the story ID, the task, and the date.
  The agent reads `git log`, `git diff`, and the story file for the rest.
  A fact that exists nowhere in the repo, such as a measured number, a server result, or a user decision, goes into the brief.
  The main session reads what the agent wrote before it reports the work as done.
- **Why:** Vault writing is routine work, and a smaller model does it at a lower cost per token than the main session.
  The agent needs no extra tool, and it runs in the terminal the session already uses.
  Haiku is billed, not free, so the saving is lower cost and not zero cost.
- **Alternatives:** (1) Hermes, a free model in a second tmux pane. It needs a second tool to run and sits outside the Claude Code terminal, so it is the fallback below. (2) Keep vault edits in the main session. It spends the main model's tokens on routine writing.
- **Evidence:** The user's choice on 2026-10-10. No cost measurement exists yet.
- **Affects:** `.claude/CLAUDE.md` (section "Vault edits go to the vault-writer agent") and `.claude/agents/vault-writer.md`.
- **Revisit if:** the cost still hurts after about a week, around 2026-10-17. The fallback is Hermes in a second tmux pane, which reuses `vault-writer.md` as its instructions.

## D-030: Show a pinned demo flood when no rain is forecast, and keep its peak step through every prune

- **Date:** 2026-10-10
- **Status:** active for the rule. The status signal and the router's read of the pinned step wait for [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]].
- **Decided by:** the user.
- **Decision:** The flood map has three modes.
  - **LIVE:** rain is forecast above the threshold, or a standing flood exists, and real simulation steps are published. The map shows the real result, as today.
  - **PENDING:** rain is forecast, but the simulation has published no step yet. The map shows a dry map with a warning that the simulation is running.
  - **DEMO:** Tomorrow.io shows no rain past the threshold and no standing flood. The map shows the demo flood with the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.
  The demo is one static frame, the peak step of the 12-hour replay of the 2026-09-16 storm ([[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]). The source is the replay of 2026-10-10 ([[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]). It has no slider and no animation.
  In DEMO mode the tiles, the routing, and the depth popup all use the pinned demo flood, not the tiles alone. The peak step must therefore survive every pruner: the MinIO tiles, `flood_extent_step`, and `flood_extent_polygon` (`FLOOD_EXTENT_KEEP_RUNS`, 8 runs), `flood_depth_raster_tile`, `flood_road_values` (`prune_flood_road_values`), and the routing edge tables (`EDGE_TABLE_KEEP_RUNS`, 3 runs).
- **Why:** The request did not give a reason, so none is recorded here.
- **Alternatives:** The user rejected these: (1) shift the demo onto the real clock, (2) show a slider over the demo, (3) show the demo on the tiles only, and (4) write the warning in Vietnamese.
- **Evidence:** None. The code is not written, and the feature is not on any branch.
- **Affects:** [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], [[minio-flood-extent-pipeline]], [[core-output-contract]], and [[edge-depth-table-format]].

## D-031: Count the violation rate of single-timestep routes as the case for time-aware routing

- **Date:** 2026-10-10
- **Status:** active for the finding. Whether `TIME_AWARE_ROUTING` stays on waits for the product owner's decision (open decision 7 in [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]).
- **Decided by:** The development team, from the result of [[US-091-measure-how-often-a-single-timestep-route|US-091]], which the product owner accepted as `Done` on 2026-10-10.
- **Decision:** The measured violation rate supports time-aware routing.
  Single-timestep routes met a road that was too deep on arrival in every storm stage, vehicle, trip length class, and departure step tested.
  The figures and their limits are in US-091.
  The decision does not turn `TIME_AWARE_ROUTING` on or off.
- **Why:** The case for time-aware routing is now a measured rate on the replay's tables, not an argument.
  The slowed-travel sensitivity case on the 3-hour table kept the same count, so the free-flow arrival assumption did not drive that table's result.
- **Alternatives:** A slowed-travel case run as a labelled sensitivity check, which kept the same count on the 3-hour table.
- **Evidence:** The result files of `US-091` in `marie-curie/us-091/` (git-ignored), and the screenshots `us-091-single-timestep-result-output.png` and `us-091-live-sticky-mid-step-output.png` in `artifacts/docs/stories/evidence/`.
- **Affects:** [[US-091-measure-how-often-a-single-timestep-route|US-091]], [[EP-20-routing-paper-experiments|EP-20]], [[sticky-routing-reference]], [[graphhopper-backend]], and [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]].
- **Revisit if:** the owner decides on `TIME_AWARE_ROUTING`, a later replay gives a different rate, or the free-flow arrival times are replaced by measured travel times.

## D-032: Store the flood history by road piece and moment in TimescaleDB, for one year, with a moment table for dry and unknown

- **Date:** 2026-10-10
- **Status:** active for the store, the grain, and the one-year retention. The `history_moment` table, the dry-or-unknown rule, and the compression and drop policy are the team's recommendation, which the product owner reads at the review of [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]].
- **Decided by:** The product owner, on 2026-10-10, for three points: the three industries (sub-question 1 of `US-105`), a missing row means dry at piece level (sub-question 4), and history lasts one year (sub-question 5).
  The development team recommends the `history_moment` table and the moment rule in the Decision below.
  That recommendation is not an owner answer.
  The product owner accepted US-105 on 2026-10-12.
- **Decision:** The store is `depth_history` in TimescaleDB, as [[decision-log|D-028]] set.
  The grain is one row per road piece and moment.
  When two runs cover the same moment, the run with the later `issued_at` wins for every piece of that moment.
  A piece that an earlier run wets and the winning run does not wet gets a row with depth 0, or its earlier row is removed, so the earlier depth does not stay as the answer.
  History is kept one year, which supersedes the several-year target of [[decision-log|D-028]].
  The proposal for [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is compression of each chunk once it closes, and a drop policy at 365 days.
  A table `history_moment`, with `valid_time` as primary key and `issued_at`, gets a row for every moment a run covers, even when no piece is wet.
  Consumer rule: a moment in `history_moment` with no row for a piece means dry (0 m).
  A moment not in `history_moment` means unknown, for example a slot that the 5 mm/h rain gate skipped ([[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]]).
  The consumer rule in [[EP-21-industry-analysis-on-the-flood-data|EP-21]] is confirmed for the read-only consumer and the pipeline as the only writer of the contract tables (its first bullet under "Dependencies and assumptions").
  It is changed for the history: a missing row means dry only when the moment is in `history_moment`.
  The rule for `flood_road_values` does not change.
- **Why:** The measured latest-wins series holds 319,573 rows over three local days, and 297,244 of them fall on the replay storm day (`US-105`, "Evidence and details").
  TimescaleDB 2.30.1 compresses that sample 11.4 times, so one year of storm days is about 1.3 GB.
  A missing row cannot say dry or unknown alone, because a run that wets no piece writes no rows, and a skipped run writes no rows either.
  The `history_moment` table is the cheapest way to tell those apart.
- **Alternatives:** (1) Write a row for every piece at every moment, the ceiling of about 3.4 million rows a day. Rejected, because most of those rows would say 0. (2) Keep `depth_history` alone, with no moment table. Rejected, because a skipped run and a dry moment would look the same.
- **Evidence:** The measurements in `US-105`, "Evidence and details", taken on the server and on a scratch hypertable on TimescaleDB 2.30.1 on 2026-10-10.
  The sample ordered runs by `file_id`, and the decision orders them by `issued_at`.
  Across the 80 runs on the server, `file_id` order and `issued_at` order agree for 79 of 80 runs and disagree for one pair.
  `file_id` 523 has run timestamp 2026-10-10 19:00 but was written after `file_id` 522 (timestamp 20:15).
  The 319,573 row count and the compression ratio do not depend on which run wins, but the depth values of overlapping moments between files 522 and 523 could.
  The routing writer in `scripts/flood_roads/flood_on_roads.py` picks "the newest run with rows at that time", which is not the same rule as the one above, so US-106 must settle the two.
- **Affects:** [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]], [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], [[decision-log|D-028]], [[EP-21-industry-analysis-on-the-flood-data|EP-21]], and [[timescaledb-schema]].
- **Revisit if:** the product owner rejects the `history_moment` table, the measured row size or compression on a longer storm series differs far from 141 bytes and 11.4 times, an analysis needs more than one year, or an analysis needs forecast error or lead time ([[decision-log|D-028]]).

## D-033: Keep the edge depth files for the newest 8 runs, the count of the depth rasters

- **Date:** 2026-10-12
- **Status:** active. The contract row and the edge depth format page change to 8 when [[US-112-keep-the-edge-depth-files-to-the-contract-count|US-112]] is `Done`.
- **Decided by:** The product owner, on 2026-10-12, at Sprint 13 planning.
- **Decision:** The edge depth files (`EDGE_TABLE_KEEP_RUNS`) keep the newest 8 runs, not the newest 3 that the contract named.
  The count matches `flood_depth_raster_tile`, which keeps the newest 8 runs (`FLOOD_RASTER_KEEP_RUNS`, default 8).
- **Why:** The product owner gave the reason as "so that it matches the depth tif we saved".
  The depth rasters that are saved are the rows of `flood_depth_raster_tile`, which [[US-028-store-depth-rasters-as-tiles-and-read|US-028]] measured at exactly 8 run timestamps on 2026-09-29.
  The `depth_*.tif` files on disk are not kept by count, because the 24-hour cleanup of the depth folder removes them.
- **Alternatives:** (1) Keep 3, the count in [[core-output-contract]] and the code default. Not chosen. (2) Keep the value of 100 that the second replay set in the server `.env`. Not chosen.
- **Evidence:** [[core-output-contract]], "Retention", which lists 8 for `flood_depth_raster_tile` and 3 for the edge depth files. [[US-112-keep-the-edge-depth-files-to-the-contract-count|US-112]], which found about 35 `.bin` files on 2026-10-11.
- **Affects:** [[US-112-keep-the-edge-depth-files-to-the-contract-count|US-112]], [[core-output-contract]], [[edge-depth-table-format]], `dags/routing_adapter_dag.py` (the default of `EDGE_TABLE_KEEP_RUNS`), and `compose.yml`.
- **Revisit if:** the product owner changes the count, a consumer needs an edge depth file older than the newest 8 runs, or the depth rasters and the edge depth files stop covering the same runs.

## D-034: Keep TIME_AWARE_ROUTING on for floodmap-backend

- **Date:** 2026-10-12
- **Status:** active. The product owner gave the go on 2026-10-12.
  The server reads `TIME_AWARE_ROUTING=true` for `floodmap-backend` as of about 10:50 +07 on 2026-10-12, by the read-back in Evidence.
- **Decided by:** The product owner, on 2026-10-12, at Sprint 13 planning (open decision 7 of [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]).
- **Decision:** `TIME_AWARE_ROUTING` stays on for `floodmap-backend`.
  Making it stay on on the server means `scripts/routing_proof/rollout.ps1 -LeaveOn` and `TIME_AWARE_ROUTING=true` in the server `.env`.
- **Why:** No reason came with the decision in the planning input, and none is recorded here.
  The flag was off at rest on 2026-10-08, and the live readings of [[US-091-measure-how-often-a-single-timestep-route|US-091]] turned it on for one reading each on 2026-10-10, and the script turned it off after each reading ([[graphhopper-backend]]).
- **Alternatives:** Turn the flag off again after each reading, the state that [[US-091-measure-how-often-a-single-timestep-route|US-091]] left. Not chosen.
- **Evidence:** [[graphhopper-backend]] and [[architecture-block-diagram]], which record the flag, the `-LeaveOn` switch, and the state of the server at rest.
  Server read-back, 2026-10-12 at about 10:50 +07: `printenv TIME_AWARE_ROUTING` in the container `airflow_new-floodmap-backend-1` prints `true`, the container is `Up`, and `GET /health` from the worker returns 200.
  Only `floodmap-backend` reads the flag (`compose.yml`, line 425).
  The change was made without `rollout.ps1`, because that script builds images and a `docker build` over SSH fails on the credential helper.
  A backup of `.env` was taken first, `TIME_AWARE_ROUTING=true` was appended to it, and `docker compose up -d --no-deps floodmap-backend` ran on the host.
  No screenshot was taken, so the read-back is the evidence.
- **Affects:** `scripts/routing_proof/rollout.ps1`, the server `.env`, and [[graphhopper-backend]].
- **Revisit if:** the product owner changes the decision, or a server reading shows the flag in a state other than the one this decision sets.

## D-035: Set the archive free-space floor at 50 GB, and allow a lowered rain gate to prove the archive

- **Date:** 2026-10-12
- **Status:** superseded by D-037.
- **Decided by:** The product owner, on 2026-10-12, at Sprint 13 planning (open decisions 1 and 2 of [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]).
- **Decision:** The free-space floor `ARCHIVE_MIN_FREE_GB` is 50 GB.
  The copy fails loudly when the free space of D: is below it ([[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]]).
  If no forecast passes 5 mm/h by 2026-10-23, a lowered rain gate may prove the archive in [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]].
  This decision does not set the value of the lowered gate.
- **Why:** The 50 GB floor was a proposal, about 8 percent of the 586 GB that was free on 2026-10-08, and the product owner confirmed it.
  The proof in [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] waits for a forecast above 5 mm/h, so the lowered gate lets the proof run if no such forecast comes by 2026-10-23.
  The planning input gave no other reason for either answer.
- **Alternatives:** None were recorded at planning.
- **Evidence:** [[US-094-archive-results-3di-nc-and-a-run|US-094]] sets the default of `ARCHIVE_MIN_FREE_GB` to 50.
- **Affects:** [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], [[US-094-archive-results-3di-nc-and-a-run|US-094]], and [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]].
- **Revisit if:** the product owner sets a value for the lowered gate, or D: falls below the floor during the archive proof.

## D-036: Record the moments of a run that wets no road piece as dry, at depth 0 cm

- **Date:** 2026-10-12
- **Status:** active.
- **Decided by:** The product owner, on 2026-10-12, at Sprint 13 planning (the open question of [[US-113-backfill-per-segment-depth-history|US-113]]).
- **Decision:** A run that wets no road piece writes no rows to `flood_road_values`.
  Its moments are recorded as dry, at depth 0 cm.
  This applies the dry rule of [[decision-log|D-032]] to such a run.
- **Why:** The product owner decided the question, and the planning input gave no reason.
  A run that wets no piece leaves no rows that could show its moments as dry.
- **Alternatives:** Skip such a run, which leaves its moments unknown. The open question of [[US-113-backfill-per-segment-depth-history|US-113]] named this option. Not chosen.
- **Evidence:** [[US-105-decide-what-flood-history-the-industry-apps-need|US-105]], Evidence item 5, which found that a run that wets no piece writes no rows.
- **Affects:** [[US-113-backfill-per-segment-depth-history|US-113]], [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], and [[decision-log|D-032]].
- **Revisit if:** [[US-113-backfill-per-segment-depth-history|US-113]] finds that the moments of such a run cannot be read from any source the team keeps.

## D-037: Withdraw the lowered rain gate of D-035, and keep the 50 GB floor

- **Date:** 2026-10-12
- **Status:** active. It supersedes [[decision-log|D-035]], and the 50 GB floor that D-035 set stays active here.
- **Decided by:** The product owner, on 2026-10-12, the same day as D-035, after saying that no rain is expected.
- **Decision:** The lowered rain gate that [[decision-log|D-035]] allowed is withdrawn, and no lowered gate is set.
  The rain gate of 5 mm/h stays for [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]].
  The 2026-10-23 cutoff is removed.
  The free-space floor `ARCHIVE_MIN_FREE_GB` is 50 GB, and it stays active.
- **Why:** The owner said that no rain is expected, so the proof in [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] waits for a real forecast above 5 mm/h.
  The owner kept the 5 mm/h gate, and the planning input gave no other reason.
- **Alternatives:** None were recorded on 2026-10-12.
- **Evidence:** The product owner's answer on 2026-10-12, and the D-035 entry, which keeps the earlier wording as the record.
  [[US-094-archive-results-3di-nc-and-a-run|US-094]] sets the default of `ARCHIVE_MIN_FREE_GB` to 50.
- **Affects:** [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]], [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]], and the Next action block of [[TODOS]].
- **Revisit if:** the product owner sets a value for a lowered gate, or D: falls below the floor during the archive proof.

## D-038: Keep flood_road_values and the edge depth table, and fix the winner query with the run registry

- **Date:** 2026-10-12
- **Status:** proposed. The product owner accepts it, or chooses another option.
- **Decided by:** Awaiting the product owner. The spike [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]] recommends it.
- **Decision:** Keep `flood_road_values` for the map, the route fallback, the metrics, and the history, and keep the edge depth table for the routing engine.
  Fix the stale overlay by making the winner query of `flood_areas.py` read the run registry `flood_road_file`, so a run with no wet piece wins its forecast times with no features.
  Replace later, with a trigger: the export of the graph carries a stable key (the OSM way id and the position along the way), and the metrics read it.
- **Why:** The stale overlay comes from the missing record of a dry run, and a sparse edge table keeps that gap.
  `graph_edge` has no stable key, so history and metrics keyed on `edge_id` break at each re-import.
  A sparse edge table has 11,650 to 16,370 rows per run against about 20,000, so it does not save storage.
  A merged sampler saves up to 62 s of 136 s per run, but the `9c` time already grows along a chain ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]]).
- **Alternatives:** (1) Replace `flood_road_values` with the edge depth table now. Not chosen, because of the missing key and the metrics. (2) Add a sentinel row for a dry run to `flood_road_values`. Not chosen, because the registry already holds the fact and a sentinel row would reach every reader that sums depth.
- **Evidence:** [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]], Evidence and details, points 1 to 7.
- **Affects:** [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] (method decided), [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] (no change: `depth_history` keeps reading `flood_road_values`), and [[decision-log|D-036]].
- **Revisit if:** the export carries a stable key, the `9c` time passes 150 s on average, or a reader needs a piece set that `road_segment` cannot give.

