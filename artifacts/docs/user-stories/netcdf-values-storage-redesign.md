---
date_drafted: 2026-10-04
type: user-story
us_ids: ["US-066"]
status: reviewed
subsystem: infra, storage-postgres, timescaledb
sprint: 5
source_ideas: []
related: ["[[netcdf-values-timescale-migration]]", "[[docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[sprint-plan-2]]", "[[timescaledb-and-flood-metrics]]"]
tags: [user-story, infra, storage, timescaledb, postgres]
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
  [[docker-data-vhdx-fills-c-drive-again]] (the other, `flood_extent_polygon`, was already cleaned
  up by hand in that session and does not need a schema change). Scheduled into Sprint 5 of
  [[sprint-plan-2]], the current active sprint, since nothing in this repo depends on it finishing
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
  rule, only direct verification in this session. `TODOS.md` and [[sprint-plan-2]] updated to
  match.
