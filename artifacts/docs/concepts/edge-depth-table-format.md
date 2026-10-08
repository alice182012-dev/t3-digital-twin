---
date: 2026-10-01
type: concept
status: active
tags: [edge-depth-table, graphhopper, file-format, sprint-5]
related: ["[[graph-reimport-procedure]]", "[[edge-depth-table-publish]]", "[[edge-depth-table-airflow-task]]", "[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[sprint-plan-2]]", "[[time-aware-routing-engine]]", "[[graphhopper-backend]]", "[[flood-on-roads]]"]
last_updated: 2026-10-08
---

# Edge depth table format

The edge depth table holds the flood depth of every GraphHopper edge at every forecast step of one run. One file is one run. The Java engine and the Python departure timeline read the same bytes. The requirements are in [[edge-depth-table]], and the story that defines the format is `US-040` ([[edge-depth-table-stories]] Story E2).

The Python reader and writer are `scripts/edge_depth/edge_depth_table.py`, with tests in `scripts/edge_depth/test_edge_depth_table.py`. The test `test_writer_produces_the_documented_bytes` pins the layout on this page to a literal byte string.

## File layout

All integers are unsigned and little-endian unless the table says otherwise.

| Field | Size | Meaning |
| ----- | ---- | ------- |
| `magic` | 4 bytes | The ASCII bytes `EDGD`. |
| `version` | `uint16` | The format version. This page describes version 1. |
| `stepCount` | `uint16` | The number of forecast steps, 1 to 65,535. |
| `edgeCount` | `uint32` | The number of edges, 0 to 4,294,967,295. |
| `hashLength` | `uint16` | The length of `graphHash` in bytes. |
| `runLength` | `uint16` | The length of `runName` in bytes. |
| `graphHash` | `hashLength` bytes | The hash of the graph build, as UTF-8 text. |
| `runName` | `runLength` bytes | The run that produced the table, as UTF-8 text. |
| `stepTimes` | `stepCount` times 8 bytes | Each step's time as seconds since 1970-01-01T00:00:00Z, in an `int64`. The times increase. |
| `depths` | `edgeCount` times `stepCount` times 2 bytes | One `uint16` per edge and step. |

The fixed part of the header is the first 16 bytes. The body starts at `16 + hashLength + runLength + 8 * stepCount`. The file size is the body start plus `2 * edgeCount * stepCount`.

## Depth values

- The unit is centimetres. The largest value is 65,535, which is 655.35 m.
- The value is the deepest 1 m sample along the edge at that step, the same statistic as `flood_on_roads` (D-006).
- An edge with no model coverage reads 0. The file has no coverage flag (decision of 2026-09-29 in [[edge-depth-table]]).
- The table holds no vehicle limit. Each reader applies its own.

## Order of the body

The body is edge-major. The edge id is the row index, so the file stores no id column. The depth of edge `e` at step `s` starts at byte `bodyStart + 2 * (e * stepCount + s)`. GraphHopper numbers its edges from 0 without gaps, so the first row is edge 0. The export story (`US-039`) checks that the edge count of the table equals the graph's edge count.

## What a reader refuses

A reader refuses the file, and names the cause, in these cases.

- The first 4 bytes are not `EDGD`.
- `version` is not one the reader supports.
- The file ends inside the header.
- The file size differs from the size the header's counts give, which covers a truncated body and extra bytes after it.
- `graphHash` or `runName` is not valid UTF-8, or the step times do not increase.

