---
date_drafted: 2026-09-23
type: user-story
us_id: "US-009"
story_label: "4"
epic: "[[EP-02-frontend-polish]]"
status: Done
priority: P1
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Show no route and a clear message when the selected mode has none"
---

# US-009 Show no route and a clear message when the selected mode has none

As a driver whose mode has no safe route, I want the map to show no route and say why, so I am
not shown another mode's route under my mode's icon.
Given a start and destination where the selected mode has no connection under the current flood
(for example `21.014103,105.764718` to `21.014534,105.768982` at flood step
`2026-09-29T15:15:00+07:00`, where motorbike, car, and truck have none and foot has a 1,011 m
detour), when the user selects walking and then car, then the map draws no route for car and the
panel shows "Connection between locations not found" in the error banner, and the walking route is
not on the map. When the user selects walking again, the 1,011 m route returns.
Test with a stub backend that answers the car request with GraphHopper's
`ConnectionNotFoundException` body and the walking request with a route, since the live flood
changes and the run is pruned after 8 runs. Also check the live server while the flood blocks the
pair. A unit test of `RouteStore` on `RouteRequestFailed` covers the store half.
Priority: P1. Status: Done. Estimate: S. Sprint: 3 (scheduled by the user on 2026-09-29). Dependencies: a backend change to pass GraphHopper's error body through
(`floodmap/graphhopper-flood-road/backend/server.py`, `_handle_route`), tracked in the blocker.
Blocker tracking: [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]]
Later change: the red bar for the no-connection case was dropped on 2026-09-30 (Story 6, US-057). The yellow "No safe route available" box stays.
Evidence: ![[failed-route-car-no-route-server-check.png|420]] ![[failed-route-walking-returns-server-check.png|420]]
Details:
1. What: a failed route request clears the route from the map, and the error banner shows GraphHopper's message.
2. How: `route_error_payload()` in `server.py` sends GraphHopper's error JSON through with `message` and `hints` at the top level. `RouteStore.ts` returns to its initial state on `RouteRequestFailed`. Deployed 2026-09-30 from branch `front-end-according-to-mock-up` at `dc5ed15`.
3. Why: a car driver was shown the walking route under the car icon, with an empty banner.
4. Effect: on the live UI at 1366x768, `21.011,105.748` to `21.010,105.750` gave a 760 m walking route, then car showed no route and the banner "Connection between locations not found", then walking returned the route. The original pair (`21.014103,105.764718` to `21.014534,105.768982`) could not be reused, because its run is pruned. Whether to suggest a mode that has a route stays a product call.
