---
date_captured: 2026-09-28
type: idea
status: exploring
source: conversation with the user, 2026-09-28, after observing the frontend serve a 14:30 tile at 14:37
subsystem: airflow-pipeline, floodmap-backend, floodmap-frontend
tags: [idea, freshness, tiles, fifteen-minute-cycle, worker-concurrency]
related: ["[[fifteen-minute-cycle-tiles-and-histogram]]", "[[map-shows-forecast-not-now]]", "[[flood-mapping-full-worker-concurrency-serializes-runs]]", "[[hotstart-state-saved-at-end-of-run]]"]
---

# Serve the map's "now" tile within 5 minutes of real time

## Idea

Cut the gap between real time and the timestamp of the tile the map shows from the current
0-to-15-minute range down to under 5 minutes, whatever combination of a finer simulation grid,
staggered runs, or query-time interpolation gets there.

## Why it might be worth it

Observed live on 2026-09-28: at 14:37 local, the frontend served the tile valid at 14:30, seven
minutes stale. That's not a bug in the sense of something broken: `GET /flood/timesteps` confirmed
14:30 was genuinely the newest published step at that moment, and the current design
([[fifteen-minute-cycle-tiles-and-histogram]]) publishes tiles only on the 15-minute grid (3Di's
output interval is 900 s), so a tile is "now" for up to 15 minutes before the next one lands. The
user's stated target is under 5 minutes, which the current design cannot guarantee even in the
best case, only in the best case of its own 0-to-15-minute range.

Two separate problems compound the gap actually observed, not just the structural one:

1. **Structural.** By design, a fresh tile stays "now" for up to 15 minutes
   ([[map-shows-forecast-not-now]]: "It is 0 to 15 minutes old and never in the future"). Even a
   perfectly-running pipeline averages 7.5 minutes of staleness and peaks at just under 15.
2. **Pipeline latency, worse under overlap.** The run that should have refreshed the tile before it
   went stale was itself still building tiles well past when it needed to. On the same day,
   [[flood-mapping-full-worker-concurrency-serializes-runs]] found the pipeline's heavy tasks
   (`3_calculate_depth`, `9_build_flood_tiles`, `9b_load_depth_raster`, `flood_on_roads`) share only
   `AIRFLOW__CELERY__WORKER_CONCURRENCY=2` worker slots across every concurrently active run. A
   dedicated pool fixed the simulation-trigger chain's scheduling priority, but not this: under
   three overlapping runs (observed the same day, `FLOOD_TEST_RAIN_MM_HR=50`), one run's tile-build
   task was still running more than five minutes after the moment its output was supposed to
   already be "now".

## Candidate approaches

