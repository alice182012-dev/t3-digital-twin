---
date_drafted: 2026-10-13
type: user-story
us_id: "US-140"
title: "Delete the postgis input of the flood tile build"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P2
estimate: S
sprint: 
subsystem: flood-extent, airflow-pipeline
source_ideas: []
related: ["[[BL-029-postgis-tile-input-drops-every-polygon|BL-029]]", "[[minio-flood-extent-pipeline]]", "[[decision-log|D-027]]"]
tags: [user-story]
---

# US-140 Delete the postgis input of the flood tile build

As the owner of the pipeline, I want the dead `postgis` input of the flood tile build deleted, so the DAG has one input and no option that fails on every step.

The DAG `flood_tiles` reads `FLOOD_TILES_INPUT`, which is `files` or `postgis`.
With `postgis`, `scripts/flood_extent/raster_export.py` exports each step from `flood_depth_raster_tile` in EPSG:4326, and the tile engine drops every polygon ([[BL-029-postgis-tile-input-drops-every-polygon|BL-029]]).
The owner kept `files` ([[decision-log|D-027]]), the server `.env` does not set the variable, and no user reaches the `postgis` path.
The story deletes the variable and its check in `dags/flood_tiles_dag.py`, the export task and its import, `scripts/flood_extent/raster_export.py` and `test_raster_export.py`, the entry in `compose.yml`, and the tests of the `postgis` mode in `test/test_flood_tiles_dag.py`.
It closes the blocker, and it updates the concept page.

Given a search of `dags`, `scripts`, `floodmap`, `test`, `compose.yml`, and `README.md` for `FLOOD_TILES_INPUT` and `raster_export`, then it finds nothing.
Given the DAG `flood_tiles`, then it imports with no error and builds from the depth files as before.
Given the tests, then `python3 -m pytest -q test/` and the suites of `scripts/flood_extent` pass.

Dependencies: None. Deploy it after the server steps of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], so the pull of that story stays the one that was checked.

## Status history

- **2026-10-13, Ready.** Raised from [[BL-029-postgis-tile-input-drops-every-polygon|BL-029]], whose cleanest fix is to delete the option. It is in the backlog and has no `sprint`, as the product owner asked. The code is built on the branch `us-140-delete-postgis-tile-input`, which is not merged into `modular` until the server steps of US-123 end.
- **2026-10-13, Reviewed.** Built and checked on the branch `us-140-delete-postgis-tile-input` (commit "Delete the postgis input of the flood tile build"), which is not merged into `modular` and not on the server (details items 1 to 4). The owner has not accepted it.

## Evidence and details

**Evidence:** the test counts and the DAG import in details items 2 and 3. No screenshot.

**Details:**

1. Deleted: `scripts/flood_extent/raster_export.py` and `test_raster_export.py`, which had no caller outside themselves. In `dags/flood_tiles_dag.py`: `FLOOD_TILES_INPUT` and its check, the export folder, the `depth_input` context manager (with one mode left it only returned the announced folder, so the `os.path.isdir` check moved into the loop, with the same skip-and-continue for a missing folder), and the imports that became unused. In `compose.yml`: the `FLOOD_TILES_INPUT` line. In `test/test_flood_tiles_dag.py`: the tests of the `postgis` mode and of an invalid value. The DAG schedule and the task inlet are `FLOOD_DEPTH_FILES`, as before.
2. A search of `dags`, `scripts`, `floodmap`, `test`, `analysis-service`, `java`, `minio_custom`, `compose.yml`, `README.md`, and `Dockerfile` for `FLOOD_TILES_INPUT`, `raster_export`, and `TILES_INPUT` finds nothing. `python3 -m pytest -q test/` gives 124 passed and 1 skipped, and `scripts/flood_extent` gives 25 passed and 20 skipped (the database tests, which run through the command of [[US-128-run-the-test-suites-against-the-test-databases|US-128]]).
3. In the worker (Airflow 3, Python 3.12), Airflow's `DagBag` loads the new `dags/` from a temporary folder with no import error, and `flood_tiles` has its one task `9_build_flood_tiles`.
4. The return value of the task lost the keys `input` and `input_seconds`, which only compared the two input modes (`input_seconds` was always 0.0 in the `files` mode). Nothing else in the repository reads them. `FLOOD_DEPTH_RASTER` stays in `dags/core_assets.py`, because task `9b` still emits it.
5. Still open: the merge into `modular` and the pull on the server after the server steps of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], and the closing of [[BL-029-postgis-tile-input-drops-every-polygon|BL-029]] and the update of [[minio-flood-extent-pipeline]] at that merge.

