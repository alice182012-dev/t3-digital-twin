---
date_drafted: 2026-10-10
type: user-story
us_id: "US-103"
title: "Move the flood tile build into its own DAG"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Not started
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

Dependencies: [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] (do not change the DAG the replay is testing).

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
  The code is built on a branch on the Mac and is not pulled to the server until the replay stops, since an edit to `flood_mapping_dag.py` changes the DAG under test.
- **2026-10-10, code written on branch `us-103-flood-tiles-dag`.**
  It decided the open design choice: an Asset `flood_depth_files`, emitted by the new task `3b_publish_depth_files`, which runs after `3_calculate_depth`, `2c_archive_done`, and `0b_ensure_schema`.
  The PostGIS raster was not used as the input, because the tile code reads `.tif` files.
  The unit tests pass on the Mac.
  The server acceptance check below is still open.

## Evidence and details

Fill this when the story reaches `Done`.
