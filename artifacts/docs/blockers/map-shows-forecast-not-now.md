---
date_open: 2026-09-25
date_closed: 
type: blocker
status: monitoring
severity: P2
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 1
tags: [blocker, frontend, forecast, routing, product-decision]
related: ["[[frontend-polish]]", "[[route-forecast-query]]", "[[depth-forecast-chart]]", "[[3di-simulation-orchestration]]", "[[flood-routing-mockup-frontend-gap]]", "[[decision-log]]", "[[five-minute-tile-freshness]]", "[[carried-over-backlog]]"]
last_updated: 2026-10-02
---

# The map shows a forecast timestep, not the situation now

## Description

The frontend map, the "Updated" line, and routing show the timestep closest to now. Every timestep is a
simulated forecast, so at most times the map shows a moment that has not happened yet.

The user saw this during the manual test on 2026-09-25. At 21:22 local, the legend read "Updated 25/09/2026
21:40" and the map showed the 21:40 flood tiles. The test DAG run started at 21:09:53. Its first output step
comes 30 minutes later, so the timesteps are 21:40, 22:10, and so on. No timestep exists at or before 21:22,
and `reanchorTimestepIndex` in `FloodStore.ts` picks the closest one, which is the earliest. Production
behaves the same way: a live screenshot on 2026-09-24 showed "Updated 24/09/2026 17:36" at about 16:38.

The user's position: the map should show the exact situation at t0, that is now, and the forecast belongs in
routing and in the flood histogram. This blocker records the facts, the options, and what is unknown, so the
team can decide together.

## Why this matters

For a flood-safety app, the map is what people trust first. A label that says "Updated 21:40" at 21:22 reads
as data from the future. The choice also decides how routing and the route histogram must behave, because the
user's plan splits "now" (map) from "forecast" (routing and histogram).

## What the code and the vault say

- **No usable t0 raster exists.** `scripts/calculate_depth.py:211` skips step 0, which is 3Di's placeholder
  record with nodata for most or all cells. The first real output is one output interval after the trigger,
  30 minutes in the observed run. This matters less than first thought: during rain, runs overlap, so an
  earlier run already has a step at or before now.
- **Routing sees one moment.** The frontend interceptor sends the selected timestep's `valid_time` and run to
  `POST /route`. Routing is not time-aware along the route, and it uses the same timestep as the map.
- **The histogram is not built.** [[route-forecast-query]] and [[depth-forecast-chart]] are both `draft` and not
  started. So the forecast is not yet factored into a route or a histogram, which the user's plan assumes.
- **The design defines now as the nearest timestep.** The PRD [[flood-routing-mockup-frontend-gap]] says
  "Water depth now" is read at "the nearest available flood timestep", and the histogram highlights a "Now"
  column. The current behavior matches that spec. Only the "Updated" label is misleading, because it shows
  the timestep's time, not when the data was produced (the timesteps list carries only `valid_time` and `run`).
- **One run at a time.** `GET /flood/timesteps` lists the newest single run only (a deliberate fix against
  mixing runs). Right after a run starts, the newest run has no step at or before now.

## Approaches tried

The 15-minute cycle design below is built and on main, see the 2026-09-26 and 2026-09-29 status entries.

## Decision and explanation

Proposed design, agreed in the brainstorm on 2026-09-25 and waiting for the user's approval in the
[[decision-log]]. It takes option C (below) and changes the simulation cycle so option C always has a tile.
Option D is not needed: overlapping runs already cover now.

### Proposed design: a 15-minute clock cycle with the map fed by step 1 of each run

**Cycle.** A run starts on the clock every 15 minutes, at tₖ = :00, :15, :30, :45. The rain gate still decides
whether a run happens. Each run:

- sets the 3Di `start_datetime` to tₖ, not to the unrounded time of the rain check;
- simulates 2 hours with an output interval of 900 s, so 8 depth steps land on the shared 15-minute grid
  (tₖ+15 to tₖ+120; step 0 stays dropped);
- saves the state at 900 s (= tₖ₊₁), which the next run hotstarts from, and at 1800 s as a backup if a slot is
  missed. This replaces the 1800 s fix in [[hotstart-state-saved-at-end-of-run]]: the save point equals the
  cycle length, so the state chain has no offset;
- keeps running until no rain is forecast and the deepest water is below 5 cm (not built today; runs stop when
  the rain check sees no rain).

