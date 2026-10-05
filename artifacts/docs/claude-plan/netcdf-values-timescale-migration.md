---
date: 2026-10-04
type: plan
branch: front-end-according-to-mock-up
status: complete
tags: [plan, infra, storage, postgres, timescaledb]
related: ["[[docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[netcdf-values-storage-redesign]]", "[[minio-flood-extent-pipeline]]", "[[2026-10-05-us-066-criterion-4-spot-check]]"]
---

# Plan: narrow and compress netcdf_values onto TimescaleDB

## Context

[[docker-data-vhdx-fills-c-drive-again]] traced C: filling to ~250 MB free back to two tables in
`storage-postgres` with no retention policy at all: `flood_extent_polygon` and `netcdf_values`.
[[2026-10-04-docker-vhdx-disk-full]] records the same-day emergency cleanup: a one-off
`DELETE ... WHERE valid_time_utc < now() - interval '48 hours'` plus `VACUUM FULL` took
`flood_extent_polygon` from 13 GB to 5 GB (it was almost entirely dead TOAST bloat behind 1,463
live rows), fixing that table by hand. `netcdf_values` is a different shape of problem: after the
equivalent 48-hour-cutoff delete, it still held about 143 million live rows at 56 GB, because the
48-hour soak test's own data is what the delete was told to keep. There is no quick deletion fix
here — the table needs a different schema before it can hold a multi-day soak without this
recurring.

`netcdf_values` is written by `scripts/database/netcdf_to_pg.py`'s `insert_values`, created by
`scripts/database/create_netcdf_tables.py`. It stores one row per `(file, element, variable,
timestep)`, and every DAG cycle (`task_upload_netcdf_postgres` in `dags/flood_mapping_dag.py`,
task `3b_upload_netcdf_postgres`) uploads the whole mesh again — not just new timesteps. Across a
48-hour soak at the DAG's `*/15 * * * *` schedule, that is around 192 full-mesh uploads.

## Why this table is wasteful today

Every row carries `element_id`, `x`, `y`, `mesh_type`, `element_type`, and `variable_name` — but
for one simulation model, an element's `x`/`y`/`mesh_type`/`element_type` never changes between
runs, and `VARIABLE_MAPPING` in `netcdf_to_pg.py` lists only 8 distinct variables, total, ever.
Only `timestamp` and `value` actually vary run to run. Five indexes
(`idx_netcdf_values_file`, `_sim_time`, `_model_time`, `_var`, `_element`) then repeat that same
redundant data again on top of the heap.

## Design

Two dimension tables, each built once and reused:

```sql
-- element_id restarts at 1 per (mesh_type, element_type), so the same number is a
-- different 2D line and 2D node within one model. The key carries both, corrected
-- after implementation showed (model_id, element_id) alone silently drops rows
-- (see Status history).
CREATE TABLE mesh_elements (
    model_id BIGINT NOT NULL,
    mesh_type TEXT NOT NULL,
    element_type TEXT NOT NULL,
    element_id BIGINT NOT NULL,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    PRIMARY KEY (model_id, mesh_type, element_type, element_id)
);

-- 8 rows, seeded from VARIABLE_MAPPING, never grows. Carries mesh_type and
-- element_type so a value's element kind, and so its geometry, is derivable by
-- joining on variable_id alone.
CREATE TABLE netcdf_variable_catalog (
    id SMALLINT PRIMARY KEY,
    variable_name TEXT UNIQUE NOT NULL,
    mesh_type TEXT NOT NULL,
    element_type TEXT NOT NULL
);
```

And a narrow fact table, as a TimescaleDB hypertable on the `timescaledb` service (which today
holds `institution_histogram_bar`, `background_forecast_depth`, and `depth_history`; this is the
first large table to actually need compression):

