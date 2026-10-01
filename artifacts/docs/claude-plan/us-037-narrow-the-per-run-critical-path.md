---
date: 2026-10-01
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, pipeline, performance, us-037, sprint-4]
related: ["[[carried-over-backlog]]", "[[sprint-plan]]", "[[2026-10-01]]", "[[five-minute-tile-freshness]]", "[[map-shows-forecast-not-now]]", "[[flood-mapping-full-worker-concurrency-serializes-runs]]", "[[3di-simulation-orchestration]]"]
---

# Plan: US-037 narrow the per-run critical path

## Context

`US-037` ([[carried-over-backlog]] Story 6, Sprint 4, M, P2) is option D of [[five-minute-tile-freshness]]. A run that starts at slot tₖ must publish the step 1 tile before tₖ + 15 minutes, because then the next slot's step 1 becomes "now". The user chose this over accepting the delay ([[map-shows-forecast-not-now]]). The pass condition is four consecutive real runs that publish step 1 before it becomes now, with a measured margin.

## Facts that shape the design

1. The margin of a run is `slot + 15 min - end of 9_build_flood_tiles`. A negative margin means the tile is late. `marie-curie/us-037/run_margins.sh` prints it from the Airflow database.
2. Baseline from the runs on record, in minutes (trigger, depth, raster load, tiles, margin):

| Slot (+07) | Trigger | Depth | Raster | Tiles | Margin |
| ---------- | ------- | ----- | ------ | ----- | ------ |
| 2026-09-29 15:15 | 3.3 | 7.0 | 2.4 | 6.3 | -1.9 |
| 2026-09-29 15:30 | 3.1 | 7.7 | 3.4 | 10.4 | -6.5 |
| 2026-09-29 15:45 | 3.2 | 8.2 | 2.5 | 9.3 | -6.1 |
| 2026-09-29 16:00 | 3.2 | 7.9 | 2.3 | 9.8 | -6.3 |
| 2026-09-29 16:15 | 3.2 | 8.0 | 2.3 | 10.3 | -6.8 |
| 2026-09-30 01:15 | 3.5 | 6.7 | 2.5 | 4.7 | -4.8 |
| 2026-09-30 01:30 | 4.1 | 6.8 | 2.3 | 5.3 | -1.6 |
| 2026-09-30 01:45 | 3.4 | 6.8 | 2.4 | 6.4 | -1.9 |

3. The critical path of one run is trigger, download (0.2), depth, then tiles. The raster load and flood-on-roads tasks run beside the tiles and are not on it. The sum is about 17 minutes against 15.
4. The trigger (3.4 min) is the 3Di simulation, which this repository does not control. That leaves depth (about 7 min) and tiles (about 5 to 10 min).
5. The tile build takes 4.7 to 6.4 min in some runs and 9.3 to 10.4 min in others. The slow runs overlapped the next run's depth calculation, so the two share the server's 12 logical CPUs and 15.6 GiB. That is a hypothesis until the CPU samples confirm it.
6. Current settings in the worker: `MAX_WORKERS` 8 for depth, `FLOOD_EXTENT_WORKERS` 2 for tiles, `AIRFLOW__CELERY__WORKER_CONCURRENCY` 4. The `depth_calc` pool holds one depth task at a time.
7. `FLOOD_TEST_RAIN_MM_HR=50` is set, so every run simulates a 50 mm/h storm. That is the heavy case for the tile build.

## Decisions already made

1. `flood_mapping_full` was unpaused at 18:19 +07 on 2026-10-01, with the test rain kept, at the user's request.
2. Measure first. No knob changes until the CPU and memory samples and the margins of at least three real runs exist.

## Steps

1. Collect samples. `marie-curie/us-037/sample_stats.sh` records the worker's and the database's CPU and memory every 5 seconds until 19:15 +07. The first run on the new clock starts at the 18:30 slot.
2. Read the margins of the new runs with `run_margins.sh`, and line the CPU samples up with each run's depth and tile windows.
3. Choose a lever from the evidence: more depth workers, more tile workers, or stopping the tile build from overlapping the next run's depth. Ask the user for the margin they want, because the story names none.
4. Change one knob, redeploy over SSH with `--no-deps`, and collect four consecutive runs.
5. Record the table of margins, a screenshot of rendered output, and numbered details in the sprint plan, the epic, and the log. Update [[map-shows-forecast-not-now]] and [[five-minute-tile-freshness]].

## Status history

- **2026-10-01, active.** Plan written. Baseline table taken from the Airflow database. The sampler and the first new run are under way.
- **2026-10-01, active.** The unpause started the 18:15 slot (`scheduled__2026-10-01T11:15:00+00:00`) at about 18:19, four minutes late. Its margin is not used. The first usable run is the 18:30 slot. Three usable runs finish by about 19:20.
