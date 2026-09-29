---
date: 2026-09-29
type: plan
status: active
tags: [plan, frontend, todos, backend-dependency]
related: ["[[flood-routing-mockup-frontend-gap]]", "[[frontend-depth-features]]", "[[frontend-polish]]", "[[mockup-screen-coverage]]", "[[truck-routing-profile]]", "[[depth-forecast-chart]]", "[[route-forecast-query]]", "[[point-depth-lookup-backend]]", "[[flood-points-connection-per-request]]", "[[routing-not-time-aware]]", "[[map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[sprint-plan]]"]
---

# Frontend todos and their backend dependencies

Written 2026-09-29 from a refresh of the vault and a check of `floodmap/graphhopper-maps/src` and
`floodmap/graphhopper-flood-road/backend` at `main` (`88070cd`). It lists what is left in the
frontend and, for each item, whether the backend is ready. Rows that name a story link to its epic
file. Nothing here replaces the sprint plan. Where the two disagree, the code check below is newer.

## What the code check found

- **The depth chart is built.** `DepthForecastChart.tsx` is wired into `RoutingResults.tsx:70` and
  calls `POST /flood/forecast`, which reads the raster tiles in 15-minute columns
  (`backend/flood_forecast.py`, up to 2,000 route points and 96 steps). Two stories still read
  `Not started`: [[depth-forecast-chart]] and [[route-forecast-query]]. Both were written for
  30-minute columns over `flood_road_values`. The work went a different way, so both files need a
  status and design update, not new code.
- **No frontend code calls `GET /flood/points`.** A search of `src/` finds no caller. The endpoint
  is live and verified on the server, so the three point-depth stories are unblocked on the backend
  and unstarted on the frontend.
- **The truck profile is still missing.** `config-local.js.example` lists `motorbike`, `car`, and
  `foot`. Its comment says truck is not listed yet.
- **The default zoom is still 17.** `src/map/map.ts:19`.

## Todos, in the order to work them

| # | Todo | Size | Backend state | Blocks or waits on |
| - | ---- | ---- | ------------- | ------------------ |
| 1 | Show the truck routing profile (done 2026-09-29) | S | Ready. GraphHopper serves `truck`, and the depth-limit blocker is resolved. | Nothing. |
| 2 | Lower the default zoom from 17 to a value from 13 to 15 (done 2026-09-29, zoom 14) | XS | None needed. | Nothing. |
| 3 | Place-depth popup on map tap (done 2026-09-29) | M | Endpoint ready. Latency unmeasured. | Todo 9, reverse geocoding. |
| 4 | Per-step depth in the turn-by-turn list | S | Endpoint ready, but the call shape is a problem. | Todo 9. |
| 5 | Depth badges along the route polyline | M | Same as todo 4. | Todo 9. |
| 6 | "Route to" button on the place popup | S | None needed. | Todo 3. |
| 7 | Tap a turn step to highlight its segment | XS | None needed. | Todo 4. |
| 8 | Check the mockup screens 2a, 2c, 2d on the live app | S | None needed. | A frontend rebuild on the remote host. |
| 9 | Decide how the frontend reads many point depths | S | Needs a backend decision. | Todos 3, 4, 5. |
| 10 | Check place search through the browser UI | XS | Ready. | Nothing. |
| 11 | Accessibility pass on the toggle, legend, and route tabs | S | None needed. | Nothing. |
| 12 | Write a project `DESIGN.md` | M | None needed. | Nothing. |
| 13 | Show no route and a clear message when a mode has none (added 2026-09-29, deferred) | S | A small backend change: pass GraphHopper's error body through. | [[failed-route-shows-previous-mode-route]] |

### 1. Show the truck routing profile

Done 2026-09-29. `truck: {}` is in the config, the frontend is rebuilt and recreated on the server, and the live UI shows four modes with a 918 m truck route ([[truck-routing-profile]], evidence `frontend-truck-profile.png`).

Add `truck: {}` to `profiles` in `config-local.js.example`, rebuild `flood-routing-frontend` on the
remote host, and confirm the profile row shows four modes and a truck route returns. See
[[truck-routing-profile]]. The known risk in that story is gone: routing now sends each request's
own profile ([[flood-routing-vehicle-type-always-motorbike]], resolved). The per-mode travel time
row sends one request per mode, so a fourth mode adds a fourth request per query. The story keeps
that as an accepted cost.

### 2. Lower the default zoom

Done 2026-09-29. The default is zoom 14. Screenshots: `frontend-default-zoom-14-desktop.png` and `frontend-default-zoom-14-mobile.png` under `docs/user-stories/evidence/`.

Change `zoom: 17` in `src/map/map.ts:19` to a value from 13 to 15 and choose the value by looking
at the study area. Backlog item "The map's default zoom is too tight", P3.

### 3. Place-depth popup on map tap

Done 2026-09-29, see [[place-depth-popup-on-map-tap]]. The reverse geocoder was a new backend endpoint, `GET /places/reverse`, since the app's geocoder is forward only. Todo 6 (route button) and todos 4, 5, 9 still stand.

Open a card on a plain tap with the place name, address, coordinates, and "Water depth now: N cm"
(mockup 2b). Today only right-click opens a menu (`ContextMenu.tsx`).

Backend dependency:

- `GET /flood/points?lat=&lon=&valid_time=` is done and matched `gdallocationinfo` at three points
  on the server. It returns `wet`, `dry`, or `no_data`.
