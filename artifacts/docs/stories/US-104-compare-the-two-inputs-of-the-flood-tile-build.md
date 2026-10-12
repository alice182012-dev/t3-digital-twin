---
date_drafted: 2026-10-10
type: user-story
us_id: "US-104"
title: "Compare the two inputs of the flood tile build"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: In progress
kind: spike
priority: P2
estimate: S
sprint: 13
subsystem: flood-extent
source_ideas: []
related: ["[[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]]", "[[minio-flood-extent-pipeline]]", "[[decision-log|D-027]]", "[[BL-029-postgis-tile-input-drops-every-polygon|BL-029]]"]
tags: [user-story, spike]
---

# US-104 Compare the two inputs of the flood tile build

Question: does the `flood_tiles` DAG build the map's tiles faster and with the same output when it reads the `depth_*.tif` files of task 3 (`FLOOD_TILES_INPUT=files`) or the raster table `flood_depth_raster_tile` (`FLOOD_TILES_INPUT=postgis`)?

Timebox: one sprint at most, and the measurements are a few hours of server time.

The answer decides whether the tile build can leave the worker's disk, which a future 3D view or cost estimate may need.
It ends with the measured result in this story and an update of [[decision-log|D-027]].

Given the branch of [[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]] on the server, when both modes build the same runs, then the story records the numbers below for each mode and names the faster mode that also passes the output check.

Dependencies: [[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]] is deployed and `Done`.

## What to measure

1. **Time in the task.** The task returns `input_seconds` (zero for `files`, the export for `postgis`) and `build_seconds` for each run. Read them from the XCom of 20 or more runs of each mode on the same storm.
2. **Time to the map.** From the end of `3_calculate_depth` to the end of `9_build_flood_tiles`, read from the task instances. In `postgis` mode the tile build waits for `9b_load_depth_raster`, so this is where the two modes differ most.
3. **Same output.** Build one run in `files` mode, save the area per band and the tile count of each timestep, rebuild the run in `postgis` mode, and compare. The export is in EPSG:4326 and the tile engine reads a raster in the source CRS, so check that the areas agree within 1 percent and the tile count is equal.
4. **Load.** The size of the export (`ST_Union` of the tiles of one step) and its time on the storage database while `routing_adapter` runs.

The modes write the same bucket and the same rows, so run one at a time, with `flood_tiles` paused between switches.
`flood_depth_raster_tile` keeps 8 runs, so the `postgis` mode can rebuild a stored run. The `files` mode can rebuild only a run whose folder is younger than 24 hours.

## Status history

- **2026-10-10, draft.**
  The code for both modes is on the branch `us-103-flood-tiles-dag` (`scripts/flood_extent/raster_export.py` and the `FLOOD_TILES_INPUT` switch in `dags/flood_tiles_dag.py`).
  Nothing is measured yet.
  `compose.yml` passes `FLOOD_TILES_INPUT` (default `files`) to the Airflow containers. A switch means a new value in the server `.env` and a recreate of the scheduler and the DAG processor, since DAG files read it at parse time.
- **2026-10-12, Ready.** The dependency [[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]] is `Done`, so the story passes the INVEST check. Picked for Sprint 13 at S (2 points).
- **2026-10-12, Reviewed.** Answered with 5 paired runs, and the owner called the answer clear after the fifth. The `files` mode stays. The `postgis` mode builds no tiles as shipped ([[BL-029-postgis-tile-input-drops-every-polygon|BL-029]]), and the fixed variant is slower and fails the output check. [[decision-log|D-027]] is updated. Waits for the owner's acceptance.
- **2026-10-12, In progress.** The owner rejected the answer at review. The reason is not recorded yet. The result under Evidence and details is the first attempt, and the story stays in Sprint 13.

## Evidence and details

**Answer:** keep `FLOOD_TILES_INPUT=files`. The `postgis` mode is not faster, and it does not pass the output check.

**Evidence:** `marie-curie/us-104/bench_tiles.py` and its raw output `marie-curie/us-104/results.jsonl` (5 paired runs, measured on the server on 2026-10-12). A spike builds nothing that ships, so it has no screenshot.

**Details:**

1. The method differs from the plan above.
   The harness ran in the Airflow worker and called the same functions as the DAG (`calculate_depth.process_single_step`, `raster_load.load_run`, `raster_export.export_run`, `publish.publish_run`).
   It read the 3Di results of the storm test dataset ([[test-dataset]]), loaded a scratch schema in `storage-postgres`, wrote two scratch buckets, and passed `db_conn=None`.
   So the live tables, the live bucket, `.env`, and the scheduler were not touched, and `flood_tiles` stayed on `files`.
   The DAG switch was not made, so "time to the map" and the load of the export while `routing_adapter` runs are not measured.
   Each run built the first 2 steps, one mode at a time, on an otherwise idle worker. The scratch schema and buckets are dropped.
2. The `postgis` mode as shipped builds no tiles ([[BL-029-postgis-tile-input-drops-every-polygon|BL-029]]).
   `raster_export.export_run` writes EPSG:4326, and the engine compares `min_area` (20 m²) with areas in the layer's unit, so `clean` drops every polygon and the build fails with `'NoneType' object has no attribute 'GetLayer'`.
   The variant measured below warps each exported file to EPSG:3405 first.
3. Time in the task, in seconds, for the first 2 steps of 5 runs:

   | Run | Flooded area (km²) | `files` build | `postgis` input | `postgis` build | `postgis` total |
   | --- | --- | --- | --- | --- | --- |
   | `20261010T041500` | 1.80 | 56.8 | 32.2 | 64.3 | 96.5 |
   | `20261010T044500` | 2.33 | 74.7 | 35.0 | 73.7 | 108.6 |
   | `20261010T053000` | 3.75 | 105.7 | 33.8 | 108.4 | 142.1 |
   | `20261010T061500` | 4.99 | 130.6 | 35.2 | 128.6 | 163.8 |
   | `20261010T070000` | 5.85 | 150.7 | 33.0 | 144.3 | 177.3 |

   The `files` input time is 0. The `postgis` input is 24 to 27 s of export plus about 8 s of warp, for 438 MB of GeoTIFF per run.
   The median total is 105.7 s for `files` and 142.1 s for `postgis`, so `postgis` adds 32 to 35 s to every run.
   The build time of both modes grows with the flooded area, because the band dissolve has more polygons to union. The input mode does not change this.
4. The two modes do not give the same output.
   The tile counts of the first run were 217 (`files`) and 221 (`postgis`), and equal in the other four.
   The area of the worst band differs by 1.53, 1.67, 1.33, 1.08, and 1.01 percent, so no run passes the 1 percent check.
   The warp resamples the raster, which moves the band edges.
5. The `postgis` mode also needs the raster table first.
   `9b_load_depth_raster` took 121 to 130 s for the 59 steps of a run in the first 4 runs, and the tile build waits for it in this mode. The `files` mode starts when `3b` ends.
6. The live `flood_tiles` runs of 2026-10-10 took 1.3 to 2.1 minutes in `files` mode, which matches the build times above (57 to 151 s for 2 steps).
7. What would change the answer: a fix of [[BL-029-postgis-tile-input-drops-every-polygon|BL-029]] that keeps the raster in its source CRS or makes the engine unit-aware, and a need to build tiles on a host that does not share the worker's disk.
   A fix would remove the warp (8 s) but not the export (24 to 27 s) or the wait for `9b`.
