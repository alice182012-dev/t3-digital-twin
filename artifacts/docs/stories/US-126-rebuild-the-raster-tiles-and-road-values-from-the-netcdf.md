---
date_drafted: 2026-10-12
type: user-story
us_id: "US-126"
title: "Rebuild the raster tiles from the NetCDF"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Reviewed
kind: story
priority: P3
estimate: M
sprint: 14
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-126 Rebuild the raster tiles from the NetCDF

As a developer, I want a script that rebuilds the depth rasters and the raster tiles of a run from its NetCDF file when a test needs them, so a changed pipeline can be tested on a real run without keeping the tiles.

The owner decided on 2026-10-12 ([[decision-log|D-039]]) that raster tiles are not restored up front, so this story is built when a test needs them.
The script takes the runs to rebuild as arguments, and it runs the pipeline functions in order for each, in the test database: `calculate_depth` on the NetCDF and the raster tile load of `9b_load_depth_raster`.
It uses the same functions as the DAGs and not a copy of them.
A run whose 8 steps are already loaded is skipped.
The owner dropped the road values on 2026-10-13 ([[decision-log|D-046]]), because [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes them.

Given a run of the manifest, when the script runs, then `flood_depth_raster_tile` has the 8 steps of that run in the test database.
Given the script run twice, then the counts do not change.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`. A test that needs raster tiles exists. The worker has the 3Di libraries that `calculate_depth` needs.

## Status history

- **2026-10-12, draft.** On demand since the owner's answer of the same day, so it is P3. Raised with [[decision-log|D-039]]. Its size M is a guess. It is rated again when the time of one run is measured, and it is split if it is L.

- **2026-10-12, Ready.** Picked for the sprint at the product owner's request. Its condition, that a test needs raster tiles, is met by [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]], which rebuilds the tiles of the demo step. The worker has the libraries that `calculate_depth` imports (checked 2026-10-12). Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]].
- **2026-10-13, In progress.** The tile part is built and checked on the server. `scripts/testdata/rebuild_tiles.py` takes run names of the test dataset, finds each NetCDF in `manifest.json`, runs `calculate_depth.run_calculate_depth`, and loads the result with `raster_load.load_run`, the call of task `9b_load_depth_raster`. It keeps every run in the table, so a rebuild deletes nothing. It writes to the database that `POSTGRES_DB` names. On the server, run `20261010T041500` was rebuilt into `minio_custom_test` in about 5 minutes, with 8 steps and 7,040 rows, and a second run skipped it. The tables of production kept their 8 runs. The runs `20261010T223000` and `20261011T001500` are not in the manifest, and their tiles were already in production. Still open: the road values (`flood_on_roads.compute` and the comparison with the snapshot rows).
- **2026-10-13, Reviewed.** The owner dropped the road values ([[decision-log|D-046]]), so the story is the tile rebuild, which is built and checked on the server (details items 1 to 3). The owner has not accepted it.

## Evidence and details

**Evidence:** the output of the script on the server (details item 2). No screenshot.

**Details:**

1. `scripts/testdata/rebuild_tiles.py RUN_TS ...` takes each NetCDF from `manifest.json`, runs `calculate_depth.run_calculate_depth` into a scratch folder, and loads the result with `raster_load.load_run` into the database that `POSTGRES_DB` names.
   It keeps every run of the table, so it deletes nothing.
   A run with its 8 steps already loaded is skipped.
2. On the server, run `20261010T041500` was rebuilt into `minio_custom_test` in about 5 minutes, with 8 steps and 7,040 rows.
   A second call skipped it, and production kept its 8 runs.
   The 50-run check of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] rebuilds the tiles of the first 50 runs of the manifest the same way, at about 5 minutes per run.
3. `test_rebuild_tiles.py` has 3 tests of the pure function that maps a manifest and run names to the NetCDF paths.
4. The road values are not rebuilt ([[decision-log|D-046]]).

