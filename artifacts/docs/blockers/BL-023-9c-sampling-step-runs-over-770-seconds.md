---
date_open: 2026-10-05
date_closed: 
type: blocker
status: monitoring
severity: P1
subsystem: airflow-pipeline
approaches_tried: 1
approaches_remaining: "confirm the cause on the server, from the 9c log after the pull, and the plan of a slow step if one is cancelled"
tags: [blocker, airflow, postgres, edge-depth-table, replay]
related: ["[[PRD-003-edge-depth-table|edge-depth-table]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]"]
last_updated: 2026-10-06
---

# 9c sampling step runs over 770 seconds

## Description

During the 48-hour replay, task `9c_build_edge_depth_table` of the first run ran far longer than the 42.0 s measured
with no load. The sampling query (`_SAMPLE_SQL` in `scripts/edge_depth/build_edge_depth.py`) was active for 772 s with
no wait event and no lock. The task had been running 785 s. It was not queued (wait of 0 s). `storage-postgres` used
154% CPU and the worker 108%. `flood_on_roads` took 45 s for the same run.

## Why this matters

The query holds the database CPU that the next runs need, and runs start every 15 minutes, so slow 9c tasks can pile
up. `US-045` (prove the table on the server) needs the 9c timing under load, and `US-055` needs a working table.
The task fails without failing the run, so the tile path is not blocked.

Severity of the case under rule 11 of `.claude/CLAUDE.md`: it does not block build in the next sprint. The fix is
small, built and tested. The server pull is the only open step, and it waits for the user.

## Approaches tried

### Approach 1

Read the evidence the user pasted. Wet pixels per step are 1.57M to 1.72M over 880 tiles for the replay runs and
1.60M to 1.61M for the old run `20261005T120000`, so a larger wet area does not explain it. `flood_depth_raster_tile`
had no statistics when the first 9c query started at 17:07:20Z. Autoanalyze ran at 17:22:08Z. The leading theory is a
plan made on missing statistics. It is not proven, because the `EXPLAIN` the user ran printed the plan of the
`pg_stat_activity` query.

Built a guard, tests first (133 tests pass in `scripts/edge_depth/`, and removing either guard fails a test).
`build_table` runs `ANALYZE flood_depth_raster_tile` before sampling, and sets a per-step `statement_timeout` of 120 s
(`DEFAULT_STEP_TIMEOUT_S`). A step past the limit fails the build with "step N of M ... was cancelled". The previous
table stays published. Pushed as `5e358bf`. Not on the server yet.

## Decision and explanation

Pending. After `git pull alice front-end-according-to-mock-up` on the server (scripts are bind-mounted, so no image
build), the next 9c log shows whether `ANALYZE` was the fix. If a step is cancelled, its plan is the next evidence.
The running query was not cancelled, because that is the user's call.

## Concerns

The 120 s limit is a guess at 20 times the idle step time. A heavily loaded but healthy database could trip it and
leave the table stale for a run. The cause is unproven until the server shows it.

## Related topics

- [[PRD-003-edge-depth-table|edge-depth-table]]
- [[EP-08-edge-depth-table|edge-depth-table-stories]] Story E8 (`US-070`)

## Status history

- **2026-10-05, open.** Found during the replay by the user ("the task 9c is taking really long"). Case under rule 11: does not block build.
- **2026-10-05, open.** Approach 1 built and pushed (`5e358bf`). Waiting for the pull on the server and the next 9c log.
- **2026-10-06, monitoring.** The server working directory is at `4d262ef`, which contains the fix (`5e358bf`), so the pull is done. Run `20261006T104500` (slot 03:30 UTC, task started 10:41:12 +07) took 51.1 s: 8 steps of 5.7 to 6.8 s, 67,833 edges, 1,085,487 bytes, published. The log prints no `ANALYZE` line and the pull time is unknown, so it is not proven that this run used the guard. Next evidence: `last_analyze` of `flood_depth_raster_tile` against the run start, and several more 9c runs under load. Close it as `resolved` when they stay near 50 s.
- **2026-10-06, monitoring.** The user ran the `pg_stat_user_tables` check on the server. `last_analyze` of `flood_depth_raster_tile` is 2026-10-06 03:41:16 UTC, four seconds after run `20261006T104500` started 9c (03:41:12 UTC), so the guard's `ANALYZE` ran in that run. `last_autoanalyze` is still 2026-10-05 17:22:08 UTC, the old value, so autovacuum has not analyzed the table since and the build's own `ANALYZE` is the only fresh statistics. The run took 51.1 s. That supports the stale-statistics theory but does not prove it, since one run is one sample. Close as `resolved` after several more 9c runs under load stay near 50 s.
- **2026-10-07, monitoring.** `US-073` moved 9c into its own `routing_adapter` DAG, merged to branch `modular` and running on the server since 2026-10-07 16:00 +07. `table_timing.ps1 -Runs 250` found exactly one real 9c run from it so far (the DAG only started two hours earlier): build time 60.1 s, same 67,833 edges and 1,085,487 bytes as the 2026-10-06 run, still near 50 to 60 s inside the step. But the gap from the end of `3_calculate_depth` to the end of 9c was 8.21 minutes, over `US-045`'s 5-minute limit, most likely the new DAG's cold-start/asset-event catch-up rather than a real regression, but n=1 cannot tell the two apart. Stays `monitoring`, not `resolved`: need several more `routing_adapter` runs once the replay ends to see whether the build time holds near 50 to 60 s and whether the end-to-end gap comes down once the DAG is warm.
- **2026-10-10, monitoring.** `US-070` and `US-086` are `Done`. In the second replay (45 runs after the prune and `VACUUM FULL`) `9c` took 46 to 96 s, mean 65 s, with no run past the 120 s cancel and no 770 s step in 92 runs. It still rose within chain 1 (46 s to 96 s over 27 runs) and in chain 2 (46 s to about 60 s over 18 runs). The cause is unknown, so the blocker stays `monitoring`.
