---
date_open: 2026-09-23
date_closed: 2026-09-28
type: blocker
status: resolved
severity: P2
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, routing, frontend, flood]
related: ["[[graphhopper-backend]]", "[[truck-routing-profile]]", "[[frontend-polish]]", "[[graphhopper-vehicle-profile-rejection]]"]
last_updated: 2026-09-28
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

### Approach 1

Candidate 1 from Decision and explanation: stop sending `vehicle_type` from the interceptor
(`main` at `18d1c42`). Built and deployed to the server (`docker --context remote-server compose
build flood-routing-frontend` from the Mac, then recreated on the server with `--no-deps`; no
issue with the established build/deploy split for this repo). The webpack build itself compiled
clean, which also confirms the TypeScript change type-checks.

Verified mechanism, not yet a live route-distance spot-check. Grepped the deployed bundle for
`vehicle_type`: absent (`grep -c` returns 0 in every `.js` asset), with `valid_time` (an untouched
sibling field on the same request object) present as a positive control, ruling out a bad glob or
grep failure. Attempted a live before/after route comparison (car profile forced to
`vehicle_type=motorbike` versus car profile with no `vehicle_type`, same points, same valid_time)
at the codebase's own `DEFAULT_ORIGIN`/`DEFAULT_DESTINATION` test points
(`flood_utils.py:16-17`). Both calls returned `ConnectionNotFoundException`, and so did every
vehicle profile tried (motorbike, car, foot) at those points, while a plain request with no flood
fields at all routed successfully (772.9 m). Conclusion: the flood custom model is genuinely being
applied and is genuinely vehicle-sensitive at the code level (a plain route succeeds, a flood-aware
one doesn't), but the sustained `FLOOD_TEST_RAIN_MM_HR=50` test rain has now flooded this specific
area past even foot's 40 cm threshold, so no vehicle type can currently demonstrate a route
*difference* there. Redo the spot-check at a location or moment with moderate (20 to 40 cm) water,
not deep flooding.

### Spot-check, 2026-09-28

Unpaused `flood_mapping_full` (still under `FLOOD_TEST_RAIN_MM_HR=50`) and let a full cycle complete
(`scheduled__2026-09-28T13:15:00+00:00`, success in 16 minutes). Queried the fresh
`flood_road_values` (`file_id=30`) for a road segment sitting between two vehicle thresholds instead
of reusing the deeply-flooded `DEFAULT_ORIGIN`/`DEFAULT_DESTINATION` points: `way/776941610#3`, "Cầu
vượt đường sắt Đại Việt 2" (a railway overpass), depth 0.202 m. That is above motorbike's 0.20 m
limit but below car's 0.30 m, truck's 0.35 m, and foot's 0.40 m.

`derive_areas` (`flood_areas.py`) confirmed the difference before routing: `GET /flood/areas` for
the same `valid_time` and run returned 814 avoid-polygon features for `vehicle_type=motorbike` versus
651 for `vehicle_type=car`, the first live evidence that the two vehicle types now get genuinely
different avoid-zones (previously identical, since every request forced `motorbike`).

Then `POST /route` for the same origin/destination pair straddling the overpass
(`[105.73607,21.00634]` to `[105.74080,21.00469]`), one call per profile, no other change:

| Profile | Threshold | Result |
| --- | --- | --- |
| motorbike | 20 cm | `ConnectionNotFoundException` (blocked, the overpass's 20.2 cm exceeds its limit) |
| car | 30 cm | 932 m, 67 s |
| truck | 35 cm | 932 m, 75 s |
| foot | 40 cm | 928 m, 682 s |

Motorbike alone is blocked at a depth that every other vehicle's own limit tolerates, the exact
mismatch this blocker was about, now gone. This is the route-distance difference Approach 1's earlier
attempt could not produce.

## Decision and explanation

Candidate 1, done and spot-checked (see Approaches tried). Two original candidates, for the record:

1. Stop sending `vehicle_type` from the interceptor, so `server.py:214` falls back to the request's
   `profile`. The profile names `motorbike`, `car`, `truck`, and `foot` match `VEHICLE_PROFILES`
   one to one. This is the smallest change, and it touches only the interceptor.
2. Make `vehicleType` in `FloodStore` follow the selected routing profile by dispatching
   `SelectFloodVehicle` when `SetVehicleProfile` fires. `useFloodState.ts` then re-issues the route
   on each profile change, at the cost of a second store reacting to the first and one extra
   request per switch.

## Concerns

Changing the limits changes which roads routes avoid, so results for car, foot, and truck differ
from what was demoed before the fix. Spot-checked (see Approach 1); no longer a concern. The
per-mode travel times fire one request per profile, so each request must carry its own profile's
limit, which favors the first candidate (deployed).

## Related topics

- [[graphhopper-backend]], Vehicle thresholds
- [[truck-routing-profile]], Known risk
- [[frontend-polish]], Story 1

## Status history

- **2026-09-23, open.** Logged at the user's request after a delegate building per-mode travel times
  reported that every mode was routed with motorbike limits. Confirmed against `FloodStore.ts` and
  `server.py`. Root cause: `SelectFloodVehicle` is never dispatched.
- **2026-09-28, monitoring.** Fixed and deployed (`18d1c42`): the interceptor no longer sends
  `vehicle_type`, so `server.py` falls back to each request's own `profile`. Mechanism verified
  live (bundle no longer contains the field, TypeScript compiled clean). A live route-distance
  spot-check was attempted but inconclusive: the test area is currently flooded past every
  vehicle's threshold under sustained `FLOOD_TEST_RAIN_MM_HR=50`, so no profile can show a
  difference there right now. Revisit once conditions allow an actual before/after route
  comparison.
- **2026-09-28, resolved.** Redid the spot-check against a moderately-flooded segment (a railway
  overpass at 20.2 cm) instead of the too-deep test points: motorbike alone is blocked
  (`ConnectionNotFoundException`), car/truck/foot all route through at 928-932 m. `GET /flood/areas`
  also confirmed motorbike and car now get different avoid-polygon counts (814 vs. 651) for the same
  `valid_time`. The vehicle-specific mismatch is gone.