| Approach | What changes | Cost | Gets to <5 min? |
| --- | --- | --- | --- |
| A. Shorten 3Di's own output interval to 5 minutes | `UPDATE_INTERVAL` drops from 900 s to 300 s; each run computes 24 depth steps over its 2-hour window instead of 8 | Roughly 3x the depth tifs per run, so roughly 3x the `calculate_depth`/raster-load/tile-build work per run. The fifteen-minute-cycle plan already rejected a 5-minute interval on cost grounds when comparing against the older 30-minute baseline ("gives six times the rasters"). The per-run pipeline is already tight against its 15-minute budget at 8 steps (Stage 1 baseline: about 11:30 to publish step 1, out of a 15-minute window); 3x the work per run risks blowing that budget before the run even finishes, let alone with margin | Yes, directly, if the per-run pipeline can still finish in time |
| B. Stagger three 15-minute-cycle run streams 5 minutes apart | Each run keeps its own 900 s output interval and 8-step cost (no change to A's problem), but three interleaved streams start at `:00/:15/:30/:45`, `:05/:20/:35/:50`, and `:10/:25/:40/:55`, so the union of their step-1 tiles lands on a 5-minute grid | See "B in detail" below. Triples how often our own downstream pipeline runs, hitting the same worker-concurrency bottleneck at 3x the load, and cuts 3Di's own turnaround margin from about 12 minutes to about 2 | Yes, if paired with a real concurrency fix and 3Di reliably holds its ~3-minute turnaround; no on today's worker, and fragile even after that fix |
| C. Interpolate or extrapolate depth at query time between the two nearest published steps | `GET /flood/points` and the route-forecast query compute an estimated value between (or ahead of) the last two real steps, instead of only ever returning the literal last-published raster's value | Cheap: a read-time calculation, no new simulation load. Only covers scalar point and route-forecast queries (the "Water depth now: N cm" popup, per-step and per-point depth figures); does not help the map's own colored flood-extent tile layer, since morphing a polygon layer between two flood states is a materially harder problem than interpolating one number | Partially: yes for point-depth reads, no for the visible map tile |
| D. Fix the worker-concurrency bottleneck harder, keep the 15-minute grid as is | Give the heavy pipeline tasks real added capacity (more worker concurrency, or their own pool sized to actual CPU headroom) so each run's step-1 tile reliably publishes with the design's intended ~3.5-minute margin, even under overlap | Cheapest option on the table; it's also just finishing the fix [[flood-mapping-full-worker-concurrency-serializes-runs]] already started | No on its own: narrows the worst case toward the current design's 0-to-15-minute ceiling, but a tile still ages up to 15 minutes by design |
| E. B plus D together | The direct route to an actual 5-minute grid: interleaved run streams, but only once the pipeline has enough real concurrency to run three streams' worth of heavy tasks without the queuing D is meant to fix | Sum of B's and D's costs. The most expensive option, and the only one on this list that hits the stated target without changing what "now" means (unlike C, which only approximates it) | Yes |

## B in detail

The user pointed out a concrete constraint: 3Di simulations cannot run concurrently, each one
queues. That doesn't rule B out the way it first sounds, but it removes all of B's slack.

**B never asks for concurrent simulations.** Merge the three streams' start times
(`:00/:15/:30/:45`, `:05/:20/:35/:50`, `:10/:25/:40/:55`) and exactly one new simulation starts
every 5 minutes, never two at once. B is compatible with a strict one-at-a-time queue by
construction, not in spite of it.

**Where the queue constraint actually bites: margin, not feasibility.** Today's cadence is one
simulation every 15 minutes, and `1_trigger_simulation`'s measured duration (which includes 3Di's
own queue and processing time, per `monitor_simulation` blocking on it) was consistently about
3 minutes (3:01, 3:11, 3:01 across three observed runs on 2026-09-28). That leaves roughly 12
minutes of slack every cycle, so 3Di's queue is never under real pressure today. Under B, the
cadence drops to one simulation every 5 minutes. If 3Di keeps turning each one around in about
3 minutes, B is fine on paper (3 min < 5 min). But the slack drops from about 12 minutes to about
2. Nothing in `run_forecast_process` retries or backs off if 3Di is running behind (it submits once
via `simulations_from_template` and polls); a single simulation that takes longer than usual
(heavier rain, competing load elsewhere on 3Di's platform, a network hiccup) pushes every stream
behind it later, the same compounding-delay shape already measured on our own worker in
[[flood-mapping-full-worker-concurrency-serializes-runs]], just triggered from the 3Di side instead
of the Airflow side.

**The larger, more certain problem is unrelated to 3Di's queue.** Even if 3Di holds its 3-minute
turnaround perfectly, B triples how often each stream's downstream pipeline runs on our own worker:
`3_calculate_depth`, `9_build_flood_tiles`, `9b_load_depth_raster`, `flood_on_roads`. Those already
take 11 to 20-plus minutes per stream under today's contention, not the 5 minutes B's cadence would
need. That part is entirely [[flood-mapping-full-worker-concurrency-serializes-runs]] again, at 3x
the load, independent of anything 3Di does.

**Net effect:** B is not blocked outright by "no concurrent simulations," since it never needs
concurrent ones. But it's a materially worse bet than it first looked: it spends 3Di's comfortable
12-minute margin down to about 2, on top of still requiring the worker-concurrency fix to survive
3x the downstream load. Both conditions have to hold at once for B to work, and neither is
confirmed today.

## What's already covered

The current 15-minute cycle ([[fifteen-minute-cycle-tiles-and-histogram]]) already reduced staleness
from the old up-to-30-minute nearest-timestep behavior. `tile_steps=2` already gives each run a
one-step backup (run k's own step 2 can cover a slot if run k+1 is late), which softens occasional
misses but doesn't change the grid's own 15-minute spacing. The trigger-chain pool
([[flood-mapping-full-worker-concurrency-serializes-runs]]) already fixed one piece of the latency
picture (the simulation trigger no longer queues behind a previous run's heavy tasks), but not the
heavy tasks' own contention with each other.

## Trigger to revisit

Once [[flood-mapping-full-worker-concurrency-serializes-runs]] is fully resolved (not just the
trigger chain, the heavy-task queuing too) and a fresh overlap test shows runs reliably finishing
with real margin, that's the point to decide between D-only (accept 0-to-15-minute staleness,
averaging 7.5) and E (commit to the added cost of a true 5-minute grid). If <5 minutes turns out to
be a hard product requirement rather than a target to approach, that decision doesn't need to wait
for D; it can be scoped directly as E, since D alone provably cannot satisfy it.

## Status history

- **2026-09-28, exploring.** Captured after observing the frontend serve a 14:30 tile at 14:37 local
  (seven minutes stale) during a live re-test of
  [[flood-mapping-full-worker-concurrency-serializes-runs]]'s fix, with `flood_mapping_full`
  unpaused under `FLOOD_TEST_RAIN_MM_HR=50`. `GET /flood/timesteps` confirmed 14:30 was genuinely
  the newest published step at that moment; the delay traced to the still-open heavy-task
  contention concern on that blocker, compounded by the current design's own 0-to-15-minute
  structural staleness.
- **2026-09-28, exploring.** The user pointed out 3Di simulations must queue, never run
  concurrently. Added "B in detail": B never actually asks for concurrent simulations (it triggers
  one every 5 minutes, staggered, never two at once), so the constraint doesn't rule B out, but it
  cuts 3Di's turnaround margin from about 12 minutes to about 2, with no retry or backoff in
  `run_forecast_process` if 3Di falls behind. B's larger problem is still the same worker-
  concurrency bottleneck, now at 3x the load. Downgraded B's verdict in the comparison table from a
  plain "yes, if paired with a concurrency fix" to "fragile even after that fix."
