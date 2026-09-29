---
date_captured: 2026-09-30
type: idea
status: exploring
source: conversation with the user, 2026-09-30, after the Sprint 2 close-out, with a queueing model in marie-curie/stagger_sim.py
subsystem: airflow-pipeline, floodmap-backend, floodmap-frontend
tags: [idea, freshness, tiles, staggered-runs, five-minute-tiles, cpu-pool]
related: ["[[five-minute-tile-freshness]]", "[[flood-mapping-full-worker-concurrency-serializes-runs]]", "[[hotstart-state-saved-at-end-of-run]]", "[[map-shows-forecast-not-now]]", "[[fifteen-minute-cycle-tiles-and-histogram]]"]
---

# Add light "map" runs every 5 minutes next to the 15-minute full run

## Idea

Keep the full pipeline as it is, on `*/15`. Add a second DAG that starts a light "map" run every 5
minutes. A map run simulates, downloads, calculates depth for steps 1 and 2 only, and builds their
tiles. It skips the netcdf upload, the raster load, and `flood_on_roads`, which the full run keeps.

The goal is a new map tile every 5 minutes, not every 15. This is option E in
[[five-minute-tile-freshness]], with a cheaper run so that the CPU can carry it.

## Why the obvious version fails

Staggering the full pipeline hits the CPU, not the 3Di simulation. One simulation takes about 3.3
minutes and 3Di does the compute. One full run costs 78.9 core-minutes on the worker, and the host has
12 logical cores. Depth calculation alone is 8 processes for 7.3 minutes, which is 58.5 of those
core-minutes.

The lowest stable spacing for the full pipeline is therefore about 7 minutes, and only after
`depth_calc` goes from 1 pool slot to 2. At 5 or 6 minutes the queue grows without limit.

## What was measured

Medians of 25 to 27 successful `flood_mapping_full` runs, from Airflow's `task_instance` table
(2026-09-28 to 2026-09-29).

| Task | Median | Range |
| ---- | ------ | ----- |
| `1_trigger_simulation` | 3.32 min | 3.00 to 4.11 |
| `2_download_results` | 0.21 min | 0.13 to 0.32 |
| `3_calculate_depth` | 7.31 min | 6.66 to 8.91 |
| `3b_upload_netcdf_postgres` | 2.09 min | 1.31 to 2.93 |
| `9_build_flood_tiles` | 6.71 min | 4.31 to 14.39 |
| `9b_load_depth_raster` | 2.35 min | 2.20 to 3.60 |
| `flood_on_roads` | 2.33 min | 1.99 to 3.21 |

From the create-simulation log line to the first depth file, across 9 runs: minimum 9:51, median 10:54,
maximum 12:16. In the slot 18:15 run, the first depth file finished 9:49 after the create line, and the
tiles for steps 1 and 2 finished 15:04 after it. Step-1 tiles were done 3:16 into a 4:34 tile task, so
the model gives step 1 a 72% share of the tile task.

Live limits on 2026-09-29: 4 Celery slots (`AIRFLOW_WORKER_CONCURRENCY`), pool `threedi_trigger` 2,
pool `depth_calc` 1, `max_active_runs=2` on the DAG, 6 physical and 12 logical cores.

## Model

`marie-curie/stagger_sim.py` (scratch, untracked). It simulates each task with a Celery slot, the two
pools, and a CPU-sharing rule: when the running tasks want more than 12 cores, all of them slow down in
proportion. A task's core demand is depth 8 (full) or 2 (map), tiles 2, others 1. The map shows the
newest published tile whose valid time is at or before now. "Age" is now minus that valid time.

Today's real age is the step-2 rule, not step 1. Step 2 of the previous run covers the same valid time
as this run's step 1, and it is ready earlier, so the map uses it. Today: age mean 7.5 min, p95 14.3,
max 15.0.

Full run every S minutes:

| S | Result | Tile ready after start | CPU |
| - | ------ | ---------------------- | --- |
| 15 (today) | stable | 15.7 min | 44% |
| 9 | stable | 15.7 min | 72% |
| 8 | stable | 15.7 min | 80% |
| 7, `depth_calc` 1 | queue grows | 25.8 min and rising | 88% |
| 7, `depth_calc` 2 | stable, tight | 16.8 min | 92% |
| 6 or 5, `depth_calc` 2 | queue grows | 44 to 94 min and rising | 98% |

Full run every 15 minutes plus a map run every S (8 slots, `depth_calc` pool 4), tile taken from step 2:

| S | Age mean | Age p95 | Age max | On time | CPU |
| - | -------- | ------- | ------- | ------- | --- |
| 9 | 3.7 min | 8.3 | 9.0 | 100% | 69% |
| 8 | 3.3 min | 7.3 | 8.0 | 100% | 72% |
| 7 | 3.0 min | 6.5 | 7.0 | 100% | 76% |
| 6 | 2.7 min | 5.7 | 6.0 | 100% | 81% |
| 5 | 2.5 min | 4.8 | 5.0 | 100% | 88% |

The step-2 tile is ready about 18 to 20 minutes after start against 30 minutes of lead, so it is on
time in every row.

