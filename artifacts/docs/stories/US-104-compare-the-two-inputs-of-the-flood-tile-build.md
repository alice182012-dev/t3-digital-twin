---
date_drafted: 2026-10-10
type: user-story
us_id: "US-104"
title: "Compare the two inputs of the flood tile build"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Ready
kind: spike
priority: P2
estimate: S
sprint: 13
subsystem: flood-extent
source_ideas: []
related: ["[[US-103-move-the-flood-tile-build-into-its-own-dag|US-103]]", "[[minio-flood-extent-pipeline]]", "[[decision-log|D-027]]"]
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

## Evidence and details

Fill this when the spike is answered. A spike records its measured result and needs no screenshot.
