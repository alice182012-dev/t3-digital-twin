---
date_drafted: 2026-10-12
type: user-story
us_id: "US-124"
title: "Save the storm-replay results and derived data"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Reviewed
kind: story
priority: P1
estimate: S
sprint: 
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-124 Save the storm-replay results and derived data

As a developer, I want the results and derived data of the 12-hour storm replay kept in a folder that no cleanup touches, so every test can use the same real storm.

The 58 runs of the replay of 2026-10-10 (slots 04:00 to 18:15 +07) have their `results_3di.nc` in `data/mapping/results`, which `flood_tiles` empties of files older than 24 hours on the next publish.
The story copies them to `data/testdata/storm-2026-10-10/nc/`, writes a manifest, and saves the derived data that still exists as a snapshot.
The layout and the file list are in [[test-dataset]].

Given the folder on the server, when each `results_3di.nc` is hashed, then it equals the SHA-256 in `manifest.json`.
Given the snapshot, when each CSV is read, then its row count equals the manifest.

Dependencies: None.

## Status history

- **2026-10-12, Reviewed.** Built on 2026-10-12 by the lead, outside a sprint, because the next core run would delete the NetCDF files. Waiting for the owner's acceptance.

## Evidence and details

**Evidence:** the checks of 2026-10-12 on the server, read from the files themselves.

**Details:**

1. 58 `results_3di.nc` files, 423,859,437 bytes (405 MB), copied from `data/mapping/results/<sim_id>/` to `data/testdata/storm-2026-10-10/nc/<sim_id>/`. Each copy was hashed against its source (0 mismatches), and the folder is read-only.
2. `manifest.json` has, for each run, the `sim_id`, the `run_ts` (from `9b_load_depth_raster`), the slot in +07, the `rain_ingested` of `1_trigger_simulation`, the size, and the SHA-256. The dataset has model 84916, graph hash `8c13d8841f83`, and the rain source `replay:hanoi_20260916_storm.csv`.
3. `snapshot/` holds the derived data that existed: `flood_road_file` (58 rows), `flood_road_values` (1,573,912 rows, 172.7 MB compressed), `flood_extent_step` (116), `flood_extent_polygon` (812 rows, 1.4 GB), `road_segment` (35,652), `graph_edge` (67,833), `graph_edge_export` (1), the 58 edge depth files (62,958,246 bytes), and `graph.json` and `edges.csv` of the graph export. `snapshot/MANIFEST.json` has the row counts and the checksums.
4. Verified from the files: 58 of 58 NetCDF checksums match, all 8 CSV row counts equal the manifest, and 60 of 60 edge depth and graph export files match their checksums.
5. Not in the snapshot, because it does not exist for these runs: the raster tiles (the table keeps the newest 8 runs), the depth GeoTIFFs (24-hour cleanup), the MinIO vector tiles, `depth_history`, and `flood_segment_metrics` (0 rows for these runs). [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] and [[US-127-rebuild-edge-tables-history-and-metrics-from-the-rebuilt-data|US-127]] rebuild them.
6. The folder is `D:\airflow_new_data\data\testdata\storm-2026-10-10\` on the host, 2.1 GB with 577 GB free on D:. D: is a hard disk drive.