The model starts a map run at every multiple of S, including the quarter hours. The cron in the design
skips those, which is 8 map runs an hour instead of 12 at S=5. So the CPU figures here are a little high
for the design. The lower load was not simulated.

Stress, map runs every 5, 6, or 7 minutes:

- Heavy rain (tile time doubled, depth 22% slower): unstable at every spacing from 5 to 7 (CPU 97%).
- Only 9 effective cores: unstable at every spacing from 5 to 7.
- 6 slots instead of 8: still stable, at a slightly later tile.

## Recommendation

Build the map DAG for a 5-minute spacing, with a backoff to 10 minutes when it rains hard or the CPU
queue builds up. The 5-minute spacing is the one that matches the existing state saves at 900 s and
1800 s, so it needs no new save logic. At normal rain the model shows 88% CPU and 5.6 slots busy on
average. That leaves little headroom, which is why the backoff is part of the design.

Expected result if the assumptions hold: the tile's age drops from mean 7.5 and p95 14.3 minutes to
mean 2.5 and p95 4.8.

## Design sketch

1. Map DAG cron `5,10,20,25,35,40,50,55 * * * *`. It skips the minutes the full DAG already owns.
   Together the two DAGs cover a new valid time every 5 minutes.
2. Do not chain the DAGs. The simulation is cheap, and chaining ties the map back to the full run's
   18.8-minute critical path.
3. One shared pool `cpu` with 12 slots. Each CPU task asks for `pool_slots` equal to its cores: full
   depth 8, map depth 2, tiles 2, others 1. This replaces `depth_calc` and keeps its protection against
   two full depth runs at once.
4. Higher `priority_weight` on map tasks. `max_active_runs=4` and `catchup=False` on the map DAG. Worker
   concurrency 8 to 10. `threedi_trigger` pool 3.
5. A guard task at the start of each map run that skips the run when 4 are already active, the `cpu`
   pool has a queue, or rain is heavy.

## What could break

From reading the code on 2026-09-30.

- **A lost hotstart state, silently.** `save_saved_states` in `scripts/create_simulation.py` (line 59)
  reads the state file, merges, and writes it back with no lock. Two runs that register at the same
  moment can overwrite each other. The next run then finds no state and cold starts from a dry model,
  so the map shows too little water and nothing fails.
- **Too few states kept.** `SAVED_STATES_KEPT = 8` (line 41) covers about 4 runs. Staggered runs need at
  least 24.
- **The slot rounds to 15 minutes.** `CYCLE_MINUTES = 15` (line 37) and `clock_slot` (line 93) floor
  every run to a quarter hour. Runs at `:05` and `:10` would land on `:00`. The fallback window in
  `choose_saved_state` (line 76) is `2 * CYCLE_MINUTES`, so it would also be wrong for a 5-minute cycle.
- **Retention by count.** `keep_runs=8` in `scripts/flood_extent/publish.py` (line 157) and
  `FLOOD_EXTENT_KEEP_RUNS` in `dags/flood_mapping_dag.py` (line 50) keep the newest 8 runs. Map runs every
  5 minutes push a full run's tiles out within an hour. Keep by age, about 3 hours, or a count near 24.
- **CPU oversubscription.** Two full depth runs at once want 16 processes on 12 cores.
- **`max_active_runs=2`** on the DAG (line 303) must be raised, or the map runs go in their own DAG.

Depth temp folders use a UUID and result folders use the simulation ID, so those do not collide.

## Risks and open questions

- **Map and routing disagree.** The map would update every 5 minutes, but routing still reads
  `flood_road_values` from the 15-minute run. A route can be planned on water up to 15 minutes older
  than the map shows.
- **3Di usage.** Simulations go from about 4 an hour to about 12 (8 map runs plus 4 full runs). The quota
  and the cost are unknown.
- **Tomorrow.io.** Each run reads the rain forecast, so the number of calls rises in step. The rate
  limit is unknown.
- **CPU headroom.** The model treats 12 logical cores as 12 usable cores. The host has 6 physical cores.
- **Sensitivity.** The model uses medians. Heavy rain doubles the tile time and breaks 5 minutes.

## What to measure first

1. Depth calculation time for 2 steps on 2 processes. The model assumes 7.3 minutes. It could be much
   less, which would give headroom.
2. The effect of a shorter simulation horizon. The map needs 30 to 45 minutes of simulated time, not the
   current 2 hours. A shorter horizon could cut both simulation time and depth time. This is an untested
   hypothesis.
3. Tile time for a heavy-rain event, since it decides how far the spacing has to back off.

Then run both DAGs together at a 10-minute spacing, watch the `cpu` pool's queued slots, and move to 5
minutes only if the queue stays empty.

## Status history

- **2026-09-30, exploring.** Captured after the Sprint 2 close-out. The model, the measured durations,
  and the code review of the state file, the slot rounding, and the retention are recorded above. No
  story or sprint slot yet. Under the sprint-plan rules, a story comes first, and a `TODOS.md` item
  follows once the story has a sprint.