The graph hash guard (refuse a table whose `graphHash` differs from the loaded graph's) is not part of the format. It belongs to each reader's caller. The Python guard is built (`US-044`): `require_graph_hash` and `read_latest_table_for_graph` raise `StaleTableError`, naming both hashes, and log it at ERROR. The Java guard is built (`US-043`): `EdgeDepthTable.requireGraphHash` throws `StaleTableException` with the same wording, and `LatestTableSource` refuses such a table, logs it at ERROR, and keeps the valid current one. What to do after a graph re-import is in [[graph-reimport-procedure]], and `scripts/edge_depth/check_tables.py` shows whether the export, `graph_edge`, the tables, and the live graph agree on one hash.

## The `latest` pointer

A table directory holds the table files and one text file named `latest`. It contains the current table's file name and a newline, for example `20260930T020000.bin`. The name has no path separator and is not `latest`. `read_latest` returns the path of that table, and `write_latest` writes the pointer. Replacing the pointer without a partial read, and keeping the newest 3 tables, belong to `US-042`.

## Measured

The real graph has 67,833 edges and a run has 8 steps, so a real table is about 1.1 MB ([[routing-not-time-aware]], "Baselines on the server"). As a stress test, on 2026-10-01, on a Mac, a table of 2,000,000 edges and 9 steps is 36.0 MB. The Python writer wrote it in 0.7 s, and the reader opened it in 0.01 s. These are not server numbers. `US-045` measures the server build time and is open. The one real `routing_adapter` run read so far built in 60.1 s, and the gap from the end of `3_calculate_depth` to the end of 9c was 8.21 minutes against the 5-minute limit. One run cannot separate that gap from the catch-up of a new DAG (`artifacts/TODOS.md`).

## Build task (US-041)

Task `9c_build_edge_depth_table` of the DAG `routing_adapter` writes `<EDGE_TABLE_DIR>/<run_ts>.bin` after `9b_load_depth_raster` of `flood_mapping_full` emits its asset event. The task runs in `routing_adapter` since commit `77169c3` on the branch `modular`, and `routing_adapter` is unpaused on the server (checked 2026-10-08). `artifacts/TODOS.md` records it running there from 2026-10-07 16:00 +07. The code is `scripts/edge_depth/`. The design and the reasons are in [[edge-depth-table-airflow-task]].

- **Input, the export.** `graph.json` and `edges.csv` from `ExportEdges`, in `EDGE_EXPORT_DIR` (default `data/mapping/graph_export`). Airflow cannot run the export, because it runs in the GraphHopper image, so an operator writes the two files with `java/time-aware-routing/export-edges.sh` and `EXPORT_DEST`. `graph_edges.load_graph_edges` copies them into the PostGIS tables `graph_edge` and `graph_edge_export` when the hash differs from the loaded one, in one transaction.
- **Sampling.** The method and the SQL of `flood_on_roads`, with `graph_edge` in place of `road_segment`: the midpoint of every metre along the edge, matched to its pixel by grid arithmetic, the deepest sample. Metres are rounded to whole centimetres and capped at 65,535. An edge that touches no wet pixel reads 0.
- **Output.** `<run_ts>.bin` in the format above, with the export's graph hash, the run name, and the step times in UTC. It is written under a temporary name and renamed. The `latest` pointer, retention, and the storage choice belong to `US-042`.
- **A failure does not fail the core run.** The task is in `routing_adapter`, and nothing in `flood_mapping_full` waits for it. `hotstart_policy.should_hotstart` lets a run hotstart only when a run of the previous slot is in state `success` or `running`, so a red core run would force cold starts. A failed 9c turns only the `routing_adapter` run red. The no-op leaf `edge_table_done` that did this job inside the core DAG is gone.
- **Slow steps.** `build_edge_depth.py` runs `ANALYZE flood_depth_raster_tile` first and cancels a sampling step after `DEFAULT_STEP_TIMEOUT_S` (120 s) (`US-070`).
- **Report.** The task prints and pushes to XCom (`edge_depth_table`) the edge and step counts, the wet edges per step, the sampling seconds, the file size, and the total seconds.
- **Check.** `scripts/edge_depth/spot_check.py` compares the table with a direct `ST_Value` reading at the same sample points. `scripts/edge_depth/server_check.sh` builds a retained run's table in the Airflow worker on the server and runs the check.

Verified on 2026-10-05 against a throwaway PostGIS in the cloud session (59 tests in `scripts/edge_depth/`), and on the server: for run `20261005T120000` the table has 67,833 edges by 8 steps, 1,085,487 bytes, built in 42.0 s with no other load (about 5 s per step), and a 20-edge spot check matched `ST_Value` for all 160 values. That build ran `build_edge_depth.py` in the Airflow worker, not a DAG run, because the DAG was paused. About 1,000 edges are wet at each step of that run.

## Publish, retention, and storage (US-042)

`scripts/edge_depth/publish_edge_depth.py` publishes a table that `build_edge_depth.py` wrote into the table folder. The design and the reasons are in [[edge-depth-table-publish]].

- **Storage.** The Docker named volume `edge-depth-tables`, mounted at `/opt/airflow/edge_depth_tables` in the Airflow containers. The worker is the only writer, and the routing readers mount it read-only. It is not MinIO (the readers would need an S3 client and credentials) and not a folder under `DATA_HOST_PATH` (on the D: drive, behind Windows file sharing, where replacing an open file can behave differently from Linux).
- **One pointer, many tables.** A reader reads `latest`, then the file it names. Each publish writes a new file name, so a file a reader has opened is never rewritten.
- **The pointer moves in one step.** `write_latest` writes a temporary file in the same folder, flushes it, and renames it over `latest`. A reader sees the old name or the new one, never an empty file. A test reproduced the empty pointer on the old code (a write in place) before the fix.
- **The pointer only moves forward.** Table names are run timestamps and sort in time order. Two runs can overlap, and the older one can finish last. Its table stays on disk until retention removes it, and `latest` is not moved back. A lock on the folder makes the read of the pointer and the write of it one step, so two publishes cannot interleave.
- **Publish checks the file first.** The table is read back whole. A file that does not read, or whose header names another run, is removed, `latest` stays, and the task fails.
- **Retention.** The newest `EDGE_TABLE_KEEP_RUNS` (default 3) files named `YYYYMMDDTHHMMSS.bin` stay, plus the one `latest` names. Temporary files older than one hour are removed. Other files are left alone.
- **A reader reads the pointer again** if the named file has just been removed (`read_latest_table`, one retry).
- **A failure keeps the previous table.** The pointer moves only inside `publish_table`, after the checks. A failed publish turns the `routing_adapter` run red and leaves `flood_mapping_full` green.
- **Check on the server.** `scripts/edge_depth/publish_check.py` runs a reader in its own process while 41 tables of the real size publish into a scratch folder on the same volume. `server_check.sh` runs it.

Verified on 2026-10-05 in the cloud session: 83 tests in `scripts/edge_depth/`, three mutations caught (no lock, a pointer that can move back, and retention that can remove the pointer's table), and `publish_check.py` on a local folder (4,715 polling reads, none failed). On the server (2026-10-05, volume `edge-depth-tables`): `publish_check.py` published 41 tables of 1,085,487 bytes in 2.2 s while a reader in its own process made 11,878 reads, none failed, and it saw all 41 pointer moves. 3 tables were left, and the real `latest` was untouched. The reader ran in the same container as the writer, as a separate process. The real table of run `20261005T120000` is published there.

## Open items

- The file name is `<run_ts>.bin`, as `scripts/edge_depth/build_edge_depth.py` writes it. The format does not require the extension.
- The hash algorithm is fixed by the export (`US-039`, built 2026-10-05). It is a SHA-256, written as 64 lowercase hex characters, over the node count, the edge count, and for each edge in id order its base node, adjacent node, point count, and points in 1e-7 degrees. `ExportEdges` writes it to `graph.json` as `graph_hash`, and the table's `graphHash` header holds the same text. See `java/time-aware-routing/README.md`. Run on the server graph on 2026-10-05: 67,833 edges, 51,328 nodes, hash `8c13d8841f8335a39207a38bb833bfc70d8e7d0709d46953076e4e5142c716ce` for the graph of that day.
- The Java reader (`US-043`) passes the same bytes. `scripts/edge_depth/golden_fixture.py` writes one fixture (3,000 edges, 9 steps, edge-case values) to `java/time-aware-routing/src/test/resources/edge-depth/`, and both readers are tested against it.
