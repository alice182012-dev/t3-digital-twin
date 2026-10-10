---
date_open: 2026-10-05
date_closed: 2026-10-10
type: blocker
status: resolved
severity: P1
subsystem: airflow-pipeline
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, airflow, postgres, edge-depth-table, replay]
related: ["[[PRD-003-edge-depth-table|edge-depth-table]]", "[[EP-08-edge-depth-table|edge-depth-table-stories]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]"]
last_updated: 2026-10-10
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

Closed by the product owner on 2026-10-10, see Status history. Before the close, the plan was: after `git pull alice front-end-according-to-mock-up` on the server (scripts are bind-mounted, so no image
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
- **2026-10-10, monitoring.** `US-070` and `US-086` are `Done`. `9c` still rose within a chain in the second replay (46 s to 96 s in chain 1), with no run past the 120 s cancel, so the blocker stays `monitoring`. The readings are in [[US-070-stop-a-slow-sampling-step-from-holding|US-070]].
- **2026-10-10, monitoring.** The replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] (04:45 to about 18:15 +07) gave the longest `9c` of the chain at each sample.
  It grew from 57 s (the run at 05:07 +07, first seen at the 05:09 reading) to 109 s (the run at 15:22 +07, first seen at the 16:17 reading), and it averaged 87 s over 54 runs at the 18:17 reading.
  No run passed the 120 s cancel.
  The longest value is under 120 s, but the duration still grows with the length of the chain, so the owner decides at planning (open decision 8 in [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]).
- **2026-10-10, monitoring.** The `n_dead_tup` of `flood_depth_raster_tile` was 0 at the 07:47, 10:47, 13:47, and 16:17 readings.
  It was 7,040 at the 04:04, 05:09, and 18:17 readings, each taken after an autovacuum (at 00:38, 04:53, and 18:06 +07).
  Those three readings also show the same live and dead counts (56,320 and 7,040), so the statistics may not have refreshed, but the cause is not proven.
  The claim that the dead-tuple count is 0 after each autovacuum does not hold for these readings.
  The raw readings are in `marie-curie/us-102/bl023_samples.log`, and the script is `marie-curie/us-102/bl023_sample.sh`.
- **2026-10-10, resolved.** The product owner closed this blocker on 2026-10-10. The readings above stay as the record: the longest `9c` grew to 109 s under the 120 s cancel, and the cause is not proven.
