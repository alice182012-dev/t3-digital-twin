---
date: 2026-10-09
type: plan
branch: modular
status: active
tags: [plan, sprint-12, us-086, us-087, us-088, us-089, us-090, us-091, us-092, us-093]
related: ["[[sprint-plan-3]]", "[[core-output-hygiene-stories]]", "[[rain-replay-test-environment-stories]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[9c-sampling-step-runs-over-770-seconds]]", "[[US-094-095-archive-and-netcdf-retirement-stories]]", "[[2026-10-09]]"]
---

# Plan: Sprint 12, finish the routing

Sprint 12 started on 2026-10-09, 59 days before its planned start of 2026-12-07, at the user's request. It holds eight rows: four M (`US-089`, `US-090`, `US-091`, `US-092`) and four S (`US-086`, `US-087`, `US-088`, `US-093`). The sprint is one week of work (rule 10), and `US-070`, `US-094`, and `US-095` of Sprints 9 to 11 are still open beside it.

## What changed since the sprint was written

- `US-045`, `US-055`, and `US-073` are `Done` as of 2026-10-09, so the engine proof that `US-091` reads is closed.
- The replay left only 3 edge depth tables on the server (`20261009T024500`, `T030000`, `T031500`), all from the end of the storm. `EDGE_TABLE_KEEP_RUNS=3` removed the other 42. The Risks row of [[sprint-plan-3]] said to copy the tables before retention removed them, and that did not happen in time. The 3 tables are copied to `marie-curie/edge_tables_replay_2026-10-09/`.
- `US-091` needs the storm stages (cold start, one hour, three hours), and `US-093` needs depth tables across the storm. Three tables from the tail cannot give either. A second 12-hour replay with `EDGE_TABLE_KEEP_RUNS` raised (for example to 60) is the way to get them. This is open question 1 below.
- `flood_mapping_full` is paused, and the replay variables (`FLOOD_TEST_RAIN_CSV`, `FLOOD_TEST_RAIN_START`) are still set on the worker. `replay.ps1 stop` has not run.

## Order of work

1. **`US-088`, evidence only.** The event file `scripts/rain_events/hanoi_20260916_storm.csv` exists. Capture the screenshot of its check output and move the row to `Done`.
2. **`US-086`, build with tests first.** It is the cause to test for the growth of `US-070`, and it needs no new server data. See the next section.
3. **`US-090`, the proof.** It has no dependency and no server work. Write `artifacts/docs/concepts/sticky-closure-proof.md` with the six parts of the story, and add a test first for any boundary case that has none.
4. **`US-089`.** It stays `Reviewed` until the second replay ends and `replay.ps1 stop` runs (D-020).
5. **`US-091`, the harness.** Build the pair sampler, the route call, the re-walk, and the result writer on `scripts/routing_reference/` and the crossings check of `scripts/routing_proof/`. Test them against the 3 copied tables. The storm stages wait for the second replay, which runs after Sprint 12 (D-020).
6. **`US-092`** starts when the harness runs on one vehicle. If it does not by the middle of the sprint, it moves to Sprint 13 of [[sprint-plan-4]] with the user's go.
7. **`US-093`** copies the sampler of `US-091` and needs the same tables.
8. **`US-087`**, P3, fills a gap and is the first row to move to Sprint 13 if the sprint is full.

## US-086: prune `flood_road_values`

The story says rows older than 24 hours go (D-017). A size reading on 2026-10-08 gave 6,955 MB, about 18 MB per run, 377 run timestamps since 2026-09-23.

1. Read the table first: row count, size, rows per run, and the real meaning of the `timestamp` and `forecast_time` columns. Record them in [[core-output-contract]]. The story asks for this before any code.
2. Write the tests first. A table with runs across 30 hours leaves exactly the rows within 24 hours of the newest run. A table of one run leaves that run. A table whose newest run is old (a paused DAG, or a replay with past timestamps) is not emptied.
3. Measure age from the newest run in the table, not from the wall clock, so a pause or a replay cannot delete the only data. The story does not say this. The step 2 test pins it, and the user can overrule it.
4. Add the prune as a task in `routing_adapter` after `flood_on_roads`, with the window in a new variable that defaults to 24 hours.
5. Deploy today (D-019). The user chose to deploy before `US-094` is proven. Depth history older than 24 hours is then not archived. The first prune deletes about 95 percent of 14.8 million rows (413 runs, 7.4 GB), one run per transaction. Run it by hand while the DAG is paused, because inside `routing_adapter` it would hold the one pool slot and delay `9c`.
6. After the deploy, run `9c` timings again. The growth of `US-070` (44.8 to 90.3 s within a chain) should stop. That reading, not the unit test, decides `US-070` and the blocker [[9c-sampling-step-runs-over-770-seconds]].

## Decisions of 2026-10-09

1. The second replay runs after Sprint 12 (D-020). `US-091` and `US-093` build on the 3 copied tables and report storm stages after it.
2. `replay.ps1 stop` does not run. `US-089` waits for it, so it closes after the second replay.
3. `US-086` deploys today, before `US-094` is proven (D-019).
4. The prune measures age from the newest run in the table.
5. The blocker [[routing-not-time-aware]] is `resolved`.

## Risks

The Risks table of [[sprint-plan-3]] holds the row-move order. The new risk is the depth tables: without the second replay, `US-091` and `US-093` cannot report storm stages, and `US-092` waits on `US-091`.
