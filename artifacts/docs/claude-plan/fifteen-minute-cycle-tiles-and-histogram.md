---
date: 2026-09-25
type: plan
status: active
tags: [plan, tiles, forecast, histogram, frontend, airflow]
related: ["[[map-shows-forecast-not-now]]", "[[hotstart-state-saved-at-end-of-run]]", "[[route-forecast-query]]", "[[depth-forecast-chart]]", "[[minio-flood-extent-pipeline]]", "[[raster-first-flood-pipeline]]"]
---

# Fifteen-minute cycle: tiles and flood histogram

Code for the proposed design in [[map-shows-forecast-not-now]]. The user makes the new 3Di template (900 s output
interval, 8 depth steps). This plan covers the code that reads its output. Routing is out of scope
([[routing-not-time-aware]]), and so is `scripts/create_simulation.py` (start on the clock, state saved at 900 s),
because it follows the template.

## Data shape

A **step** is one `(run_ts, valid_time_utc)` pair. Each run has up to 8 steps on the shared 15-minute grid. Two
new facts about a step have to be stored, because nothing records them today:

- `published`: the tiles and polygon rows of the step are fully uploaded. Set last. A step with no flooding has no
  polygon rows, so `flood_extent_polygon` cannot carry this fact, and an empty step would fall back to an older
  run's wet tile.
- `is_empty`: the step published with no flooding.

New table `flood_extent_step (run_ts, valid_time_utc, is_empty, published_at)`, primary key `(run_ts, valid_time_utc)`.

## Rules

1. **Tiling.** `publish_run` builds tiles and polygons for the first `tile_steps` (default 2) depth files of a run
   only. The depth raster load still covers every step.
2. **Timesteps.** `GET /flood/timesteps` returns, for each `valid_time_utc`, the newest run that published it, ascending,
   each entry `{valid_time, run}`. Runs are no longer a single series.
3. **Map pick.** The frontend selects the latest `valid_time` at or before now. Never the nearest. If every step is in the
   future, it falls back to the earliest one.
4. **Retention.** The bucket and raster keep enough runs that the last hours of "now" tiles survive
   (`FLOOD_EXTENT_KEEP_RUNS` and `raster_load` `keep_runs`, default 8).
5. **Histogram.** For a list of points, `GET`/`POST /flood/forecast` returns the mean depth per 15-minute time from the
   raster tiles, taking each time from the newest run that has a raster for it. The frontend draws it as columns with
   the "now" column highlighted.

## Workstreams

| Stream | Files | Depends on |
| --- | --- | --- |
| A. Tiling backend | `scripts/flood_extent/publish.py`, `scripts/database/create_flood_extent_tables.py`, `backend/flood_extent_runs.py`, both DAGs | none |
| B. Map pick | `floodmap/graphhopper-maps/src/floodmap/FloodStore.ts`, `timestepLabel.ts`, tests | rule 2 shape only |
| C. Histogram | new `backend/flood_forecast.py`, `server.py`, a chart component in `graphhopper-maps` | none |

| D. DAG shape | `dags/flood_mapping_dag.py`, `dags/flood_forecast_state_test_dag.py` | A merged (same files) |

Stream D changes the DAG to match the cycle: a separate task for the step 1 and 2 tiles that starts as soon as the depth
tifs exist, raster load and flood on roads over all 8 steps, a 15-minute clock schedule, and a review of
`max_active_runs` and the local cleanup so overlapping runs do not delete each other's files. Stream A only passes
`tile_steps` and the retention setting through.

## Status

- **2026-09-25.** Plan written. Streams A, B, C started as separate delegates.
- **2026-09-26.** Streams A to D built and merged into the local branch `fifteen-minute-cycle` (not pushed, per the push hold).
  Merged tree: jest 193 of 193, `tsc` clean, publish and raster tests 26 of 26 against a throwaway PostGIS, DAG graph tests
  24 of 24. Not run: `test_flood_forecast.py`'s endpoint checks (no PostGIS container was allowed), the chart in a browser,
  and the two-overlapping-runs CPU load. Left for the user: `create_simulation.py` (3Di start from the clock slot, state
  saved at 900 s), and the caption wording ("As of", "Forecast for") against the mockup.
- **2026-09-26, Stage 1 on the server.** Deployed `fifteen-minute-cycle` (worker recreated with `TEMPLATE_ID=42180`,
  `flood_extent_step` created and backfilled from the newest 3 runs, map backend and frontend images rebuilt from
  the branch). Ran `flood_forecast_consecutive_state_test` (`manual__2026-09-25T17:35:10`): all 14 tasks succeeded,
  8 depth steps per event at 900 s. Event 1 timings after trigger: 3Di 2:37, download 0:08, depth for 8 tifs 6:40
  (done at +9:26), tiles for steps 1 and 2 2:40 (published at +11:33 and +12:11), raster load 2:22, flood on roads
  1:43 (done at +13:36). Event 2's tiles took 5:05 because they overlapped the raster load and flood on roads.
  Event 2 logged `[Hotstart, exact] ... offset 0 min`. Found: depth file times drift by seconds (`01:15:02`), fixed by
  rounding to the minute (`7f87538`). `GET /flood/timesteps` and `POST /flood/forecast` answer on real data (13
  columns in 1.5 s for a 5-point route). The map legend reads "As of 01:10" and the chart renders. Not measured: two
  overlapping runs (Stage 2, needs `flood_mapping_full` with `FLOOD_TEST_RAIN_MM_HR`).
- **2026-09-26.** Motorbike profile icon fixed (`7290847`) and the chart label moved into a right-hand gutter
  (`a107c78`), see [[motorbike-profile-icon-wrong]].
- **2026-09-28, Stage 2 test.** Ran two genuinely overlapping runs under `FLOOD_TEST_RAIN_MM_HR=50`
  (risk 3, previously unmeasured). Both runs succeeded, but risk 3's contention is real and worse
  than expected: not same-run task contention, but a new run's simulation-trigger chain queuing
  behind the previous run's entire downstream pipeline, because no Airflow pool separates them.
  Runs under overlap took 20 to 35 minutes instead of ~14, and the delay compounded across
  successive overlapping runs. New blocker:
  [[flood-mapping-full-worker-concurrency-serializes-runs]]. Not yet fixed; `flood_mapping_full`
  is paused again.
