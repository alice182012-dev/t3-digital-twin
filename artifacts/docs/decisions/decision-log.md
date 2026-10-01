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

## Open decisions

1. What the map shows by default: the situation now, or the nearest forecast timestep. No t0 raster exists today, and routing and
   the histogram do not yet handle the forecast side. The options and questions are in the blocker [[map-shows-forecast-not-now]].
   Decide this before the route-forecast query and the chart are built, because it changes both.

The question of which depth the flood metric extractor and TimescaleDB metrics use is settled by D-006: they read `depth`, which
is the maximum.