**What each run produces.**

| Output | Steps | Used by |
| --- | --- | --- |
| Depth tif | all 8 | everything below |
| Raster load (`flood_depth_raster_tile`) | all 8 | point depth and the histogram |
| Flood on roads (`flood_road_values`) | all 8 | routing |
| Map tiles and `flood_extent_polygon` | steps 1 and 2 only | the map |

Only step 1 of a run is ever shown as now. Run k's step 2 (tₖ+30) is also run k+1's step 1, and run k+1
publishes it at about tₖ+26, before tₖ+30 arrives. Steps 3 to 8 become now only after two newer runs have
replaced them. Step 2 is built as a backup: if run k+1 is late or fails, run k's tile for the same time is
already published.

**Map rule.** The map shows the tile at `floor(now, 15 min)`, taken from the newest run that has published
that time. It is 0 to 15 minutes old and never in the future. `GET /flood/timesteps` changes from "the newest
run's steps" to "for each time, the newest run that published it". The frontend picks the latest time at or
before now, never the nearest.

**A "published" flag per (run, time).** It is set after the tiles and polygon rows of that step are fully
uploaded, so the map never loads a half-written step.

**Timing, from the real run.** `manual__2026-09-25T14:09:53` of `flood_forecast_consecutive_state_test`
(event 1: 20 mm/h, 4 steps at 30-minute output):

| Task | Duration | Done, after trigger |
| --- | --- | --- |
| Trigger (3Di simulates the full 2 h) | 2:36 | +2:36 |
| Download | 0:09 | +2:46 |
| Depth, 4 tifs on 8 processes | 4:49 | +7:35 |
| Raster load | 1:10 | +8:45 |
| Flood on roads | 0:43 | +9:29 |
| Tiles, 4 steps, 2 workers | 7:51 | +15:31 |

Event 2 (5 mm/h): depth 4:46, tiles 3:50. Tiling takes about 3:55 per step at 20 mm/h and about 1:55 at
5 mm/h: it grows with the wet area, so heavy storms are the slow case.

Expected cycle, heavy rain, 8 steps, tiles for steps 1 and 2:

| After tₖ | Event |
| --- | --- |
| +2:45 | Download done |
| +7:35 | Depth done for all 8 steps, assuming 8 tifs take as long as 4 (each tif runs on its own process) |
| +11:30 | Tiles for tₖ+15 and tₖ+30 published, one round of 2 workers |
| +11 to +12 | Raster load and flood on roads done for all 8 steps |
| +15 | Tile tₖ+15 becomes now. Margin about 3 minutes. The next run triggers; the CPU has been idle since about +12 |

**Risks to measure.**

1. Depth for 8 tifs. The estimate assumes it stays near 4:50 on 8 processes. If memory limits it and it takes
   8 to 10 minutes, the heavy-rain margin goes negative. Fallback: a 30-minute cycle with the same design.
2. Storms heavier than 20 mm/h make tiling slower, which shrinks the margin.
3. Tiles, raster load, and flood on roads overlapped in the observed run. Their contention at 8 steps is not
   measured.

**First step.** A test run of `flood_forecast_consecutive_state_test` with a 900 s output interval, to
measure depth and the rest of the pipeline on 8 steps.

**Out of scope here.** Routing that uses the arrival time on each road is [[routing-not-time-aware]]. The
back-cast with observed rain (option D) can come later, once Tomorrow.io's past-rain data is confirmed.

### Options considered

The options below were the brainstorm's starting point:

| Option | What the map shows | Effort | Benefit | Cost and risk |
| --- | --- | --- | --- | --- |
| A. Keep the behavior | The nearest timestep, up to 30 minutes ahead | none | Matches the PRD | The "Updated" label stays misleading |
| B. Relabel | Same map, honest label ("Forecast for 21:40, in 17 min") | S | Removes the confusion, frontend only | Still shows a forecast |
| C. Never show the future | The latest step at or before now, across runs | M | Never shows a future tile | With a fast run cycle (observed ~8 min), the newest run alone almost never has a step at or before now, so this needs a cross-run query, not just the newest run. `list_timesteps` returns one run only today; this needs a new query. Brings back the cross-run consistency question, though the worked timeline shows the picked tile stays fresh (minutes old, not tens of minutes) |
| D. A real t0 | A true state at now | L | Exactly what the user wants | A new calculation. Either a raster from the initial water levels, or a back-cast from the saved state with observed rain. Feasibility unknown |

