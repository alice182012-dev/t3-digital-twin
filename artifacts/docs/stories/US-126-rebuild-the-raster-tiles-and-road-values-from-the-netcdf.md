---
date_drafted: 2026-10-12
type: user-story
us_id: "US-126"
title: "Rebuild the raster tiles and road values from the NetCDF"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Ready
kind: story
priority: P3
estimate: M
sprint: 14
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-126 Rebuild the raster tiles and road values from the NetCDF

As a developer, I want a script that rebuilds the depth rasters, the raster tiles, and the road values of a run from its NetCDF file when a test needs them, so a changed pipeline can be tested on a real run without keeping the tiles.

The owner decided on 2026-10-12 ([[decision-log|D-039]]) that raster tiles are not restored up front, so this story is built when a test needs them.
The script takes the runs to rebuild as arguments, and it runs the pipeline functions in order for each, in the test database: `calculate_depth` on the NetCDF, the raster tile load of `9b_load_depth_raster`, and `flood_on_roads.compute`.
It uses the same functions as the DAGs and not a copy of them.
A run whose rows already exist in the snapshot is compared and not replaced.

Given a run of the manifest, when the script runs, then `flood_depth_raster_tile` has the 8 steps of that run in the test database.
Given a run that is in the snapshot, when its road values are rebuilt, then the rows equal the snapshot rows.
Given the script run twice, then the counts do not change.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`. A test that needs raster tiles exists. The worker has the 3Di libraries that `calculate_depth` needs.

## Status history

- **2026-10-12, draft.** On demand since the owner's answer of the same day, so it is P3. Raised with [[decision-log|D-039]]. Its size M is a guess. It is rated again when the time of one run is measured, and it is split if it is L.

- **2026-10-12, Ready.** Picked for the sprint at the product owner's request. Its condition, that a test needs raster tiles, is met by [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]], which rebuilds the tiles of the demo step. The worker has the libraries that `calculate_depth` imports (checked 2026-10-12). Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]].

## Evidence and details

Fill this when the story reaches `Done`.
