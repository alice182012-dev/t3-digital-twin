---
date_drafted: 2026-10-12
type: user-story
us_id: "US-129"
title: "Pin the peak step of the demo flood"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
kind: story
priority: P2
estimate: M
sprint: 14
subsystem: flood-extent, core-output
source_ideas: []
related: ["[[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]", "[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[test-dataset]]"]
tags: [user-story]
---

# US-129 Pin the peak step of the demo flood

As a visitor on a day with no rain, I want the demo flood to stay available however many runs the pipeline makes, so the map always has a flood to show.

Part two of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]].
The demo is one static frame, the peak step of the replay of the 2026-09-16 storm.
The 58 runs of [[test-dataset]] are that replay.
This story chooses the peak step, and it keeps every table row and file of that step where no prune reaches them.

The prunes that would remove a step are these:

- `flood_extent_step`, `flood_extent_polygon`, `flood_depth_raster_tile`, and the vector tiles in MinIO keep the newest 8 runs (`FLOOD_EXTENT_KEEP_RUNS`).
- `edge_depth` and `edge_depth_run` keep the 24 hours before the newest run (`EDGE_DEPTH_KEEP_HOURS`), and the edge depth files keep the newest 8 (`EDGE_TABLE_KEEP_RUNS`).
- `flood_road_values` keeps 24 hours, until [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes the table.

The tile build tiles only the first `FLOOD_EXTENT_TILE_STEPS` (2) steps of a run, so the story first rebuilds the tiles of the chosen step ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]]).

Given the 58 runs of the test dataset, when the story ends, then it records the run and the step that it chose and the reason, which is the step with the most wet edges.
Given the chosen step, then its depth raster tiles, its extent polygons and vector tiles, and its edge depth rows and file exist under names that no prune matches.
Given more runs than the limits allow, when every prune has run, then the pinned step still has all of them.

Dependencies: [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] is in the same sprint, and [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] is `Done`.

## Acceptance check

On the server. Use a test point inside the model border (the rule in `.claude/CLAUDE.md`).
Take a screenshot of the listing of the pinned rows and files before and after the prunes ran.

1. Given the pinned step, then a query lists its rows in each table and its files in MinIO and in the edge depth folder.
2. Given a run of the prunes with `FLOOD_EXTENT_KEEP_RUNS` and `EDGE_TABLE_KEEP_RUNS` below the number of runs, then the listing is the same.

## Status history

- **2026-10-12, Ready.** Split from [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] at the product owner's request. It is picked for [[SPR-014-finish-the-remaining-backend|SPR-014]], and it has no code yet.
- **2026-10-12, Reviewed.** Built and tested, not deployed. Table `demo_pin` holds one row, the pinned run and step, and `scripts/database/demo_pin.py` fills it. By default it picks the step with the most wet edges in `edge_depth`, the earliest on a tie. `--run` and `--valid-time` take a given step. Every prune of a run table keeps the pinned run as well as the run it publishes, and takes a collection of runs where it took one. The prunes are the ones of `flood_depth_raster_tile`, `flood_extent_step`, `flood_extent_polygon`, `flood_run_output`, the MinIO tiles, `edge_depth` and `edge_depth_run`, and the edge depth file. The prune of `flood_road_values` is left out, because [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes that table. The pin keeps the whole run (8 steps) and not a copy of one step, so the story's names that no prune matches hold by exclusion. 174 tests in `scripts/edge_depth`, 50 in `scripts/flood_extent`, and 27 in `scripts/database` pass against a throwaway PostGIS. Still open: the storm runs in `edge_depth` (it keeps 24 hours, and the test dataset snapshot has no `edge_depth` yet), the tiles of the chosen step ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]], because the tile build tiles only the first two steps), the choice of the step, and the listing before and after the prunes.
- **2026-10-13, Reviewed.** On the server, `demo_pin.py` pinned run `20261011T001500` at 2026-10-10 19:00 UTC, with 2,853 wet edges (screenshot `US-129-server-demo-pin-2026-10-13.png`). The tiles of both stored runs were already in `flood_depth_raster_tile`, 8 steps each, so no tile rebuild was needed. The owner then unpaused `flood_mapping_full`, and a run left over from 2026-10-10 resumed (its `3_calculate_depth` restarted at 03:19 UTC) and published run `20261011T003000` at 03:25 UTC. The state before and after is in `US-129-server-prune-before-after-2026-10-13.txt`. The pinned run `20261011T001500` stays in `edge_depth_run`, `edge_depth`, the edge depth files, and `flood_depth_raster_tile`. The prune deleted the oldest edge depth file (`20261010T211500.bin`) and the oldest tile run, and `edge_depth` kept 3 runs. Limit: the pinned run was the second newest, so it was inside the kept window and the run does not show the pin protecting a run that would otherwise be pruned. Still open: the owner's acceptance.
- **2026-10-13, Done.** The product owner accepted it. The evidence is the screenshot `US-129-server-demo-pin-2026-10-13.png` and the listing `US-129-server-prune-before-after-2026-10-13.txt`. The prune check ran with the default keep counts, so it does not show the pin protecting a run that would otherwise be pruned, and the owner accepted the story with that limit.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/US-129-server-demo-pin-2026-10-13.png` (the `demo_pin` row) and `artifacts/docs/stories/evidence/US-129-server-prune-before-after-2026-10-13.txt` (the pinned rows and files before and after a prune).

**Details:**

1. `create_demo_pin_table.py` ran in the worker and made `demo_pin`.
2. `demo_pin.py` with no arguments pinned run `20261011T001500` at 2026-10-10 19:00 UTC, the step with 2,853 wet edges in `edge_depth`.
3. The tiles of both stored runs were already in `flood_depth_raster_tile`, 8 steps each, so no tile rebuild was needed ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]]).
4. A run left over from 2026-10-10 resumed when the owner unpaused `flood_mapping_full`, and it published run `20261011T003000` at 03:25 UTC.
   The prunes of that publish deleted the oldest edge depth file (`20261010T211500.bin`) and the oldest tile run.
   `edge_depth_run` and `edge_depth` kept 3 runs.
5. The pinned run stays in `edge_depth_run`, `edge_depth`, the edge depth folder, and `flood_depth_raster_tile` after the prune.
6. Limit: the pinned run was the second newest, so it was inside the kept window.
   The run does not show that the pin protects a run that falls outside the window.
   The listing does not include MinIO, because no vector tile of the pinned run was part of the check.
7. For [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]]: the backend reads `demo_pin` as `routing_reader`, which can `SELECT` the table.