```sql
CREATE TABLE netcdf_values (
    file_id INT NOT NULL,
    element_id BIGINT NOT NULL,
    variable_id SMALLINT NOT NULL REFERENCES netcdf_variable_catalog(id),
    "timestamp" TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

SELECT create_hypertable('netcdf_values', by_range('timestamp', INTERVAL '1 day'), if_not_exists => TRUE);

ALTER TABLE netcdf_values SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'file_id, variable_id',
  timescaledb.compress_orderby = 'element_id'
);
SELECT add_compression_policy('netcdf_values', INTERVAL '6 hours', if_not_exists => TRUE);
SELECT add_retention_policy('netcdf_values', INTERVAL '48 hours', if_not_exists => TRUE);
```

Segmenting by `(file_id, variable_id)` fits this data: within one segment, `element_id` runs
through the same sequence every single time (same mesh), so Timescale's columnar compression
should collapse that well past the roughly 2x gained from just dropping the five redundant
columns. `add_retention_policy` replaces this session's hand-run `DELETE ...` with a standing
policy, the same keep-a-window pattern `flood_depth_raster_tile` and the MinIO bucket already use
for their own retention, just expressed through Timescale's native mechanism instead of a bespoke
prune function.

`netcdf_to_pg.py`'s `insert_values` changes to: upsert `mesh_elements` once per `(model_id,
element_id)` not already present (`ON CONFLICT DO NOTHING` — the mesh doesn't change), look up
`variable_id` from `netcdf_variable_catalog`, and insert only `(file_id, element_id, variable_id,
timestamp, value)`. Check whether `delete_old_values(file_id)` is still needed once the retention
policy exists — it exists today for the case of a file reprocessed after a partial failure, which
the retention policy doesn't cover, so it likely stays, just scoped to the new narrow table.

## Migration steps

This is a live table with 56 GB of data the user wants kept for analysis of the soak that just
ran, so the old table stays until the new path is proven, not until the new path is merged.

1. Create `mesh_elements`, `netcdf_variable_catalog`, and the new `netcdf_values` hypertable on
   `timescaledb`.
2. Backfill `mesh_elements` and `netcdf_variable_catalog` from the current `netcdf_values` content
   on `storage-postgres` (a `SELECT DISTINCT` over the small dimension columns, not the full
   table).
3. Backfill the new hypertable from the current `netcdf_values`. This is itself a large copy —
   given this session's history, check free disk headroom before starting, and batch it (by
   `file_id` or by time range) rather than one `INSERT ... SELECT` over 143 million rows, so a
   failure partway through doesn't need a full restart and doesn't risk repeating today's
   out-of-space crash.
4. Verify: row counts match between old and new, and a hand spot-check of a handful of
   `(element_id, variable_name, timestamp)` triples returns the same `value` in both.
5. Cut `netcdf_to_pg.py` over to the new path. Confirm one real `flood_mapping_full` cycle
   (`task_upload_netcdf_postgres`) writes through it cleanly once the DAG is unpaused.
6. Only after step 5 is confirmed on a real run: drop the old `netcdf_values` table on
   `storage-postgres` and reclaim that space (the same `VACUUM FULL` consideration as
   [[docker-data-vhdx-fills-c-drive-again]] Approach 4, since dropping a table is immediate but
   the freed space still needs a vhdx compaction to show up on the Windows host).

## Rollback

Steps 1 through 5 touch nothing on the old table, so a failure at any point before step 6 is a
no-op for the live pipeline: revert `netcdf_to_pg.py` and the old table and its data are still
exactly as they were. Step 6 (dropping the old table) is the only irreversible step, and it is
gated on step 5's real-run verification specifically so that it is not taken on faith.

## Status history

- **2026-10-04, active.** Drafted from this session's design discussion, directly following the
  disk-full incident on [[docker-data-vhdx-fills-c-drive-again]]. Not yet implemented.
- **2026-10-05, active.** Implemented and verified on branch `us-066-netcdf-values-timescale`
  (merged into `front-end-according-to-mock-up`), three commits: the schema and catalog, the
  `netcdf_to_pg.py` write path, and a resumable `backfill_netcdf_values.py`. Two corrections to
  this doc came out of implementing it, not just reviewing it: the `mesh_elements` primary key
  above was `(model_id, element_id)`, which element_id's own numbering makes wrong, confirmed by
  building the table and finding only 42,501 of 63,339 elements survived; and this project's
  TimescaleDB version has no `create_hypertable` overload taking `chunk_time_interval` directly,
  so the interval moved into `by_range`. Both are already corrected above. Verified against a real
  2.64-million-row slice (`file_id` 241 via the backfill script, `file_id` 242 via the new
  `insert_values` against a real `.nc` result): checksums over every value row and every mesh
  element match the old table exactly, and the compressed chunk measured 10.7x smaller than
  uncompressed (283 MB to 26 MB) with the same checksum before and after compression. The old
  `netcdf_values` on `storage-postgres` was 142,548,685 rows / 56 GB before this work and is the
  same after.
  - **Decided: skip the full historical backfill.** The retention policy keeps 48 hours; the
    oldest row in the old table is already 49 hours old at the database's clock, and the chunk
    holding the newest backfilled slice becomes eligible for the daily retention job within about
    a day of being written. Backfilling the remaining ~110 `file_id`s into a table that will drop
    most of them almost immediately gains nothing. The old table already holds the full soak
    history for analysis and stays untouched, so this migration cuts over the write path for new
    data only; `backfill_netcdf_values.py` stays available if a future need justifies running it.
  - **Decided and wired in: `create_timescale_tables.py` now has a caller.** Added `import
    database.create_timescale_tables` and a `database.create_timescale_tables.main()` call to
    `task_ensure_schema` in `dags/flood_mapping_dag.py`, matching the existing pattern for the
    other five DDL scripts. `3b_upload_netcdf_postgres` no longer depends on a hand-run script.
- **2026-10-05, active.** Step 5 verified on a real production cycle, closing the gap the slice
  test in the previous entry couldn't reach: that test ran the new `insert_values` directly, not
  through the actual DAG task. Unpaused `flood_mapping_full` under `FLOOD_TEST_RAIN_MM_HR=50`
  (recreating `airflow-scheduler`, `airflow-dag-processor`, `airflow-worker`, and
  `airflow-apiserver` so they picked up the env change), and waited for the
  `scheduled__2026-10-04T19:00:00+00:00` run. `3b_upload_netcdf_postgres` succeeded through the
  real task, against a real 3Di simulation (id 449585). Verified directly in `netcdf_values` on
  `timescaledb`: a new `file_id` 245 holds 1,302,146 rows across all 6 variables this result has
  (no 1D mesh, same as `file_id` 242 in the slice test), timestamps 19:00:00 to 21:00:00 UTC,
  matching the simulation's 2-hour window. `mesh_elements` is still exactly 63,339 rows after this
  second real write, confirming `ON CONFLICT DO NOTHING` deduplicates correctly rather than
  drifting or duplicating. Afterward, `FLOOD_TEST_RAIN_MM_HR` was cleared back to real Tomorrow.io
  weather and `flood_mapping_full` was re-paused, both by the same recreate step, at the user's
  request. The only step left is step 6: dropping the old `netcdf_values` on `storage-postgres`.
  Nothing further gates it now that step 5 is proven, but it hasn't run, so the old 56 GB table is
  still there and is still the only place the soak's full history lives.
- **2026-10-05, done.** Step 6 ran: a spot-check found only 2 of 112 old `file_id`s were ever
  backfilled into the new hypertable (both matching row for row), and the other 110 are
  pre-migration soak data nothing in the codebase reads — so the soak's full history was never
  actually unique to the old table once its retention window passed. On the user's go,
  `DROP TABLE netcdf_values;` ran clean on `storage-postgres`: `minio_custom` 70 GB to 14 GB. Full
  finding in [[2026-10-05-us-066-criterion-4-spot-check]]. This plan is complete; the story
  [[netcdf-values-storage-redesign]] (`US-066`) is `Done`.
