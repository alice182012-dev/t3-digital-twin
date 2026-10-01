---
date: 2026-10-01
type: plan
branch: front-end-according-to-mock-up
status: done
tags: [plan, pipeline, performance, us-037, sprint-4]
related: ["[[carried-over-backlog]]", "[[sprint-plan]]", "[[2026-10-01]]", "[[five-minute-tile-freshness]]", "[[map-shows-forecast-not-now]]", "[[flood-mapping-full-worker-concurrency-serializes-runs]]", "[[3di-simulation-orchestration]]"]
---

# Plan: US-037 narrow the per-run critical path

## Context

`US-037` ([[carried-over-backlog]] Story 6, Sprint 4, M, P2) is option D of [[five-minute-tile-freshness]]. A run that starts at slot tₖ must publish the step 1 tile before tₖ + 15 minutes, because then the next slot's step 1 becomes "now". The user chose this over accepting the delay ([[map-shows-forecast-not-now]]). The pass condition is four consecutive real runs that publish step 1 before it becomes now, with a measured margin.

## Facts that shape the design

1. The margin of a run is the time step 1 becomes "now" (slot + 15 min) minus the time its tile is published. The task log line `<run>: 190 tiles` marks the publish. A negative margin means the tile is late. `marie-curie/us-037/run_margins.sh` prints a stricter figure, the end of the whole `9_build_flood_tiles` task, which is about 1 minute later because step 2 finishes after step 1.
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

## Measurements of 2026-10-01

Four runs after the unpause (slots 18:15, 18:30, 18:45, and 19:00 +07). The 18:15 slot started four minutes late, so only the last three are steady.

| Slot (+07) | Trigger | Depth | Tiles (task) | Step 1 published | Margin at step 1 |
| ---------- | ------- | ----- | ------------ | ---------------- | ---------------- |
| 18:15 | 3.4 | 7.1 | 5.3 | 18:33:27 | -3.5 min (late start, not used) |
| 18:30 | 3.6 | 7.5 | 5.7 | 18:46:10 | -1.2 min |
| 18:45 | 3.1 | 7.0 | 6.7 | 19:00:51 | -0.8 min |
| 19:00 | 3.1 | 6.9 | 7.4 | 19:16:42 | -1.7 min |

Findings, with the log or file each comes from:

1. Step 1 is published 0.8 to 1.7 minutes after it becomes "now". The gap to close is about 2 minutes for a 0.5 minute margin, and about 3 for a 1.5 minute margin.
2. Step 2 is published 1 to 1.3 minutes after step 1 and 10 to 13 minutes before it is due. Only step 1 sits on the critical path.
3. All 8 depth files finish within 2.4 seconds of each other (file modification times in `depth_20261001_191500_210000`). Each step costs about the same, so the depth task takes as long as one step with 8 running at once.
4. The worker's CPU averages 384 to 426 percent during depth, out of 1,200, with 8 processes running. Peaks were 537 to 1,014 percent. Memory peaked at 5.2 GiB of 15.6. So the 8 processes spend about half their time waiting, not computing. Disk or lock contention on the shared NetCDF file is the likely cause. This is a hypothesis.
5. The task ends 31 seconds after the last depth file is logged (`pool.close()`, `pool.join()`, and the directory rename in `calculate_depth.py`).
6. Tile build averages 328 to 362 percent with brief peaks of 1,014 to 1,172 percent. One step takes about 6 minutes. The logs print no stage times.
7. Raising `MAX_WORKERS` cannot help, because the 8 steps already have 8 processes. The levers that can help are doing steps 1 and 2 first, with fewer processes at once, and shortening the tile build of one step.

## Experiment of 2026-10-01

`marie-curie/us-037/depth_experiment.py` ran `threedidepth` on the retained results of the 19:00 slot, with the DAG paused and the worker idle (19:40 to 19:58 +07). The raw output is in `marie-curie/us-037/experiment-results.txt`.

