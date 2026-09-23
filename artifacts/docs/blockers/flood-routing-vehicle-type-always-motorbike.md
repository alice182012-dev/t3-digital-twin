---
date_open: 2026-09-23
date_closed: 
type: blocker
status: open
severity: P2
subsystem: floodmap-frontend
approaches_tried: 0
approaches_remaining: 2
tags: [blocker, routing, frontend, flood]
related: ["[[graphhopper-backend]]", "[[truck-routing-profile]]", "[[frontend-polish]]", "[[graphhopper-vehicle-profile-rejection]]"]
last_updated: 2026-09-23
---

# Flood routing uses motorbike limits for every vehicle

## Description

Every route request sends `vehicle_type=motorbike` to `floodmap-backend`, whatever routing profile
the user selected. A car, foot, or truck route is therefore planned around the motorbike depth limit
(20 cm) instead of its own limit.

`floodmap/graphhopper-maps/src/floodmap/FloodStore.ts` causes this in two places. The initial state
sets `vehicleType: 'motorbike'` (line 125). The fetch interceptor then writes
`body.vehicle_type = state.vehicleType` into every flood-aware `POST /route` body (line 205).
`SelectFloodVehicle` is defined and handled in the same file (lines 56 and 145), but nothing
dispatches it, so `vehicleType` never changes.

`floodmap/graphhopper-flood-road/backend/server.py:214` reads `vehicle_type` first and falls back to
the request's `profile` only when `vehicle_type` is absent. The interceptor's value always wins, so
the fallback never runs. `useFloodState.ts` re-issues the current route when `vehicleType` changes,
but nothing changes it.

## Why this matters

`flood_utils.py`'s `VEHICLE_PROFILES` sets the impassable depth per vehicle: motorbike 20 cm, car
30 cm, truck 35 cm, foot 40 cm. Motorbike is the strictest, so the error errs on the cautious side.
No route crosses water that is too deep for its vehicle. A car, truck, or walking route can instead
detour around a road it could pass, or return "No safe route available" when a passable route
exists.

The mismatch affects the selected route today. It also affects the per-mode travel times from
[[frontend-polish]]'s Story 1, which show four modes routed with one limit, and the truck profile
in [[truck-routing-profile]], which would ship with a limit 15 cm stricter than its own.

## Approaches tried

None yet.

## Decision and explanation

Pending. Two candidate fixes, neither tried.

1. Stop sending `vehicle_type` from the interceptor, so `server.py:214` falls back to the request's
   `profile`. The profile names `motorbike`, `car`, `truck`, and `foot` match `VEHICLE_PROFILES`
   one to one. This is the smallest change, and it touches only the interceptor.
2. Make `vehicleType` in `FloodStore` follow the selected routing profile by dispatching
   `SelectFloodVehicle` when `SetVehicleProfile` fires. `useFloodState.ts` then re-issues the route
   on each profile change, at the cost of a second store reacting to the first and one extra
   request per switch.

## Concerns

Changing the limits changes which roads routes avoid, so results for car, foot, and truck will
differ from what has been demoed. Spot-check a known flooded road before and after the fix. The
per-mode travel times fire one request per profile, so each request must carry its own profile's
limit, which favors the first candidate.

## Related topics

- [[graphhopper-backend]], Vehicle thresholds
- [[truck-routing-profile]], Known risk
- [[frontend-polish]], Story 1

## Status history

- **2026-09-23, open.** Logged at the user's request after a delegate building per-mode travel times
  reported that every mode was routed with motorbike limits. Confirmed against `FloodStore.ts` and
  `server.py`. Root cause: `SelectFloodVehicle` is never dispatched.
