---
date_drafted: 2026-10-05
type: user-story
us_id: "US-067"
us_ids: ["US-067"]
status: Done
subsystem: minio-flood-extent-pipeline, storage-postgres
sprint: 5
source_ideas: []
related: ["[[minio-flood-extent-pipeline]]", "[[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]", "[[2026-10-04-docker-vhdx-disk-full]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
tags: [user-story, infra, postgres, retention]
priority: P1
estimate: S
title: "Prune old runs' flood_extent_polygon rows on every publish"
---

# Prune old runs' flood_extent_polygon rows on every publish

## User story (US-067)

As the operator of this project's Docker host, I want `publish_run` to delete `flood_extent_polygon` rows for runs outside the newest `keep_runs`, so the table cannot grow unbounded the way it did before the 2026-10-04 disk-full incident.

## Priority

P1. The table has no automated retention today, and the 2026-10-04 incident ([[BL-022-docker-data-vhdx-fills-c-drive-again|docker-data-vhdx-fills-c-drive-again]]) showed what that costs: 13 GB of mostly dead TOAST bloat behind 1,463 to 2,121 live rows, fixed once by hand, with nothing in the code to stop it from happening again once `flood_mapping_full` unpauses.

## Estimate

S. One function, directly analogous to the existing `prune_step_rows`, called from the same place in `publish_run`.

## Acceptance criteria

Given a run has just published every one of its timesteps, when `publish_run` finishes, then it deletes `flood_extent_polygon` rows for every `run_ts` outside the newest `keep_runs`, except the run it is currently publishing (`always_keep`), the same contract `prune_step_rows` already gives `flood_extent_step`.

Given `db_conn` is `None`, when `publish_run` runs, then `prune_polygon_rows` does nothing and raises nothing, matching `prune_step_rows`'s own no-op.

Given the table is healthy and `flood_mapping_full` is still paused, when this story ships, then no one-off `DELETE` or `VACUUM` runs against the live `flood_extent_polygon` table. The fix is the missing automated policy, not another manual cleanup.

## Evidence

![[us-067-prune-polygon-rows-check-output.png|700]]

## Details

1. What: `scripts/flood_extent/publish.py` gets a `prune_polygon_rows(db_conn, keep_runs, always_keep)` function, called from `publish_run` right after `prune_step_rows`. It deletes `flood_extent_polygon` rows whose `run_ts` is outside the newest `keep_runs` distinct `run_ts` values in that table, except `always_keep`. `scripts/database/create_flood_extent_tables.py` had one comment that assumed `flood_extent_polygon` was never pruned; that comment is now corrected.
2. How: tests first, mirroring `test_publish.py`'s existing `prune_step_rows` test style. 21 tests pass against a throwaway `postgis/postgis:15-3.4` container (not the live `storage-postgres`), including a direct test that `always_keep` survives even when it falls outside the `keep_runs` window, a case `publish_run` itself never produces but the function's contract still promises.
3. Why: `publish_run` already prunes the MinIO bucket and `flood_extent_step` after every successful run. `flood_extent_polygon` had no equivalent, which is exactly the gap the 2026-10-04 incident found. Keying the delete on `run_ts` alone, not on the table's `(run_ts, valid_time_utc, dn_code)` primary key, matches `prune_step_rows`'s own granularity: a run's polygon rows all share one `run_ts`, so "the newest `keep_runs` runs" names the same runs in both tables.
4. Effect: once `flood_mapping_full` unpauses, every publish deletes roughly one old run's worth of polygon rows (about 183 rows at the table's current 1,463 live rows over 8 kept runs) instead of letting years of runs accumulate. Checked against the live `storage-postgres` container on 2026-10-05: `flood_extent_polygon` is 5,125 MB total (5,125 MB of that is TOAST, the main relation is 160 kB), autovacuum is on with `scale_factor 0.2` and `threshold 50` and no per-table override, and `last_autovacuum` is null because the pipeline has been paused since 2026-10-04 and nothing has triggered it yet. A routine per-publish delete this small stays well under the autovacuum trigger threshold between runs, unlike the unbounded growth the table had before this story, so no `VACUUM FULL` call was added to the routine code path; see [[minio-flood-extent-pipeline]]'s Retention section for the full reasoning. Touched no `netcdf_values`, `mesh_elements`, `netcdf_variable_catalog`, or `timescaledb` container data, which `US-066` owns.

## Status history

- **2026-10-05, draft.** Opened from the gap `docker-data-vhdx-fills-c-drive-again`'s Approach 4 found: `flood_extent_polygon` has no retention policy, unlike the MinIO bucket and `flood_extent_step`, which `publish_run` already prunes.
- **2026-10-05, done.** `prune_polygon_rows` added and wired into `publish_run`. 21 tests pass, including the new coverage for this function, against a throwaway PostGIS container. No `VACUUM FULL` added; autovacuum's default thresholds are expected to keep up with the small, routine deletes this adds, reasoned from the live table's current autovacuum settings and TOAST-heavy size. Evidence: `us-067-prune-polygon-rows-check-output.png`.