Shortening the output interval to 5 minutes is not an option: it gives six times the rasters. 15 minutes is
the proposed interval above, and it matches Tomorrow.io's 15-minute rain steps.

**Safety trade-off.** Showing only now can under-warn: water that rises in 30 minutes is missing from the map,
and routing could send someone down a road that floods before they arrive. Splitting "now" (map) from
"forecast" (routing and histogram) is sound, but it needs the route-forecast query and the chart first, and
time-aware routing.

The first recommendation (do B, build the route-forecast query and the chart, and spike D) is replaced by the
proposed design above.

## Questions for the brainstorm

1. Which "now" do we mean: a modelled state at t0, or the nearest step with an honest label?
2. Should routing use now, the forecast, or the worst depth over the trip? The histogram alone does not change
   which route is chosen.
3. Can the initial water levels (the state a run starts from) produce a depth raster? What does the
   `initial_wl` pipeline already hold?
4. Is a back-cast (start the simulation 30 to 60 minutes earlier with observed rain) affordable, and does
   Tomorrow.io give past rain?
5. Does the map need a true "updated at" time, and where would the backend get it?

## Concerns

Any option that changes what the map shows also changes the "Updated" line story in [[frontend-polish]]
(Story 2, `Done`), so its details and evidence need an update.

## Related topics

- [[frontend-polish]], Story 2
- [[route-forecast-query]] and [[depth-forecast-chart]]
- [[3di-simulation-orchestration]], the `calculate_depth` step 0 note
- [[decision-log]], open decisions

## Status history

- **2026-09-25, open.** Logged at the user's request after the two-event test showed "Updated 21:40" at 21:22.
  Facts checked in `calculate_depth.py`, `FloodStore.ts`, and the PRD. Waiting for the brainstorm.
- **2026-09-25, open.** Brainstorm, part 1. The user's model: runs start at the forecast window start and
  overlap during rain, so an earlier run nearly always has a tile at or before now, and no separate t0 is
  needed (option D is not required). A worked timeline, assuming 28 minutes per run: `list_timesteps` offers
  only the newest run, so the map moves to a future tile (at X+48 it picks X+60 over X+30). In the 2 minutes
  after each run publishes, the newest run has no tile at or before now, while the previous run does. Split
  out: [[hotstart-state-saved-at-end-of-run]] and [[routing-not-time-aware]]. The code has no rule that stops
  runs when depth falls below 5 cm. Runs stop only when the rain check sees no rain. Still open: the rule for
  choosing the now tile, and whether to mix runs.
- **2026-09-25, open.** Brainstorm, part 2. Corrected the run duration with real evidence: the user pointed
  to `manual__2026-09-25T14:09:53`, whose tiles were already published by about 21:17, roughly 8 minutes
  after the 21:09:53 trigger, not the ~28 minutes assumed in part 1 (that number came from a "run already
  takes about 28 minutes" line elsewhere in this doc, of uncertain meaning, not a measured DAG wall-clock
  time). Redid the timeline at 8 minutes per run. Result reverses part 1's read: with a fast cycle, the
  newest run's own first tile is always in the future when it publishes (30-minute step minus ~8-minute
  cycle time leaves a ~22-minute gap), and the newest run changes every 8 minutes. So "the newest run's tile
  at or before now" is empty almost always, not just for 2 minutes; a usable now tile exists only by looking
  across runs. Looking across all runs, the now tile is consistently fresh: 0 to about 7 minutes old in the
  worked example, far better than part 1's 14-to-27-minute estimate. This also changes
  [[hotstart-state-saved-at-end-of-run]]'s numbers (the 8-minute cycle makes that offset worse, not better).
  Conclusion so far: any fix needs to search across runs for the latest tile at or before now, not read the
  newest run only. `D` (wall-clock time per run) is one data point, not a measured average, and needs more
  runs to pin down; the qualitative conclusion (cross-run search is required, not optional) does not depend
  on the exact value.
