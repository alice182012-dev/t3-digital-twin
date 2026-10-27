---
date_drafted: 2026-09-23
type: user-story
us_id: "US-002"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P0
estimate: M
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-01-frontend-depth-features]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Place-depth popup on map tap"
---

# US-002 Place-depth popup on map tap

As a user exploring the map, I want to tap a point and see its current water depth, so I can judge conditions at a specific location, not just along a route.
Given the app is open with a route already showing on screen (any two points, any mode), when the user taps a point on the map that isn't a query point, then a card opens at that point showing its name, its address, its coordinates (for example "20.992987, 105.773723"), and a "Water depth now:
`N` cm" line, matching mockup screen 2b.
Dependencies: [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 3 (`GET /flood/points`), Story 4 (latency validation, not run, see Details).
The reverse-geocoding source turned out to be a new backend endpoint, since the app's geocoder is forward only.
Evidence: ![[frontend-place-depth-popup-wet.png|420]] ![[frontend-place-depth-popup-with-route.png|420]]
![[frontend-place-depth-map-mode.png|420]] ![[frontend-place-depth-popup-wet-rebuilt.png|420]]
Details:
1. What: a card at the tapped point in Flood mode with the place name, address, coordinates, and "Water depth now: N cm" (`PlaceDepthPopup.tsx`), plus `GET /places/reverse` for the place.
2. How: `ContextMenu.tsx` hands a plain click on empty map to the popup when Flood mode is on.
   The popup calls `GET /flood/points` with the selected timestep's `valid_time` and `run`, and `GET /places/reverse` (Photon `/reverse`), each on its own so one failing leaves the other.
   `placeDepth.ts` holds the parsing and the wording.
   In Map mode, and on right-click or long touch, the context menu opens as before.
3. Why: a user can judge water at a specific place, not only along a route.
   Checked on the server at 1366x768: a wet point read 205 cm (`GET /flood/points` returned 2.048 m for the same point and step), a dry point read 0 cm, the card also opens with a route on screen, and Map mode still opens the menu.
   A second wet-case screenshot, taken on the frontend rebuilt from the merged branch, is saved as `frontend-place-depth-popup-wet-rebuilt.png`.
4. Effect: the depth line says "as of `time`" for a step older than 45 minutes and "Forecast for `time`" for a future step, so it never calls a stale or forecast depth the present.
   One tap costs one request to each endpoint: depth about 0.13 to 0.23 s and the place about 1.1 to 1.4 s (5 samples through the proxy from a Mac), so the place name is the slow part.
   [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 4 (concurrent-tap latency) has not run.
   The card has no route button yet ([[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 1).
   The address
   Photon returns includes the postcode and country, which the mockup omits.
   Photon returns the nearest OSM object, so the name can be a building near the tap.
   See [[place-depth-popup-on-map-tap]].
