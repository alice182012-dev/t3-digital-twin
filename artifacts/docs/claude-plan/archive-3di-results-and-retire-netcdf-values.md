---
date: 2026-10-08
type: plan
status: active
tags: [plan, archive, netcdf, retention, storage]
related: ["[[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[decision-log]]", "[[move-non-ssd-storage-to-d-drive]]", "[[US-066-netcdf-values-storage-redesign|netcdf-values-storage-redesign]]", "[[3di-simulation-orchestration]]"]
---

# Plan: archive the 3Di results, then retire `netcdf_values`

Planning only. No code, DAG, or compose file changes in this pass. The stories are `US-094` (Sprint 10) and `US-095`
(Sprint 11) in [[EP-15-archive-and-netcdf-retirement|US-094-095-archive-and-netcdf-retirement-stories]]. The decisions are D-016 and D-018 in [[decision-log]].

## Order

1. `US-094`: archive the file and the run record. The order in the DAG matters. The 24-hour cleanup runs inside
   `9_build_flood_tiles` (`cleanup_dirs` at `dags/flood_mapping_dag.py` line 251), so the archive task runs after
   `2_download_results` and `9_build_flood_tiles` waits for it.
2. Prove `US-094` on real rain: the file and the record exist after the cleanup, test-rain runs archive nothing, and
   the daily growth in GB is recorded here.
3. `US-095`: remove `3b`, the scripts, and the tests. Deploy. Then drop `netcdf_values`, then `netcdf_variable_catalog`,
   then `mesh_elements` on the server, only with the user's explicit go. Record the `timescaledb` size and the C: free
   space before and after.

## Build notes for `US-094`

- Archive folder (confirmed by the user on 2026-10-08): `D:\airflow_new_data\archive`, mounted at `/opt/airflow/archive` through
  `ARCHIVE_HOST_PATH`, beside `DATA_HOST_PATH` (`compose.yml` line 61).
- Test-rain check: the same three variables that `scripts/create_simulation.py` lines 130 to 132 read.
- Run record: `sim_id`, rain input, model revision, graph hash, run timestamp. The source of the model revision and the
  graph hash is unverified.

## Build notes for `US-095`

The file list, the drop order, and the tables that must survive are in Story 2 of the epic file. Concept pages and the
architecture doc change when the story is built, not now.

## Estimates

`US-094` is M: one task and one mount, plus a server deploy and a check that needs real rain. `US-095` is M: about ten
files across one DAG, two tests, and a script, plus a server drop with a go and two readings.

## Open questions

See the epic file: archive folder, the two `storage-postgres` tables, the `timescaledb` container, and the proof on real rain.

## Status history

- **2026-10-08, active.** Written with the stories. `US-094` is in Sprint 10 by dependency, and the user can override it.