- The latency check ([[point-depth-lookup-backend]] Story 4) has not run. The endpoint opens a new
  database connection on every request, which costs about 58 ms locally
  ([[flood-points-connection-per-request]], open, P2). A single tap is fine at that cost. Todos 4
  and 5 are not (see todo 9).
- The place name and address need a reverse geocoder. `NavBar.ts` already calls
  `reverseGeocode(...)` on the Nominatim-backed client, so start there. Photon is what
  `/geocode` uses today, and it is forward-only in the backend code read for this list. Confirm
  which client answers a point lookup before building the card.

### 4. Per-step depth in the turn-by-turn list

Show "320 m · 8 cm" on each step in `Instructions.tsx` (mockup 2e). Each step needs the depth at its
location and at the selected timestep. The backend can answer this with one `GET /flood/points` call
per step, and a route has dozens of steps. See todo 9.

### 5. Depth badges along the route polyline

Draw pill badges where depth changes along the route (mockup 2e shows four). The frontend has to
find the change points first, which needs depth at many points along the line. See todo 9. The
existing `POST /flood/forecast` samples the route already, but it returns a mean per time column,
not a depth per point, so it does not answer this.

### 6. "Route to" button on the popup

Set the popup's place as the destination and leave the start empty (mockup 2f). Reuse the route-to
action in `ContextMenuContent.tsx`. No backend work. See [[mockup-screen-coverage]] Story 1.

### 7. Tap a turn step to highlight its segment

Reuse the click handler of `RHButton` in `RoutingResults.tsx` (it dispatches
`PathDetailsElevationSelected` and `SetBBox`). No backend work. It only makes sense once todo 4
gives each step a depth to show. Backlog item, P3.

### 8. Check mockup screens 2a, 2c, and 2d on the live app

Open each screen at 1366x768 and compare it with the mockup. Log each difference as a new story or
blocker. This also closes the `needs-revalidation` autofill item in `TODOS.md`. See
[[mockup-screen-coverage]] Story 2. It needs a rebuilt frontend on the remote host.

### 9. Decide how the frontend reads many point depths

This is the one open backend question that blocks the frontend. `GET /flood/points` takes one
point. Todos 4 and 5 need tens of points per route, and todo 3 needs one. Three ways to close it:

1. Call the endpoint once per point in parallel. It needs no backend change. Each call opens a
   database connection, so the cost grows with route length unless
   [[flood-points-connection-per-request]] is fixed first.
2. Fix the connection cost, then call per point. The backlog already has this as a P2 item.
3. Add a batch endpoint that takes a list of points and returns one depth each. It needs a new
   backend story.

Recommendation: do option 2 first, measure with the Story 4 latency check on a 40-point route, and
add the batch endpoint only if that check fails the latency budget. That budget is not set yet.
The user needs to pick it.

### 10. Check place search through the browser UI

[[frontend-polish]] Story 3 is `Reviewed`. The backend returns only Hanoi results for "Hồ Gươm",
checked against `/geocode` directly. Type the query in the live UI at `100.67.84.55:8082`, then
move the story to `Done` with a screenshot.

### 11. Accessibility pass

Keyboard navigation, ARIA roles, 44 px touch targets, and 4.5:1 legend contrast for `MapModeToggle`,
`FloodLegend`, and the route tabs. Backlog item, P2. It can start now, since the components exist.

### 12. Write a project `DESIGN.md`

Run `/design-consultation` to extract tokens from the mockup. Backlog item, P3. It blocks nothing.

## Frontend work that waits on a backend or product decision

None of these can start. The frontend part is small once the decision lands.

| Item | What the frontend does | What it waits on |
| ---- | ---------------------- | ---------------- |
| Time-aware routing ([[routing-not-time-aware]], P1) | Shows "This road floods at 21:40" on the route. Possibly sends the origin to `GET /flood/areas`. | The user's choice of approach, the trip-time bound, and the overlay question (one timestep on the map, or the same window as the route). No approach is built. |
| What the map shows by default ([[map-shows-forecast-not-now]], monitoring) | Reword the legend caption. The map already picks the latest step at or before now, and the legend reads "As of". | The user's wording decision against the mockup, and the tile latency work below. |
| Map tile within 5 minutes of now ([[five-minute-tile-freshness]], idea) | Nothing, unless the team picks query-time interpolation for point depths. | Pipeline latency. Tiles publish 1.5 to 3 minutes after their target moment today. |
| Second dashed depth-limit line, route tabs with time and maximum depth, mobile version of 2e | Builds them. | A decision to build them. The mockup lists them as "Try next", so no story exists. |

## Vault upkeep

Done on 2026-09-29. [[depth-forecast-chart]] and [[route-forecast-query]] now describe the
raster-based, 15-minute design and read `Reviewed`. [[sprint-plan]] carries the same status, the
point-depth rows name todo 9 as a dependency, and its risks table has a latency row. [[frontend-polish]]
Story 2 has a history entry about the "As of" caption.

Still open: a server screenshot of the chart and of the `POST /flood/forecast` response, one
hand-checked column, and `test_flood_forecast.py` against a real PostGIS. Each is needed before
either story reaches `Done`.

## Status history

- **2026-09-29, active.** Written after a vault refresh and a code check. No frontend change made.
- **2026-09-29, active.** Updated the stale stories and the sprint plan.
- **2026-09-29, active.** Todo 1 (truck profile) done.
- **2026-09-29, active.** Added todo 13 from [[failed-route-shows-previous-mode-route]]. Deferred by the user.
- **2026-09-29, active.** Todo 2 (default zoom) done.
- **2026-09-29, active.** Todo 3 (place-depth popup) done.