| Steps at once | Inputs | Outputs | Slowest step |
| ------------- | ------ | ------- | ------------ |
| 1 | bind mount | bind mount | 206.0 s |
| 2 | bind mount | bind mount | 217.5 s |
| 8 | bind mount | bind mount | 368.6 s |
| 8 | local disk | bind mount | 148.6 s |
| 8 | local disk | local disk | 150.1 s |

1. Eight steps on the bind mount took 6.1 minutes on an idle server, close to the 6.4 to 7.5 minutes of the production runs. So the slowdown does not come from other tasks.
2. The same eight steps with the DEM (93 MB), the grid (3 MB), and the results file (8 MB) copied to the container's disk took 2.5 minutes. The copy took 0.7 seconds. The cause is concurrent reads of the inputs through the Windows bind mount.
3. Where the outputs go does not matter (148.6 s against 150.1 s).
4. The fix is to read the inputs from local disk. The expected saving is about 3.6 minutes of depth time, which turns a step 1 margin of -0.8 to -1.7 minutes into about +2 to +3. Splitting the depth task into a head start for steps 1 and 2 is no longer needed unless the measured margin falls short.

## After the depth fix, 2026-10-01 evening

The depth fix (`684262b`, `3e83a7f`) reached the server at 20:02 +07. The first runs on it:

| Slot (+07) | Trigger | Depth | Tiles (task) | Step 1 margin | Note |
| ---------- | ------- | ----- | ------------ | ------------- | ---- |
| 20:00 | failed | | | | 3Di returned 429, no free session for the organisation |
| 20:15 | 3.1 | 3.3 | 10.5 | -1.2 min | first run on the fix |
| 20:30 | 3.4 | 3.5 | 15.0 | -5.1 min | contaminated: profiling jobs ran in the same worker from 20:32 to 21:00 |

1. The fix works as measured: depth fell from 6.8 to 7.5 minutes to 3.3 to 3.5 minutes.
2. The tile build grew from 5.3 minutes (18:15) to 10.5 minutes (20:15). The test storm of 50 mm/h keeps growing the flooded area, and the tile build grows with it.
3. A stage profile of step 1 of the 20:15 run (`flood_extent.py` run verbosely on `depth_20261001_203000.tif`, 20:32 +07):

| Stage | Seconds |
| ----- | ------- |
| reclassify depth | 4.5 |
| close bands | 30.8 |
| polygonize | 67.1 |
| dissolve | 440.7 |
| clean | 4.8 |
| cut tiles | 70.2 |

