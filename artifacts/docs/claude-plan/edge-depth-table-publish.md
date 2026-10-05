---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-7, edge-depth-table, us-042, atomic-publish, retention, storage]
related: ["[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-format]]", "[[edge-depth-table-airflow-task]]", "[[sprint-plan-2]]", "[[graphhopper-backend]]"]
---

# Plan: publish the edge depth table atomically and keep the newest three (US-042)

## Context

`US-041` writes `<run_ts>.bin` and stops. This story makes a table visible to readers in one step, keeps the newest three, and picks where the tables live.

Acceptance, from [[edge-depth-table-stories]] Story E4. Given a reader that polls in a loop, when the task publishes a table, then the reader sees the old table or the new one and never a partial file. Given four runs, when the fourth publishes, then the oldest is removed. A failed task leaves the previous `latest` in place and does not block the DAG. The story also picks the storage, a volume or MinIO, and records why.

## What is already there

1. `write_latest` and `read_latest` in `scripts/edge_depth/edge_depth_table.py` (`US-040`). `write_latest` is not atomic. It opens `latest` for writing, which empties it, and then writes. A reader that polls at the wrong moment reads an empty pointer. This is the first thing to fix.
2. `build_table` writes the table file under a temporary name and renames it, so the `.bin` itself is never partial. Each run has its own file name, so a new table never replaces an old file.
3. The DAG task `9c_build_edge_depth_table`, followed by the no-op `all_done` leaf, so a failed task does not fail the run.

## Decisions

1. **Storage: a named Docker volume, `edge-depth-tables`.** Not MinIO, and not a folder under the host data mount.
   - MinIO would put an S3 client and its credentials into the Java reader (`US-043`) and the Python timeline. That is a second way to fail in the routing path, for three files of about 1 MB.
   - A folder under `DATA_HOST_PATH` sits on the D: drive and reaches the containers through Windows file sharing. Replacing the `latest` file while a reader in another container has it open is the case where Windows file semantics can differ from Linux. A named volume lives on the Docker VM's own Linux disk, with Linux rename semantics, the same as `graphhopper-graph-cache`.
   - Both readers will mount the volume read-only. The Airflow worker is the only writer. The size is tiny, so the C: drive budget is not a concern.
2. **One pointer, many tables.** `latest` holds a file name. A reader reads the pointer, then the file. Each publish writes a new file name, so the file a reader opened is never rewritten.
3. **The pointer only moves forward.** Two runs can overlap (`max_active_runs=2`), and the older one can finish last. Table names are run timestamps, and they sort in time order. A publish of a name that sorts below the current pointer leaves the pointer where it is.
4. **Publish checks the file first.** The table is read back whole (`read_table`) before the pointer moves. A file that does not read, for example a truncated one, is deleted, the pointer stays, and the task fails.
5. **Retention counts valid names.** After the pointer moves, only the newest `EDGE_TABLE_KEEP_RUNS` (default 3) files named `YYYYMMDDTHHMMSS.bin` stay. The file the pointer names is never removed. Temporary files older than one hour (left by a killed build) are removed.
6. **A failure keeps the previous pointer.** The build or the publish raises before the pointer is replaced, so `latest` still names the previous table. The no-op leaf keeps the DAG run green.

## Steps

Tests first at every step.

1. Make `write_latest` atomic: write a temporary file in the same folder, flush, replace. A test has a reader thread poll the pointer while the writer alternates names many times. It must never see an empty or partial pointer. I check that the test fails on the current code first.
2. `scripts/edge_depth/publish_edge_depth.py`: `publish_table(table_dir, table_name, keep)` with the checks of decisions 3 to 5. Tests: first publish, newer moves, older does not, four runs keep three, the pointer's file survives, a truncated file is refused and removed, stale temporary files are removed, `keep < 1` is an error, a bad name is an error.
3. A reader test that polls pointer and table in a loop in another process while the test publishes 30 times, and requires every read to be a complete table.
4. The DAG: task `9c` calls `publish_table` after `build_table`, with `EDGE_TABLE_KEEP_RUNS`, and adds the result to the report. The default `EDGE_TABLE_DIR` becomes `/opt/airflow/edge_depth_tables`.
5. `compose.yml`: the volume `edge-depth-tables`, mounted into the Airflow containers at that path, and `airflow-init` makes it writable for the Airflow user.
6. `scripts/edge_depth/publish_check.py` for the server: the polling reader in a separate process and the retention check, in a scratch folder on the same volume so the real `latest` is untouched. `server_check.sh` runs it.
7. Docs: [[edge-depth-table-format]], the sprint plan, `TODOS.md`.

## Not in this story

- The Java and Python readers, and their reload without restart (`US-043`).
- The stale-table check against the graph hash and the re-import page (`US-044`).

## Risks

- **The volume needs `airflow-init` to run once** so the Airflow user can write to it, and the worker needs a recreate to mount it. Both are server steps for the user.
- **The old build output** in `data/mapping/edge_depth` stays where it is and is not read. It can be deleted.

## Status history

- **2026-10-05, active.** Plan written at the start of `US-042`. Decisions 1 to 6 fixed. The storage choice is mine to record, and the user can overrule it.
