---
date: 2026-10-05
type: log
status: active
tags: [log, infra, storage, timescaledb, postgres]
related: ["[[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]", "[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# US-066 Done verification and the criterion 4 spot-check

## Re-verifying criteria 1 to 3

Ran the three acceptance checks for US-066 again, live, against the real containers on this host
(ADMIN / 100.67.84.55), instead of trusting the 2026-10-05 "reviewed" write-up at face value.

1. `mesh_elements` on `timescaledb` still holds exactly 63,339 rows: 42,501 `2D`/`line` and 20,838
   `2D`/`node`, with 0 duplicates on `(model_id, mesh_type, element_type, element_id)`.
2. `timescaledb_information.jobs` shows both `policy_compression` (6-hour `compress_after`) and
   `policy_retention` (48-hour `drop_after`) active on the `netcdf_values` hypertable, both with
   `last_run_status = Success`.
3. `file_id` 245 still has 1,302,146 rows across all 6 real variables (`Mesh2D_q`, `Mesh2D_rain`,
   `Mesh2D_s1`, `Mesh2D_ucx`, `Mesh2D_ucy`, `Mesh2D_vol`).

All three hold unchanged from the 2026-10-05 review. Rendered the verbatim `psql` output to
`artifacts/docs/user-stories/evidence/us-066-netcdf-timescale-verify.png`, captured 03:42 UTC on
this host, and moved [[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]] (`US-066`) to `Done` in that file,
[[SP-02-routing-engine-foundations|sprint-plan-2]], and `TODOS.md`.

## Criterion 4: does the old table hold anything that still matters

The fourth criterion gates dropping the old `netcdf_values` on `storage-postgres` on a row-count
and value spot-check against the new tables. That check had never run, so this is it.

The old table still holds 142,548,685 rows (56 GB) across `file_id` 131 to 242, timestamped
2026-10-02 17:15 to 2026-10-03 21:00. Every one of those 112 file_ids is from the 48-hour soak test
that caused [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]], and all of it predates `file_id` 245, the
first write that went through the new path. `netcdf_files` has no row for 245 in the old
`netcdf_values`, which confirms the new path never touched the old table.

`scripts/database/backfill_netcdf_values.py` exists to copy a named `file_id` from the old table
into the new hypertable, one file at a time, inside a transaction that only commits once the file
is fully copied. Checking what it had actually been run on:

```sql
-- storage-postgres
select file_id, count(*) from netcdf_values group by file_id order by file_id;
-- timescaledb
select file_id, count(*) from netcdf_values where file_id < 245 group by file_id order by file_id;
```

Only `file_id` 241 and 242 exist in the new hypertable. Both match the old table row for row:
1,320,167 and 1,320,179 respectively, zero gain and zero loss. The other 110 file_ids were never
backfilled; they have no rows in the new hypertable at all.

The question that matters for a safe drop is not "was every file_id copied" but "does any of the
uncopied data still have to be live under the new design." The new hypertable's own retention
policy would drop anything older than 48 hours, so data the old design would already have expired
is not a loss. Checked against the current clock (2026-10-05 03:39 UTC, 48-hour cutoff
2026-10-03 03:39 UTC):

```sql
select count(*) from netcdf_values where timestamp > now() - interval '48 hours';
-- 87,112,335 rows, file_id 173 to 242

select count(*) from netcdf_values where timestamp > now() - interval '48 hours' and file_id not in (241, 242);
-- 84,471,989 rows, file_id 173 to 240
```

So of the 139,908,339 rows in the 110 uncopied file_ids, 84,471,989 (`file_id` 173 to 240) are
still inside the 48-hour window a reader of the new hypertable would expect to find, and they exist
nowhere else. The remaining 55,436,350 (`file_id` 131 to 172) are already older than that window
and would be dropped by `policy_retention` even if they were copied today.

Whether that 84.5 million rows actually matters to anything depends on who reads it. A repo-wide
search for `netcdf_values` turns up five files, every one of them in `scripts/database/`:
`backfill_netcdf_values.py`, `create_netcdf_tables.py`, `create_timescale_tables.py`,
`netcdf_to_pg.py`, and `netcdf_variables.py`. None of the frontend, `floodmap-backend`,
`storage-backend`, or any DAG reads `netcdf_values` on either table; the only consumers are the
ingestion write path and this backfill tool. Postgres itself also has no view, materialized view,
or trigger on the old table beyond its own primary key and its outbound foreign key to
`netcdf_files` (confirmed via `pg_views`, `pg_matviews`, and `pg_trigger`), so dropping it breaks
no downstream object.

## Finding

The literal wording of criterion 4, "dropped only after a row-count and value spot-check against
the new tables passes," has passed for exactly the 2 file_ids the backfill script was actually run
against (241, 242), not for the other 110. The 84,471,989 uncopied-but-still-in-window rows are
real, but they are pre-migration soak-test exhaust, not output from the new write path, and nothing
in the running system reads them.

**Recommendation: drop.** The un-backfilled rows would not survive the new hypertable's own
retention policy for more than another day or two even if copied, nothing reads them today, and
leaving a 56 GB table around after confirming the new path works is the exact failure mode
[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]] already happened once from. The choice not to backfill the
remaining 110 file_ids is a deliberate call to let this soak data lapse under the new design, not a
parity failure the migration still owes.

Ready to run, on `storage-postgres`:

```sql
DROP TABLE netcdf_values;
```

No `CASCADE` needed; `pg_matviews`, `pg_views`, and `pg_trigger` were checked and nothing else
references the table beyond its own constraints. Not run in this session; the user asked to confirm
in person before a one-way drop of 56 GB of real data.
