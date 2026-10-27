---
date_open: 2026-09-29
date_closed: 2026-09-30
type: blocker
status: resolved
severity: P1
subsystem: floodmap-frontend, floodmap-backend
approaches_tried: 2
approaches_remaining: 0
tags: [blocker, frontend, backend, routing, safety, error-handling]
related: ["[[EP-02-frontend-polish|frontend-polish]]", "[[US-022-truck-routing-profile|truck-routing-profile]]", "[[BL-005-flood-routing-vehicle-type-always-motorbike|flood-routing-vehicle-type-always-motorbike]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-30
---

# A failed route request leaves the previous mode's route on the map

## Description

When the selected mode has no route, the app keeps drawing the route of the mode the user selected
before, and the red error banner has no text.

Found on 2026-09-29 while checking the truck profile ([[US-022-truck-routing-profile|truck-routing-profile]]). The user selected
walking, then car, between the same two points. Both screens showed the same 1 km route, "12 min".
The car request had failed. The screen still showed the walking route under the car icon.

**Reproduction.** Route from `21.014103,105.764718` to `21.014534,105.768982` at flood step
`2026-09-29T15:15:00+07:00` (run `20260929T150000`, under the test rain of 50 mm/h). Select walking,
then car.

| Mode | Depth limit | Backend result |
| ---- | ----------- | -------------- |
| motorbike | 20 cm | `ConnectionNotFoundException` |
| car | 30 cm | `ConnectionNotFoundException` |
| truck | 35 cm | `ConnectionNotFoundException` |
| foot | 40 cm | 1,011 m in 747 s |

Without the flood, every mode routes in 508 m. So the road modes have no connection, and the
walking route is a real 1,011 m detour. The backend answer is correct. The display is wrong.

**Cause 1, stale route.** `floodmap/graphhopper-maps/src/stores/RouteStore.ts` reduces
`RouteRequestSuccess`, `SetSelectedPath`, and the point actions. It has no branch for
`RouteRequestFailed`, so a failed request leaves `routingResult` and `selectedPath` as they were.
`Api.ts` dispatches `RouteRequestFailed` only for the newest request.

**Cause 2, empty banner.** `_handle_route` in `floodmap/graphhopper-flood-road/backend/server.py`
answers a GraphHopper error with `{"error": "<GraphHopper's JSON as text>"}` and status 400.
`Api.ts` (lines 220 to 232) reads `message` and `hints` from the response. It finds neither, builds
an `Error` with no message, and the banner renders empty. The comment on `_handle_route` says
GraphHopper's response is returned as is so `Api.ts` needs no changes. That holds for a success and
not for an error.

The per-mode travel times under the icons fail separately. Each logs a warning and shows no time,
which is acceptable.

## Why this matters

This is a safety gap, in the same class as [[BL-005-flood-routing-vehicle-type-always-motorbike|flood-routing-vehicle-type-always-motorbike]]. A car
driver sees a route on the map that is not a car route. It was planned for a mode that tolerates 40
cm of water and it is labeled for a mode that tolerates 30 cm. The user is also never told that no
car route exists, because the banner is empty.

## Approaches tried

### Approach 1: pass GraphHopper's error through (2026-09-30)

`route_error_payload()` in `server.py` parses GraphHopper's error text. When it is a JSON object with a `message`, the backend sends it unchanged with the original status, so `Api.ts` finds `message` and `hints`. Any other error becomes `{"message": text, "error": text}`. `test_route_error.py` covers the four cases. A local run against a stub GraphHopper returned 400 with "Connection between locations not found" and the hint. The other `/route` error, a GraphHopper that is down, previously also gave an empty banner and now shows its text.

### Approach 2: clear the route on a failed request (2026-09-30)

`RouteStore.ts` returns to its initial state on `RouteRequestFailed`. A new test in `RouteStore.test.ts` dispatches a success and then a failure and expects the initial state. All 208 frontend tests pass.

Result: both are built and tested locally, then deployed and checked on the live UI (see Decision and explanation).

## Candidate approaches

1. **Pass GraphHopper's error through.** In `server.py`, parse the GraphHopper error body and send
   it as is, so the response has `message` and `hints` and the banner reads "Connection between
   locations not found". `test_server.py` asserts `payload["error"]` on other errors, so check
   which of those cover the `/route` proxy before changing the shape. Backend change, S.
2. **Clear the route on a failed request.** In `RouteStore.ts`, reset to the initial state on
   `RouteRequestFailed`, so the map shows no route when the selected mode has none. Frontend change,
   S. Do both. Approach 2 alone leaves an empty banner, and approach 1 alone leaves the stale route.

Open question for the fix: when the selected mode fails, should the app suggest a mode that does
have a route (walking here)? That is a product call and not part of this blocker.

## Decision and explanation

Both approaches shipped together on 2026-09-30 (branch `front-end-according-to-mock-up` at `dc5ed15`, `floodmap-backend` and `flood-routing-frontend` rebuilt on the server). On the live UI, `21.011,105.748` to `21.010,105.750` gives a 760 m walking route. Selecting car draws no route and shows "Connection between locations not found". Selecting walking again returns the route. Screenshots: ![[failed-route-car-no-route-server-check.png|420]] ![[failed-route-walking-returns-server-check.png|420]]. The original pair's run was pruned, so this pair replaced it. Suggesting a mode that has a route stays a product call and is not part of this blocker. The test scenario is in [[EP-02-frontend-polish|frontend-polish]], Story 4.

## Concerns

The reproduction depends on the live flood. The pair stops failing once the water recedes or the
run is pruned (the backend keeps the newest 8 runs). A repeatable test needs a stub backend or a
fixed fixture, not the live server.

## Related topics

- [[EP-02-frontend-polish|frontend-polish]], Story 4
- [[graphhopper-backend]]
- [[US-022-truck-routing-profile|truck-routing-profile]]

## Status history

- **2026-09-29, open.** Logged at the user's request after the walking and car routes looked
  identical. Root causes read in `RouteStore.ts`, `Api.ts`, and `server.py`, and the four-mode
  backend results measured against the live server. No fix attempted.
- **2026-09-29, open.** Scheduled in Sprint 3 of [[SP-01-prd-and-backlog|sprint-plan]] at the user's request. No fix attempted yet.
- **2026-09-30, open.** Both approaches built and tested locally, see Approaches tried. Stays `open` until the fix is deployed and the reproduction pair shows no route and the message on the live UI.
- **2026-09-30, resolved.** Deployed and checked on the live UI, see Decision and explanation.
