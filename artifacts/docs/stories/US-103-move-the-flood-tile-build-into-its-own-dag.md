---
date_drafted: 2026-10-10
type: user-story
us_id: "US-103"
title: "Move the flood tile build into its own DAG"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Done
kind: story
priority: P2
estimate: M
sprint: 
subsystem: flood-extent
source_ideas: []
related: ["[[minio-flood-extent-pipeline]]", "[[raster-first-flood-pipeline]]"]
tags: [user-story]
---

# US-103 Move the flood tile build into its own DAG

As the development team, I want the map's tile build to run as a consumer of the depth rasters, outside the simulation DAG, so a later consumer (a 3D view, a building cost estimate) plugs in without touching `flood_mapping_full`.

This is prep work.
No 3D view and no cost estimate are built here.

Given a run of `flood_mapping_full` that finishes task 3, when the run ends, then `flood_tiles_dag` publishes the same tiles and audit rows that task `9_build_flood_tiles` publishes today, and the map overlay looks the same.

Dependencies: [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]].
The replay that US-102 ran on the DAG stopped at 18:49 +07 on 2026-10-10, so the DAG may change now.

## Plan

1. **A new Asset for the depth files.**
   `9b_load_depth_raster` already emits `FLOOD_DEPTH_RASTER` in `dags/core_assets.py`, and `routing_adapter_dag` runs on it.
   Task 9 reads the depth `.tif` files from disk, not the PostGIS table, so the tile DAG needs an event that says the files exist.
   Add a second Asset emitted by `3_calculate_depth`, with `run_ts` and the depth directory in its extra.
   Decide in the first step whether to reuse the PostGIS raster as the input instead, and record the choice in `decision-log.md`.
2. **Create `flood_tiles_dag.py`.**
   Move `task_build_flood_tiles` and its constants (`FLOOD_EXTENT_*`) there.
   `schedule=[<the new Asset>]`, with `run_ts` read from the event, the same way `routing_adapter_dag` reads it.
   Keep `scripts/flood_extent/publish.py` unchanged.
3. **Move the local file cleanup.**
   `publish_run` deletes `RESULT_DIR`, `DEPTH_ROOT_DIR`, and the work dir after 24 hours.
   Once the tile DAG is a separate consumer, a file must not be deleted while any consumer still needs it.
   Keep the 24 hour age rule, which already makes the race with task 9b safe, and name the owner of the cleanup in the concept page.
4. **Remove task 9 from `flood_mapping_dag.py`.**
   Keep `2b_archive_results`, `2c_archive_done`, and `9b` as they are.
   Check that the new Asset fires on every run that fired task 9 before, including the test-rain skip.
5. **Update [[minio-flood-extent-pipeline]]** (the DAG section and `last_updated`).

## Acceptance check

On the server, after the replay has stopped and the change is pulled:

1. One `flood_mapping_full` run finishes, and `flood_tiles_dag` starts from the Asset event without a manual trigger.
2. `runs/<run_ts>/` in the `flood-extent` bucket holds the same timestep folders as the previous run.
3. The frontend shows the same flood overlay for that run.
   Use a test point inside the model border.
4. `flood_extent_step` has one row per timestep for the run.

## Status history

- **2026-10-10, draft.**
  Written during the replay.
  The code was built on a branch on the Mac and was held back from the server while the replay ran, since an edit to `flood_mapping_dag.py` would have changed the DAG under test.
  The replay stopped at 18:49 +07 on 2026-10-10, so the change may now be pulled.
  `flood_mapping_full` stays paused until the branch `us-103-flood-tiles-dag` is pulled on the server.
- **2026-10-10, code written on branch `us-103-flood-tiles-dag`.**
  It decided the open design choice ([[decision-log|D-027]]): an Asset `flood_depth_files`, emitted by the new task `3b_publish_depth_files`, which runs after `3_calculate_depth`, `2c_archive_done`, and `0b_ensure_schema`.
  The `.tif` folder is the default input. A second input, the PostGIS raster, is in the code behind `FLOOD_TILES_INPUT=postgis`, and [[US-104-compare-the-two-inputs-of-the-flood-tile-build|US-104]] measured the two and was archived without a decision to use the second.
  The unit tests pass on the Mac.
  The server acceptance check below is still open.
- **2026-10-10, Done.**
  The server acceptance check passed at about 22:20 +07, and the evidence below was taken then.
  The concept page [[minio-flood-extent-pipeline]] already documents the `flood_tiles` DAG, with `last_updated` set to 2026-10-10, so the status moved to `Done`.

## Evidence and details

![[us-103-flood-overlay-server.png|420]]

Caption: the live frontend at `100.67.84.55:8082`, captured 2026-10-10 at about 22:20 +07, with the legend "As of 10/10/2026 22:15" and the flood overlay on.
The two z13 `.pbf` tiles that returned 404 are empty tiles, which are not published by design.

1. Check 1, the trigger: the asset-triggered `flood_tiles` runs from 13:38Z to 15:04Z on 2026-10-10 all ended `success`.
   Each one started within 1 second of the end of the `flood_mapping_full` run that triggered it, with no manual trigger.
2. Check 2, the bucket: `runs/20261010T220000` and `runs/20261010T221500` in the `flood-extent` bucket each hold 2 timestep folders.
3. Check 3, the frontend: the map showed the flood overlay, and the legend read "As of 10/10/2026 22:15".
   The two z13 `.pbf` tiles returned 404, which is expected because the map treats a missing tile as empty (see [[minio-flood-extent-pipeline]]).
4. Check 4, the audit rows: `flood_extent_step` holds 2 rows per run, each with `is_empty` false, for the runs 20261010T214500 to 20261010T221500.
   Since 20261009T231500, 76 distinct runs have rows.
5. Server state: the server checkout was on branch `us-103-flood-tiles-dag`, at the commit with the message "Add a constant 5 mm/h, 2 hour rain event for the US-103 acceptance check", and it was clean.
6. Server state: `flood_tiles` and `flood_mapping_full` were both unpaused when checked.
   This story does not record who unpaused `flood_mapping_full`.