The dissolve (`ogr2ogr -dialect SQLite`, one `ST_Union` per band group, one thread) is 80 percent of the tile build for one step.
4. Variants tried on the same file:
   - `ST_Collect` instead of `ST_Union`: dissolve 1.8 s, but the band areas came out 2 to 7 percent larger (band 20: 1,690,333 against 1,593,327 m2). The `-8` polygonize leaves overlapping polygons of one band, so the union is needed.
   - `ST_UnaryUnion(ST_Collect())`: same areas as the baseline, but 613.7 s (slower, under load). No gain.
   - `ST_Union` per band, all bands in parallel (on a later step's polygons): slowest band 211.2 s, against 780 s for the bands one after another.
5. Lever chosen: a per-band parallel dissolve with the exact `ST_Union`. A subagent builds it in `scripts/flood_extent/flood_extent.py`. I verify on the server against the baseline areas before it goes live.

## Decisions already made

1. `flood_mapping_full` was unpaused at 18:19 +07 on 2026-10-01, with the test rain kept, at the user's request. It was paused from about 19:34 to 19:59 for the experiment and unpaused again.
2. Measure first. No knob changes until the CPU and memory samples and the margins of at least three real runs exist.

## Steps

1. Collect samples. `marie-curie/us-037/sample_stats.sh` records the worker's and the database's CPU and memory every 5 seconds until 19:15 +07. The first run on the new clock starts at the 18:30 slot.
2. Read the margins of the new runs with `run_margins.sh`, and line the CPU samples up with each run's depth and tile windows.
3. Lever chosen from the experiment: copy the DEM, the grid, and the results file to the container's disk before the 8 processes start. A subagent builds it in `scripts/depth_inputs.py` and `scripts/calculate_depth.py`, tests first.
4. Push, then `git pull --ff-only` on the server. `./scripts` is mounted into the Airflow containers, so the next run uses the change. Collect four consecutive runs and read the margins.
5. Record the table of margins, a screenshot of rendered output, and numbered details in the sprint plan, the epic, and the log. Update [[map-shows-forecast-not-now]] and [[five-minute-tile-freshness]].

## Status history

- **2026-10-01, active.** Plan written. Baseline table taken from the Airflow database. The sampler and the first new run are under way.
- **2026-10-01, active.** The unpause started the 18:15 slot (`scheduled__2026-10-01T11:15:00+00:00`) at about 18:19, four minutes late. Its margin is not used. The first usable run is the 18:30 slot. Three usable runs finish by about 19:20.
- **2026-10-01, active.** Measured four runs (table above). Next: an experiment that times one depth step alone and two steps together on the retained NetCDF, to see whether fewer processes make each step faster. It needs the DAG paused for about 15 minutes, so it waits for the user's go-ahead.
- **2026-10-01, active.** Experiment done (table above). Inputs on local disk cut 8 steps from 368.6 s to 148.6 s. `flood_mapping_full` is unpaused again. A subagent is building the change.
- **2026-10-01, active.** The depth fix works (depth 3.3 to 3.5 minutes). The tile build is now the long pole: the dissolve takes 440.7 s of about 550 s. A subagent builds a per-band parallel dissolve. The 20:30 run's margin is contaminated by my profiling jobs, so it does not count.
- **2026-10-01, active.** The per-band parallel dissolve (`4e793c0`, `1607484`) is verified on the server: on the same depth file the area per band equals the baseline in all 7 bands and the tile count is 190 in both. The dissolve took 275.7 s against 440.7 s, measured while a live run shared the worker. It was pushed and pulled on the server at 23:15 +07. The 23:15 slot is the first run that uses it.
- **2026-10-01, active.** Trend from the runs between 20:45 and 22:45: the tile task takes 14.6 to 17.0 minutes, longer than the 15-minute cycle, so runs overlap and depth rises again to 3.7 to 6.1 minutes. The 50 mm/h test storm keeps enlarging the flooded area, so the tile build keeps growing. Margins in this period are not a fair measure of the fixes. The four runs that count start with the 23:15 slot.
- **2026-10-01, active.** Run 1 of the check: the manual run of 23:16 (slot 23:15, due 23:30). The user had stopped the 23:00 and 23:15 scheduled runs, and I stopped the two orphaned old-code dissolves of the 23:00 run. The trigger took until 23:20:21 (the first attempt went up for retry), depth took 3.25 minutes (23:20:35 to 23:23:50), tiles took 10.8 minutes (23:23:51 to 23:34:41), and step 1 was published at 23:34:34, 4.6 minutes after it was due. This is the first run with the per-band dissolve. Between 20:45 and 22:45 the same storm size gave tile tasks of 14.6 to 17.0 minutes, so the dissolve change cut about 4 to 6 minutes. It started 2.7 minutes after its slot because of the retried trigger, so an on-time run would have been about 1.9 minutes late. Not a pass yet. The 23:30 and 23:45 scheduled runs start on their slots and nothing else runs in the worker.
- **2026-10-02, done.** The cold start rule (`eef34aa` to `828446f`) is on the server. The DAG was unpaused after a state reset. The cold-started 00:30 slot started 11 minutes late and does not count. Four consecutive on-time runs followed: 00:45 (+1.9), 01:00 (+4.1), 01:15 (+2.7), and 01:30 (+2.4 minutes), with tile tasks of 4.4, 5.0, 5.7, and 6.1 minutes. `us-037-margins-check-output.png` shows the output. The story is `Done`. The user's 5-minute lateness target was not needed.
