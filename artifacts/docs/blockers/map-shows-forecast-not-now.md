---
date_open: 2026-09-25
date_closed: 
type: blocker
status: open
severity: P2
subsystem: floodmap-frontend
approaches_tried: 0
approaches_remaining: 4
tags: [blocker, frontend, forecast, routing, product-decision]
related: ["[[frontend-polish]]", "[[route-forecast-query]]", "[[depth-forecast-chart]]", "[[3di-simulation-orchestration]]", "[[flood-routing-mockup-frontend-gap]]", "[[decision-log]]"]
last_updated: 2026-09-25
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

- **No usable t0 raster exists.** `scripts/calculate_depth.py:208` skips step 0, which is 3Di's placeholder
  record with nodata for most or all cells. The first real output is one output interval after the trigger,
  30 minutes in the observed run.
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

None yet.

## Decision and explanation

Pending. The user wants to brainstorm. Candidate options, none tried:

| Option | What the map shows | Effort | Benefit | Cost and risk |
| --- | --- | --- | --- | --- |
| A. Keep the behavior | The nearest timestep, up to 30 minutes ahead | none | Matches the PRD | The "Updated" label stays misleading |
| B. Relabel | Same map, honest label ("Forecast for 21:40, in 17 min") | S | Removes the confusion, frontend only | Still shows a forecast |
| C. Never show the future | The latest step at or before now | M | Never shows a future tile | Just after a run starts, no such step exists, so the map is empty or falls back to the previous run. Merging runs brings back the cross-run inconsistency |
| D. A real t0 | A true state at now | L | Exactly what the user wants | A new calculation. Either a raster from the initial water levels, or a back-cast from the saved state with observed rain. Feasibility unknown |

Shortening the output interval (30 to 5 minutes) is not an option: it gives six times the rasters, and a run
already takes about 28 minutes.

**Safety trade-off.** Showing only now can under-warn: water that rises in 30 minutes is missing from the map,
and routing could send someone down a road that floods before they arrive. Splitting "now" (map) from
"forecast" (routing and histogram) is sound, but it needs the route-forecast query and the chart first, and
time-aware routing.

Recommendation so far (not a decision): do B after the current test, build the route-forecast query and the
chart, and run a short spike on D.

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
