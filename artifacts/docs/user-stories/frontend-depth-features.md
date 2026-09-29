---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[point-depth-lookup-backend]]", "[[sprint-plan]]"]
tags: [user-story, epic, frontend, sprint-3]
---

# Epic: frontend depth features built on `GET /flood/points`

The three [[flood-routing-mockup-frontend-gap]] goals that all read a single point's depth at a
single timestep, all served by [[point-depth-lookup-backend]]'s `GET /flood/points`. None of these
stories can start before that endpoint exists. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- **Story 1: Place-depth popup on map tap.**
  As a user exploring the map, I want to tap a point and see its current water depth, so I can
  judge conditions at a specific location, not just along a route.
  Given the app is open with a route already showing on screen (any two points, any mode), when the
  user taps a point on the map that isn't a query point, then a card opens at that point showing its
  name, its address, its coordinates (for example "20.992987, 105.773723"), and a "Water depth now:
  `N` cm" line, matching mockup screen 2b.
  Priority: P0. Status: Done. Estimate: M. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3
  (`GET /flood/points`), Story 4 (latency validation, not run, see Details). The reverse-geocoding source
  turned out to be a new backend endpoint, since the app's geocoder is forward only.
  Evidence: ![[frontend-place-depth-popup-wet.png|420]] ![[frontend-place-depth-popup-with-route.png|420]]
  ![[frontend-place-depth-map-mode.png|420]] ![[frontend-place-depth-popup-wet-rebuilt.png|420]]
  Details:
  1. What: a card at the tapped point in Flood mode with the place name, address, coordinates, and
     "Water depth now: N cm" (`PlaceDepthPopup.tsx`), plus `GET /places/reverse` for the place.
  2. How: `ContextMenu.tsx` hands a plain click on empty map to the popup when Flood mode is on. The popup
     calls `GET /flood/points` with the selected timestep's `valid_time` and `run`, and `GET /places/reverse`
     (Photon `/reverse`), each on its own so one failing leaves the other. `placeDepth.ts` holds the parsing
     and the wording. In Map mode, and on right-click or long touch, the context menu opens as before.
  3. Why: a user can judge water at a specific place, not only along a route. Checked on the server at
     1366x768: a wet point read 205 cm (`GET /flood/points` returned 2.048 m for the same point and step), a
     dry point read 0 cm, the card also opens with a route on screen, and Map mode still opens the menu.
     A second wet-case screenshot, taken on the frontend rebuilt from the merged branch, is saved as
     `frontend-place-depth-popup-wet-rebuilt.png`.
  4. Effect: the depth line says "as of `time`" for a step older than 45 minutes and "Forecast for `time`"
     for a future step, so it never calls a stale or forecast depth the present. One tap costs one request to
     each endpoint: depth about 0.13 to 0.23 s and the place about 1.1 to 1.4 s (5 samples through the proxy
     from a Mac), so the place name is the slow part. [[point-depth-lookup-backend]] Story 4 (concurrent-tap
     latency) has not run. The card has no route button yet ([[mockup-screen-coverage]] Story 1). The address
     Photon returns includes the postcode and country, which the mockup omits. Photon returns the nearest OSM
     object, so the name can be a building near the tap. See [[place-depth-popup-on-map-tap]].


- **Story 2: Per-step depth in turn-by-turn instructions.**
  As a user following a route, I want to see the depth at each turn alongside its distance, so I
  know what to expect before I reach it.
  Given a route exists, when each turn-by-turn step in the expanded instructions list renders, then
  it shows its depth next to its distance on the same line ("320 m · 8 cm"), matching mockup screen
  2e.
  Priority: P0. Status: Not started. Estimate: S. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.

- **Story 3: Per-point depth badges along the route polyline.**
  As a user viewing a rendered route, I want to see depth badges at the points where depth changes
  along the route, so I can spot flooded segments on the map itself, not just in a list.
  Given a route exists, when the route renders on the map, then the map shows depth badges at
  points along the route polyline where the depth changes, matching the four badges in mockup screen
  2e (not fewer, and not one badge per turn regardless of whether depth changed there).
  Priority: P0. Status: Not started. Estimate: M. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.

- **Story 4: Tap a turn step to highlight its segment on the map.**
  As a user reading the turn list, I want to tap a step and see its segment on the map, so I can tell where the
  step is and where its depth applies.
  Given a route with per-step depth ([[frontend-depth-features]] Story 2), when the user clicks a step in the
  expanded instructions list, then that step's segment is highlighted on the map and the map pans or zooms to
  it, the same as the route-hint buttons do.
  Reuse the click handler of `RHButton` in `RoutingResults.tsx`, which dispatches `PathDetailsElevationSelected`
  and `SetBBox`.
  Priority: P3. Status: Not started. Estimate: XS. Sprint: 3. Dependencies: Story 2 lands first, so there is a
  depth to show for the highlighted segment.

## Status history

- **2026-09-23, draft.** Drafted from [[flood-routing-mockup-frontend-gap]]'s Goals 1, 4, and 5,
  after the popup's data source was corrected from `flood_road_values` to `GET /flood/points`.
- **2026-09-24, draft.** Story 1's acceptance now includes the coordinates line that mockup
  screen 2b shows. The popup's route button is a separate story in [[mockup-screen-coverage]].
- **2026-09-29, draft.** Story 1 done. A plain click already opened the context menu, so the popup replaces it
  only in Flood mode. See [[place-depth-popup-on-map-tap]].
- **2026-09-29, draft.** Story 4 added from the tap-a-turn-step item in `TODOS.md`, scheduled in Sprint 3 after Story 2.
- **2026-09-30, draft.** Added `frontend-place-depth-popup-wet-rebuilt.png`, a second wet-case screenshot the user took on the
  frontend rebuilt from the merged branch. The card at Đại lộ Thăng Long (Tây Mỗ, Hà Nội) shows the coordinates
  21.008917, 105.733807 and "Water depth as of 29/09/2026 16:45: 62 cm", and the legend reads "As of 29/09/2026 16:45".
  The image does not show the server address. The first wet-case image, `frontend-place-depth-popup-wet.png` (212 cm at
  21.005133, 105.757325, run 15:45), is unchanged. An earlier entry here said that image was never saved. That was wrong.