- **2026-09-25, open.** Proposed design written up in Decision and explanation: a 15-minute clock cycle,
  output every 900 s, state saved at 900 s, map tiles for steps 1 and 2 only, and a cross-run "latest tile at
  or before now" rule. Timings come from the task table of `manual__2026-09-25T14:09:53` (screenshot from the
  user). They correct part 2's "8 minutes": the depth tifs were done at +7:35, but the map tiles only at
  +15:31. The pipeline in use is `flood_forecast_consecutive_state_test` on `stage-b`; the GeoJSON chain is
  retired. Waiting for the user's approval and a test run with 8 steps.
- **2026-09-26, open.** Code for the proposed design built on the local branch `fifteen-minute-cycle`, see
  [[fifteen-minute-cycle-tiles-and-histogram]]: tiles for steps 1 and 2 only, a published flag per step, the cross-run
  timesteps list, the map's latest-at-or-before-now pick, a 15-minute DAG schedule, and a raster-based depth histogram.
  Not deployed. Still needed before the blocker can close: the user's new 3Di template and `create_simulation.py`
  changes, and the test run with 8 steps that measures the three risks above.
- **2026-09-26, open.** First server test of the design, `manual__2026-09-25T17:35:10` of
  `flood_forecast_consecutive_state_test` on template 42180 (8 steps at 900 s). Depth for 8 tifs took 6:40, against 4:49
  for 4 (risk 1: about 1.4 times, under the 8 to 10 minute limit). Tiles for steps 1 and 2 published at +11:33 and +12:11
  after the trigger, so step 1 has about 3.5 minutes of margin before it becomes now. Flood on roads finished at +13:36, about
  1.4 minutes before that. Event 2's tiles took 5:05 against 2:40 for event 1 because they overlapped the raster load and
  flood on roads (risk 3, contention inside one run). Two overlapping runs are not measured yet. The map now shows the latest
  step at or before now. Found and fixed: depth times drifted by seconds off the grid (`7f87538`).
- **2026-09-28, open.** Ran the Stage 2 test on `flood_mapping_full` itself (its real 15-minute schedule, not the manual
  state-test DAG), under `FLOOD_TEST_RAIN_MM_HR=50`. Two runs genuinely overlapped and both succeeded, but risk 3's margin
  is gone under overlap: tiles published around +20 minutes instead of +11:30, already past the +15:00 point step 1 is
  supposed to become now, and the delay compounded on further overlapping runs (one run took 35:24). Root cause is not
  same-run task contention as risk 3 assumed, but a new run's simulation trigger queuing behind the previous run's entire
  downstream pipeline, since no Airflow pool separates them from the heavy tasks on the 2-slot worker. New blocker:
  [[flood-mapping-full-worker-concurrency-serializes-runs]]. The proposed design's margin numbers above needed
  re-verifying once that blocker had a fix (done on 2026-09-29, see the last entry). `flood_mapping_full` is paused again and the test rain variable is unset.
- **2026-09-29, monitoring.** [[flood-mapping-full-worker-concurrency-serializes-runs]] is resolved (2026-09-28). Four
  consecutive real runs after the deploy took a flat 17 to 18 minutes, where the old configuration gave 17, 32, 37,
  and 25. The margins above are re-measured. Each run's own critical path (trigger about 3.5 minutes, depth about 7,
  raster load about 2.3, tile build about 6) adds to slightly more than the 15-minute cycle, so a step's tile
  publishes 1.5 to 3 minutes after its target moment, not the 3 minutes before it that the design expected. The
  page's remaining gap is that latency, tracked in [[five-minute-tile-freshness]]. Contention between runs is no
  longer the cause. Status is `monitoring` until the latency work lands or the user accepts the delay.
- **2026-09-29, monitoring.** [[carried-over-backlog]] Story 5 decided: the map's "now" behavior (this page's
  Option C, already built) is accepted as final. The 1.5 to 3 minute publish delay is not accepted as final;
  the user chose to narrow it via [[five-minute-tile-freshness]]'s option D, scheduled as Story 6 in Sprint 4.
  Stays `monitoring` until that work lands and a fresh measurement shows real margin, or the delay is
  re-accepted.
- **2026-10-02, monitoring.** [[carried-over-backlog]] Story 6 (`US-037`) is `Done`. After the depth inputs moved to local disk, the tile dissolve ran per band, and a restart began from the initial water level, four consecutive on-time runs published step 1 with margins of +1.9 to +4.1 minutes. The margin shrinks about 0.6 minutes per run as the 50 mm/h test storm grows, so this holds for the first hour of a storm. Still `monitoring` until a longer or real-rain run shows the margin holds.
