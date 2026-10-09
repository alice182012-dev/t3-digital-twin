---
date_drafted: 2026-09-24
type: user-story
us_id: "US-028"
story_label: "2"
epic: "[[EP-06-raster-first-pipeline]]"
status: Done
priority: P0
estimate: M
sprint: 2
subsystem: airflow-pipeline
related: ["[[EP-06-raster-first-pipeline]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Store depth rasters as tiles and read them through a spatial index"
---

# US-028 Store depth rasters as tiles and read them through a spatial index

As the point-depth endpoint, I want each timestep stored as tiles, so a lookup touches one tile
instead of unpacking a 209 MB raster, and old runs are removed.
Given the real `depth_20260924_170639.tif`, when it is loaded as tiles, then `ST_Value` at three
points matches `gdallocationinfo`, a lookup on the server is faster than the current 80 to 280 ms,
and only the newest runs are kept (`FLOOD_RASTER_KEEP_RUNS`, default 8).
Priority: P0. Status: Done. Estimate: M. Sprint: 2. Dependencies: None.
Evidence: ![[raster-first-pipeline-sprint2-verification.png|420]]
Details:
1. What: each timestep's depth raster is stored as 256 by 256 tiles in `flood_depth_raster_tile`, read through a spatial index, and runs older than the newest `FLOOD_RASTER_KEEP_RUNS` are pruned.
2. How: `load_run` reprojects to EPSG:4326 and cuts tiles with `ST_Tile` in one delete-and-insert transaction. `GET /flood/points` selects the tile under the point, then runs `ST_Value`.
3. Why: the whole-raster lookup unpacked 209 MB per request and took 80 to 280 ms on the server.
4. Effect: deployed on 2026-09-24 (commit `6155f09`). On the server a tile lookup takes a median of 0.56 ms in the database. Retention confirmed on the server 2026-09-29: exactly 8 distinct `run_ts` values hold tiles (oldest `20260928T204500`, newest `20260929T163000`), matching `DEFAULT_KEEP_RUNS` in `raster_load.py`, raised from 3 to 8 by commit `002bdce` (2026-09-25) after this story's acceptance criteria were written; older runs are confirmed gone. The connection-per-request cost is fixed separately, see [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]] (resolved).
