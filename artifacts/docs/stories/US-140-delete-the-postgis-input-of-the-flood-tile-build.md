---
date_drafted: 2026-10-13
type: user-story
us_id: "US-140"
title: "Delete the postgis input of the flood tile build"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Ready
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

## Evidence and details

Fill this when the story reaches `Done`.
