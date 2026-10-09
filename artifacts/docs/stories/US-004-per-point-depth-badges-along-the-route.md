---
date_drafted: 2026-09-23
type: user-story
us_id: "US-004"
story_label: "3"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P0
estimate: M
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-01-frontend-depth-features]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Per-point depth badges along the route polyline"
---

# US-004 Per-point depth badges along the route polyline

As a user viewing a rendered route, I want to see depth badges at the points where depth changes
along the route, so I can spot flooded segments on the map itself, not just in a list.
Given a route exists, when the route renders on the map, then the map shows depth badges at
points along the route polyline where the depth changes, matching the four badges in mockup screen
2e (not fewer, and not one badge per turn regardless of whether depth changed there).
Dependencies: [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 3, Story 4.
Evidence: ![[frontend-route-depth-badges-live-check.png|420]] ![[frontend-route-depth-badges-preview-check.png|420]]
Details:
1. What: the map shows depth badges at the stretches of the route where the depth band changes, at most 6, each a white pill with a band-colored dot and text such as "36 cm", with the deepest in bold, as in mockup screen 2e.
2. How: `POST /flood/profile` (`flood_profile.py`) resamples the route like the forecast (every 25 m, at most 200 samples) and reads `flood_depth_raster_tile` for the selected timestep. `depthBadges` groups samples by display band, drops one-sample stretches unless they are local peaks, and keeps the first, the last, and the deepest. `RouteDepthBadges` draws them through six always-mounted `MapPopup` slots. The plan and the rule are in [[route-depth-badges]].
3. Why: a user can spot the flooded stretches on the map itself, not only in the step list.
4. Effect: checked on a preview build on the server with real data. A 6.4 km walking route from `21.0141,105.764` to `21.0145,105.769` at the 02:15 step showed 6 badges: 0, < 5, 30, 36, 23, and 26 cm. All 66 samples of two other routes (41 and 25 samples) matched separate `ST_Value` reads. Badges of nearby stretches overlap at wide zoom levels (23 and 36 cm sit about 100 m apart), so a later story could space them by screen distance. Deployed 2026-09-30 (`1b80cc3`). On the live site the same route shows the same 6 badges (`frontend-route-depth-badges-live-check.png`), `POST /flood/profile` returns 41 samples for the 4.5 km car route as the preview did, and switching to a mode with no route and back keeps the app up and brings the badges back.
