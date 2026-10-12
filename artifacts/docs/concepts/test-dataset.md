---
date: 2026-10-12
type: concept
status: active
tags: [testing, test-dataset, netcdf, snapshot]
related: ["[[decision-log|D-039]]", "[[EP-22-keep-a-real-storm-as-the-test-dataset|EP-22]]", "[[core-output-contract]]", "[[timescaledb-schema]]", "[[3di-simulation-orchestration]]"]
last_updated: 2026-10-12
---

# Test dataset

The test dataset is the storm replay of 2026-10-10, kept in its own folder so that no pipeline cleanup deletes it.
The decision is [[decision-log|D-039]], and the epic is [[EP-22-keep-a-real-storm-as-the-test-dataset|EP-22]].

## What it holds

- **Runs.** 58 runs of `flood_mapping_full`, slots 04:00 to 18:15 +07 on 2026-10-10, run names `20261010T041500` to `20261010T183000`.
- **Rain.** The replay file `hanoi_20260916_storm.csv`, which `1_trigger_simulation` reports as `replay:hanoi_20260916_storm.csv`.
- **Model and graph.** Model 84916 and graph hash `8c13d8841f83`.

## Layout

The folder is `data/testdata/storm-2026-10-10/` in the worker, which is `D:\airflow_new_data\data\testdata\storm-2026-10-10\` on the server.
The age cleanup of `flood_tiles` sweeps only `data/mapping/results` and `data/mapping/output_depths` (`RESULT_DIR` and `DEPTH_ROOT_DIR` in `dags/core_paths.py`), so this folder stays.
The files are read-only.

| Path | Content |
| ---- | ------- |
| `manifest.json` | One entry per run with `sim_id`, `run_ts`, the slot, the rain input, the size, and the SHA-256 of its NetCDF. |
| `nc/<sim_id>/results_3di.nc` | The 3Di result of the run. This is the source of truth. |
| `snapshot/MANIFEST.json` | The row count and SHA-256 of each snapshot file. |
| `snapshot/<table>.csv.gz` | The rows of `flood_road_file`, `flood_road_values`, `flood_extent_step`, `flood_extent_polygon`, `flood_segment_metrics`, `road_segment`, `graph_edge`, and `graph_edge_export`, as CSV with a header. |
| `snapshot/edge_depth/<run_ts>.bin` | The edge depth file of each run ([[edge-depth-table-format]]). |
| `snapshot/graph_export/` | `graph.json` and `edges.csv` of the graph export. |

## What can be rebuilt

The pipeline functions rebuild every derived table from the NetCDF in this order: `download_result` output to `calculate_depth` (depth GeoTIFF), the tile load of `9b_load_depth_raster`, `flood_on_roads.compute`, `build_edge_depth`, `load_run` of `flood_history`, and `extract_run` for the metrics.
The owner decided on 2026-10-12 that this is done when a test needs it and not up front ([[decision-log|D-039]]).
Four things are not in the snapshot because they did not exist on 2026-10-12: the raster tiles of these runs, the depth GeoTIFFs, the MinIO vector tiles, and `depth_history`.
The restore script does not load raster tiles.
`flood_segment_metrics` has no rows for these runs.

## Verify the folder

The NetCDF checksums are in `manifest.json`, and the snapshot checksums and row counts are in `snapshot/MANIFEST.json`.
Hash each file and compare it with its entry.
On 2026-10-12, 58 of 58 NetCDF files, 8 of 8 CSV files, and 60 of 60 binary and graph files matched ([[US-124-save-the-storm-replay-results-and-derived-data|US-124]]).

## Retention

The dataset has no retention, and the owner deletes it.
The production retention is unchanged: 24 hours for the NetCDF and depth files, 24 hours of `flood_road_values`, the newest 8 runs of tiles and polygons, and the newest 60 edge depth files.
Rana keeps the result of each run until about 2026-11-09, which is a second copy of the NetCDF files.

## Test databases

Two databases on the existing servers: `minio_custom_test` in `storage-postgres` and `flood_metrics_test` in `timescaledb`.
The script `scripts/testdata/restore_snapshot.py` fills them from the snapshot ([[US-125-restore-the-snapshot-into-test-databases|US-125]]).
Run it in the Airflow worker:

```
docker exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/testdata/restore_snapshot.py
```

- **Names.** `TEST_POSTGRES_DB` and `TEST_TIMESCALE_DB` set them. The script refuses a name that does not end in `_test`.
- **Pipeline code under test.** Set `POSTGRES_DB=minio_custom_test` and `TIMESCALE_DB=flood_metrics_test`, and the code reads the test databases.
- **What it loads.** The eight tables of `snapshot/` in foreign key order, in one transaction, so a second run gives the same rows. It runs the DDL of `scripts/database/`, so the other tables exist and are empty. `flood_metrics_test` has the Timescale schema and no rows.
- **Cost.** About 2 minutes for a second run, and 2,628 MB for `minio_custom_test` on 2026-10-12. Docker's local volumes grew by about 3.5 GB.
- **Gaps.** `graph_edge` has no `edge_key`, and `edge_depth` and `edge_depth_run` are empty, because the snapshot predates [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] and [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]].
- **Test.** `scripts/testdata/test_restore_snapshot.py` runs against a throwaway PostGIS, and CI runs it (`restore-snapshot-test.yml`).
