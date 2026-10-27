---
date: 2026-10-12
type: concept
status: active
tags: [testing, test-dataset, netcdf, snapshot]
related: ["[[decision-log|D-039]]", "[[EP-22-keep-a-real-storm-as-the-test-dataset|EP-22]]", "[[core-output-contract]]", "[[timescaledb-schema]]", "[[3di-simulation-orchestration]]"]
last_updated: 2026-10-13
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
| `snapshot/<table>.csv.gz` | The rows of `flood_road_file`, `flood_road_values`, `flood_extent_step`, `flood_extent_polygon`, `flood_segment_metrics`, `road_segment`, `graph_edge`, and `graph_edge_export`, as CSV with a header. The restore loads only the tables that still exist, so the files of `flood_road_file`, `flood_road_values`, and `road_segment` stay on disk unused ([[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]). |
| `snapshot/edge_depth/<run_ts>.bin` | The edge depth file of each run ([[edge-depth-table-format]]). |
| `snapshot/graph_export/` | `graph.json` and `edges.csv` of the graph export. |

## What can be rebuilt

`scripts/testdata/rebuild_tiles.py` runs the first two steps for the runs it is given ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]]), and the owner dropped the road values ([[decision-log|D-046]]), because [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deletes them.
The pipeline functions rebuild every derived table from the NetCDF in this order: `download_result` output to `calculate_depth` (depth GeoTIFF), the tile load of `9b_load_depth_raster`, `build_edge_depth`, `load_run` of `flood_history`, and `extract_run` for the metrics.
The owner decided on 2026-10-12 that this is done when a test needs it and not up front ([[decision-log|D-039]]).
Four things are not in the snapshot because they did not exist on 2026-10-12: the raster tiles of these runs, the depth GeoTIFFs, the MinIO vector tiles, and `depth_history`.
The restore script does not load raster tiles.
`flood_segment_metrics` has no rows for these runs.

## Verify the folder

The NetCDF checksums are in `manifest.json`, and the snapshot checksums and row counts are in `snapshot/MANIFEST.json`.
Hash each file and compare it with its entry.
On 2026-10-12, 58 of 58 NetCDF files, 8 of 8 CSV files, and 60 of 60 binary and graph files matched ([[US-124-save-the-storm-replay-results-and-derived-data|US-124]]).

## Run the database suites

The command `python3 scripts/testdata/run_db_tests.py` runs the database suites of the repository against scratch databases on the two servers ([[US-128-run-the-test-suites-against-the-test-databases|US-128]], [[decision-log|D-048]]).
It does not use `minio_custom_test` and `flood_metrics_test`, because about 9 suites create and drop tables in `public`. It only counts the rows of the restored tables there, before and after, and it fails when a count changes.
Run it on the Mac, with the SSH key of the server. `--only FOLDER` runs one folder and `--dry-run` prints the plan.
`test_restore_snapshot.py` stays skipped on the Mac, because it needs the snapshot folder of the worker.

## Retention

The dataset has no retention, and the owner deletes it.
The production retention is unchanged: 24 hours for the NetCDF and depth files, 24 hours of `flood_road_values` until [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] deleted it, the newest 8 runs of tiles and polygons, and the newest 8 edge depth files ([[decision-log|D-033]]).
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

## History and metrics

The script `scripts/testdata/build_history_and_metrics.py` builds `depth_history`, `history_moment`, and `flood_segment_metrics` from the restored road values ([[US-127-build-the-history-and-metrics-from-the-restored-road-values|US-127]]).
Run it in the Airflow worker after the restore:

```
docker exec airflow_new-airflow-worker-1 python /opt/airflow/scripts/testdata/build_history_and_metrics.py
```

- **Result on 2026-10-12.** 219,174 rows in `depth_history`, 65 moments in `history_moment`, and 786,956 rows in `flood_segment_metrics` over 58 runs. A run takes about 2 minutes, and a second run gives the same counts.
- **Moments.** A run's moments come from `edge_depth_run.valid_times`, so no raster tile is needed once the edge depth rows exist. The restore leaves `edge_depth` empty, so build its rows first with `rebuild_tiles.py` and `build_edge_depth.py` (the 50-run check of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] does that for 50 runs).
- **Compression.** The script compresses every chunk of `depth_history` and prints the ratio. On the full storm it is 9.7, from 36 MB to 3,840 kB. A chunk with dead space from many deletes reads higher (12.0 on the first run), so decompress and compress again before a measurement.

