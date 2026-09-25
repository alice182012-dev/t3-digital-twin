---
date_open: 2026-09-25
date_closed: 
type: blocker
status: open
severity: P1
subsystem: floodmap-backend
approaches_tried: 0
approaches_remaining: 3
tags: [blocker, routing, forecast, graphhopper, safety]
related: ["[[map-shows-forecast-not-now]]", "[[route-forecast-query]]", "[[depth-forecast-chart]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-25
---

# Routing checks each road at one moment, not at the time the traveller reaches it

## Description

A route request carries one timestep. The frontend interceptor in `FloodStore.ts`
(`installRoutingInterceptor`) adds the selected `valid_time` and `run` to `POST /route`.
`_handle_route` in `floodmap/graphhopper-flood-road/backend/server.py` builds one `custom_model` from the
flood areas at that timestep (`cached_areas(valid_time, ...)`), and GraphHopper routes with it. Every road
on the route is judged at the same moment.

The user's example: someone leaves now on a 20-minute route. A road reached at minute 15 is dry now but
flooded by minute 15. Today's routing sends them down it.

## Why this matters

This is a safety gap. [[map-shows-forecast-not-now]] moves the map to "now", so the forecast has to show up
somewhere. Routing is where it changes what people do.

## Candidate approaches

None tried.

| Option | How | Effort | Cost and risk |
| --- | --- | --- | --- |
| A. Worst case over the trip | Build the `custom_model` from the deepest water on each road across all timesteps from now to now plus a trip-time bound (for example 1 hour). | S to M | Simple and safe. Too cautious on long trips: it avoids a road that floods after the traveller has passed it. |
| B. Check the arrival time, then re-route | Route with now. Compute the arrival time on each road from GraphHopper's time data. Look up the depth at the timestep for each arrival time. If a road on the route is impassable at arrival, block it and route again. Repeat until the route holds. | M to L | Several GraphHopper calls per route. Needs a limit on repeats. |
| C. Time-dependent routing | Edge weights that depend on arrival time, inside the routing engine. | L | A GraphHopper `custom_model` has no time dimension. This needs engine changes or another engine. |

Timesteps are 30 minutes apart, so any option has to decide how to map an arrival time to a timestep: the
step at or before it, the nearest step, or the worse of the two around it.

## Questions

1. Which option, or A first and B later?
2. What upper bound on trip time should option A use?
3. How should the answer show in the UI? For example, "This road floods at 21:40" on the route.

## Related topics

- [[map-shows-forecast-not-now]]
- [[route-forecast-query]] and [[depth-forecast-chart]]
- [[graphhopper-backend]]

## Status history

- **2026-09-25, open.** Logged at the user's request while working on [[map-shows-forecast-not-now]].
  Routing should use the time the traveller reaches each road.
