---
date_drafted: 2026-10-04
type: user-story
us_id: "US-066"
us_ids: ["US-066"]
status: Done
subsystem: infra, storage-postgres, timescaledb
sprint: 5
source_ideas: []
related: ["[[netcdf-values-timescale-migration]]", "[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]", "[[EP-04-timescaledb-and-flood-metrics|timescaledb-and-flood-metrics]]", "[[2026-10-05-us-066-criterion-4-spot-check]]"]
tags: [user-story, infra, storage, timescaledb, postgres]
priority: P1
estimate: L
title: "Narrow and compress netcdf_values onto TimescaleDB"
---

# Narrow and compress netcdf_values onto TimescaleDB

## User story (US-066)

As an engineer operating this project's Docker host, I want `netcdf_values` redesigned into a
narrow, compressed, retention-managed hypertable, so the mesh-simulation ingest pipeline stops
refilling C: every time a long soak test runs.

## Priority

P1

## Estimate

L

## Acceptance criteria

Given the current `netcdf_values` table (56 GB, about 143 million rows, no retention policy),
when the migration in [[netcdf-values-timescale-migration]] lands and `netcdf_to_pg.py` writes
through the new path, then:

1. `mesh_elements` and `netcdf_variable_catalog` hold the deduplicated dimension data (mesh
   geometry and the variable list), upserted idempotently rather than repeated on every row.
2. The new hypertable on the `timescaledb` service has a compression policy and a 48-hour
   retention policy (`add_compression_policy`, `add_retention_policy`), so no manual prune step is
   needed going forward.
3. A real `flood_mapping_full` run, once unpaused, writes successfully through the new path with
   no code reverted.
4. The old `netcdf_values` table on `storage-postgres` is dropped only after a row-count and
   value spot-check against the new tables passes.

## Status history

- **2026-10-04, draft.** Written up after this session's C: drive incident: `netcdf_values` had
  no retention policy at all and reached 56 GB / about 143 million rows during the 48-hour soak
  test (`US-034`), one of the two confirmed root causes on
  [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]] (the other, `flood_extent_polygon`, was already cleaned
  up by hand in that session and does not need a schema change). Scheduled into Sprint 5 of
  [[SP-02-routing-engine-foundations|sprint-plan-2]], the current active sprint, since nothing in this repo depends on it finishing
  first and `US-034`'s own soak already lives in that sprint.
- **2026-10-05, reviewed.** Implemented on branch `us-066-netcdf-values-timescale`, merged into
  `front-end-according-to-mock-up`. All three criteria that don't require dropping the old table
  are met with real evidence, not just a passing test:
  1. `mesh_elements` holds exactly 63,339 rows (42,501 2D lines, 20,838 2D nodes) after both the
     slice-level backfill and a second real production write, with zero duplication; the key is
     `(model_id, mesh_type, element_type, element_id)`, corrected from this doc's original
     `(model_id, element_id)` during implementation (see [[netcdf-values-timescale-migration]]).
  2. The hypertable has both policies active (`policy_compression` after 6h, `policy_retention`
     dropping after 48h), confirmed by querying `timescaledb_information.jobs` directly.
  3. A real `flood_mapping_full` run (`scheduled__2026-10-04T19:00:00+00:00`, under a forced
     50 mm/h test rain, simulation id 449585) wrote `file_id` 245 through the new
     `3b_upload_netcdf_postgres` successfully: 1,302,146 rows across all 6 real variables, no code
     reverted.
  4. Not exercised. The old `netcdf_values` on `storage-postgres` stays untouched (still 56 GB)
     until a later pass drops it; nothing in this criterion requires that to happen yet.
  Not marked `done`: no rendered-output screenshot evidence captured per this vault's evidence
  rule, only direct verification in this session. `TODOS.md` and [[SP-02-routing-engine-foundations|sprint-plan-2]] updated to
  match.
- **2026-10-05, done.** Re-ran criteria 1 to 3 live against the real containers and they still
  hold, unchanged: `mesh_elements` still has exactly 63,339 rows (42,501 lines, 20,838 nodes, 0
  duplicates on the key), `policy_compression` and `policy_retention` are both active with
  `last_run_status = Success`, and `file_id` 245 still has 1,302,146 rows across all 6 variables.
  Rendered as `us-066-netcdf-timescale-verify.png`, captured on host ADMIN / 100.67.84.55 at
  2026-10-05 03:42 UTC. `TODOS.md` and [[SP-02-routing-engine-foundations|sprint-plan-2]] updated to match.

  Criterion 4 exercised: the old `netcdf_values` on `storage-postgres` still holds 142,548,685 rows
  (56 GB) across `file_id` 131 to 242 (2026-10-02 17:15 to 2026-10-03 21:00), all from the soak
  test that caused [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]], predating `file_id` 245, the first
  write through the new path. `scripts/database/backfill_netcdf_values.py` had only ever been run
  on the two most recent file_ids, 241 and 242; both match the old table row for row (1,320,167 and
  1,320,179), with zero loss. The other 110 file_ids were never backfilled. Of their 139,908,339
  rows, 84,471,989 (`file_id` 173 to 240) still fall inside the new hypertable's 48-hour retention
  window as of this check; the remaining 55,436,350 (`file_id` 131 to 172) are already older than
  that window and would be dropped by `policy_retention` even if copied now. No code outside the
  ingestion and backfill scripts reads `netcdf_values` on either table, so no live query depends on
  any of this data. Full finding in [[2026-10-05-us-066-criterion-4-spot-check]].

  The literal criterion text ("dropped only after a row-count and value spot-check against the new
  tables passes") has passed for the 2 file_ids actually copied and spot-checked, not for the other
  110. Recommendation: drop, since the un-copied rows are pre-migration soak exhaust that nothing
  reads and that the retention policy would discard anyway as it ages past 48 hours; the decision
  not to backfill the rest is a choice to let that soak data lapse, not a parity failure.
- **2026-10-05, done.** `DROP TABLE netcdf_values;` run on `storage-postgres`, on the user's go.
  Confirmed before: 56 GB, 142,548,685 rows. Confirmed after: `to_regclass('netcdf_values')`
  returns null, `minio_custom`'s database size dropped from 70 GB to 14 GB, and the
  `airflow_new_storage-postgres-data` Docker volume dropped from 76.61 GB to 16.01 GB.
  `storage-postgres` stayed healthy throughout, no restart needed. Criterion 4 is now fully
  exercised. This frees space inside the Docker volume, not yet on the Windows host: `C:` still
  needs a `wsl --shutdown` + `diskpart compact vdisk` pass to convert it into Windows-visible free
  space, the same open step [[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]] already tracks.

## Evidence and details

**Evidence:** None

**Details:**

![[us-066-netcdf-timescale-verify.png|120]]
