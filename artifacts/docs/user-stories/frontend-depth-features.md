---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-002", "US-003", "US-004", "US-005"]
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

- **Story 1 (US-002): Place-depth popup on map tap.**
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


- **Story 2 (US-003): Per-step depth in turn-by-turn instructions.**
  As a user following a route, I want to see the depth at each turn alongside its distance, so I
  know what to expect before I reach it.
  Given a route exists, when each turn-by-turn step in the expanded instructions list renders, then
  it shows its depth next to its distance on the same line ("320 m · 8 cm"), matching mockup screen
  2e.
  Priority: P0. Status: Done. Estimate: S. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.
  Evidence: ![[frontend-per-step-depth-live-check.png|420]] ![[frontend-per-step-depth-preview-check.png|420]]
  Details:
  1. What: each step in the expanded instructions list shows the water depth at its start point after its distance, for example "134 m · 16 cm", in Flood mode. Map mode shows the distance only.
  2. How: `useStepDepths` requests `GET /flood/points` for every step at the selected timestep, and `stepDepthText` prints the reading. `depthQuery` builds the query and is shared with the place-depth popup. The step's depth is the depth at its start point, not the deepest point along it.
  3. Why: a user can see what to expect before reaching each turn.
  4. Effect: checked on a preview build on the server (port 8083) against the real backend, with the browser clock set to 2026-09-29 17:00 +07:00 because the pipeline is paused. A 5-step route from a start point that is 16 cm deep at the 16:45 step showed 16, 0, 0, 0, and 0 cm, the same as `GET /flood/points` for each start point. A 17-step route showed 0 cm on every step, also matching. A step with no reading prints nothing, so no step claims a depth it lacks. Each route costs one request per step. Deployed 2026-09-30 (`ac1ab84`). On the live frontend at 8082, with the real clock, all 17 steps of the car route from `21.0000,105.7450` to `21.0060,105.7520` show "N m · 0 cm" (`frontend-per-step-depth-live-check.png`). Tap-a-step (Story 4) can start.

- **Story 3 (US-004): Per-point depth badges along the route polyline.**
  As a user viewing a rendered route, I want to see depth badges at the points where depth changes
  along the route, so I can spot flooded segments on the map itself, not just in a list.
  Given a route exists, when the route renders on the map, then the map shows depth badges at
  points along the route polyline where the depth changes, matching the four badges in mockup screen
  2e (not fewer, and not one badge per turn regardless of whether depth changed there).
  Priority: P0. Status: Done. Estimate: M. Sprint: 3. Dependencies: [[point-depth-lookup-backend]] Story 3, Story 4.
  Evidence: ![[frontend-route-depth-badges-live-check.png|420]] ![[frontend-route-depth-badges-preview-check.png|420]]
  Details:
  1. What: the map shows depth badges at the stretches of the route where the depth band changes, at most 6, each a white pill with a band-colored dot and text such as "36 cm", with the deepest in bold, as in mockup screen 2e.
  2. How: `POST /flood/profile` (`flood_profile.py`) resamples the route like the forecast (every 25 m, at most 200 samples) and reads `flood_depth_raster_tile` for the selected timestep. `depthBadges` groups samples by display band, drops one-sample stretches unless they are local peaks, and keeps the first, the last, and the deepest. `RouteDepthBadges` draws them through six always-mounted `MapPopup` slots. The plan and the rule are in [[route-depth-badges]].
  3. Why: a user can spot the flooded stretches on the map itself, not only in the step list.
  4. Effect: checked on a preview build on the server with real data. A 6.4 km walking route from `21.0141,105.764` to `21.0145,105.769` at the 02:15 step showed 6 badges: 0, < 5, 30, 36, 23, and 26 cm. All 66 samples of two other routes (41 and 25 samples) matched separate `ST_Value` reads. Badges of nearby stretches overlap at wide zoom levels (23 and 36 cm sit about 100 m apart), so a later story could space them by screen distance. Deployed 2026-09-30 (`1b80cc3`). On the live site the same route shows the same 6 badges (`frontend-route-depth-badges-live-check.png`), `POST /flood/profile` returns 41 samples for the 4.5 km car route as the preview did, and switching to a mode with no route and back keeps the app up and brings the badges back.

- **Story 4 (US-005): Tap a turn step to highlight its segment on the map.**
  As a user reading the turn list, I want to tap a step and see its segment on the map, so I can tell where the
  step is and where its depth applies.
  Given a route with per-step depth ([[frontend-depth-features]] Story 2), when the user clicks a step in the
  expanded instructions list, then that step's segment is highlighted on the map and the map pans or zooms to
  it, the same as the route-hint buttons do.
  Reuse the click handler of `RHButton` in `RoutingResults.tsx`, which dispatches `PathDetailsElevationSelected`
  and `SetBBox`.
  Priority: P3. Status: Done. Estimate: XS. Sprint: 3. Dependencies: Story 2 lands first, so there is a
  depth to show for the highlighted segment.
  Evidence: ![[frontend-tap-step-highlight-live-check.png|420]] ![[frontend-tap-step-highlight-preview-check.png|420]]
  Details:
  1. What: clicking a step in the expanded instructions list highlights that step's segment on the map and zooms to it. The step popup still opens at the step's start.
  2. How: `stepHighlight` in `stepHighlight.ts` turns the step's points into a lat/lng segment and a bounding box. The step's `onClick` in `Instructions.tsx` dispatches `PathDetailsElevationSelected` with the segment and `SetBBox` with the box, the same two actions the route-hint buttons use.
  3. Why: a user can tell where a step is on the map and where its depth applies.
  4. Effect: checked on a preview build on the server (port 8083), real backend: clicking "Turn left onto Phố Cầu Cốc" (422 m) zoomed the map to that stretch and drew it in red. A step that is a single point, such as the arrival, gets a padded box. Deployed 2026-09-30 (`448a434`). On the live frontend at 8082 the same step zooms and draws in red (`frontend-tap-step-highlight-live-check.png`). Clicking the same step twice does not toggle the highlight off.

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
- **2026-09-30, draft.** Story 2 built and `Reviewed`. See Details. Deploy the frontend to move it to `Done`.
- **2026-09-30, draft.** Story 2 is `Done`: deployed at `ac1ab84` and checked on the live frontend.
- **2026-09-30, draft.** Story 4 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 4 is `Done`: deployed at `448a434` and checked on the live frontend.
- **2026-09-30, draft.** Story 3 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 3 is `Done`: deployed at `1b80cc3` and checked on the live site.
