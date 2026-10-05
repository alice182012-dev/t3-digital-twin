---
date: 2026-10-01
type: concept
status: active
tags: [edge-depth-table, graphhopper, file-format, sprint-5]
related: ["[[edge-depth-table-airflow-task]]", "[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[sprint-plan-2]]", "[[time-aware-routing-engine]]", "[[graphhopper-backend]]", "[[flood-on-roads]]"]
last_updated: 2026-10-05
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

The graph hash guard (refuse a table whose `graphHash` differs from the loaded graph's) is not part of the format. It belongs to each reader's caller, and `US-043` and `US-044` build it.

## The `latest` pointer

A table directory holds the table files and one text file named `latest`. It contains the current table's file name and a newline, for example `20260930T020000.bin`. The name has no path separator and is not `latest`. `read_latest` returns the path of that table, and `write_latest` writes the pointer. Replacing the pointer without a partial read, and keeping the newest 3 tables, belong to `US-042`.

## Measured

The real graph has 67,833 edges and a run has 8 steps, so a real table is about 1.1 MB ([[routing-not-time-aware]], "Baselines on the server"). As a stress test, on 2026-10-01, on a Mac, a table of 2,000,000 edges and 9 steps is 36.0 MB. The Python writer wrote it in 0.7 s, and the reader opened it in 0.01 s. These are not server numbers. The server build time is measured by `US-045`.

## Build task (US-041)

Task `9c_build_edge_depth_table` of `flood_mapping_full` writes `<EDGE_TABLE_DIR>/<run_ts>.bin` after `9b_load_depth_raster`. The code is `scripts/edge_depth/`. The design and the reasons are in [[edge-depth-table-airflow-task]].

- **Input, the export.** `graph.json` and `edges.csv` from `ExportEdges`, in `EDGE_EXPORT_DIR` (default `data/mapping/graph_export`). Airflow cannot run the export, because it runs in the GraphHopper image, so an operator writes the two files with `java/time-aware-routing/export-edges.sh` and `EXPORT_DEST`. `graph_edges.load_graph_edges` copies them into the PostGIS tables `graph_edge` and `graph_edge_export` when the hash differs from the loaded one, in one transaction.
- **Sampling.** The method and the SQL of `flood_on_roads`, with `graph_edge` in place of `road_segment`: the midpoint of every metre along the edge, matched to its pixel by grid arithmetic, the deepest sample. Metres are rounded to whole centimetres and capped at 65,535. An edge that touches no wet pixel reads 0.
- **Output.** `<run_ts>.bin` in the format above, with the export's graph hash, the run name, and the step times in UTC. It is written under a temporary name and renamed. The `latest` pointer, retention, and the storage choice belong to `US-042`.
- **A failure does not fail the run.** `edge_table_done` is a no-op leaf with `trigger_rule="all_done"`. `hotstart_policy` lets a run hotstart only when the previous slot's run succeeded, so a red DAG run would force cold starts.
- **Report.** The task prints and pushes to XCom (`edge_depth_table`) the edge and step counts, the wet edges per step, the sampling seconds, the file size, and the total seconds.
- **Check.** `scripts/edge_depth/spot_check.py` compares the table with a direct `ST_Value` reading at the same sample points. `scripts/edge_depth/server_check.sh` builds a retained run's table in the Airflow worker on the server and runs the check.

Verified on 2026-10-05 against a throwaway PostGIS in the cloud session (59 tests in `scripts/edge_depth/`), and on the server: for run `20261005T120000` the table has 67,833 edges by 8 steps, 1,085,487 bytes, built in 42.0 s with no other load (about 5 s per step), and a 20-edge spot check matched `ST_Value` for all 160 values. That build ran `build_edge_depth.py` in the Airflow worker, not a DAG run, because the DAG was paused. About 1,000 edges are wet at each step of that run.

## Open items

- The file extension is not fixed. The Airflow task story (`US-041`) decides the file name.
- The hash algorithm is fixed by the export (`US-039`, built 2026-10-05). It is a SHA-256, written as 64 lowercase hex characters, over the node count, the edge count, and for each edge in id order its base node, adjacent node, point count, and points in 1e-7 degrees. `ExportEdges` writes it to `graph.json` as `graph_hash`, and the table's `graphHash` header holds the same text. See `java/time-aware-routing/README.md`. Run on the server graph on 2026-10-05: 67,833 edges, 51,328 nodes, hash `8c13d8841f8335a39207a38bb833bfc70d8e7d0709d46953076e4e5142c716ce` for the graph of that day.
- The Java reader (`US-043`) must pass the same bytes. The literal-bytes test is the fixture it starts from.
