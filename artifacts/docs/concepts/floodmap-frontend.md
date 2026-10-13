---
date: 2026-10-13
type: concept
status: active
tags: [frontend, floodmap, mockup]
related: ["[[EP-19-frontend-against-the-mockup|EP-19]]", "[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[graphhopper-backend]]"]
last_updated: 2026-10-13
---

# Floodmap frontend

The frontend is the fork of GraphHopper Maps in `floodmap/graphhopper-maps`.
The flood code lives in `src/floodmap/`, and the stock routing panel lives in `src/sidebar/`.
The target design is the mockup `artifacts/raw/frontend-mockups/Flood Routing Mockups v2.html`, screens 2a to 2f.
The list of differences between the two is in [[EP-19-frontend-against-the-mockup|EP-19]].

## Where the flood parts are

- `MapModeToggle.tsx` is the Map and Flood tile pair.
- `FloodLegend.tsx` is the depth legend and the "As of" line (`timestepLabel.ts`).
- `PlaceDepthPopup.tsx` is the popup after a tap. It reads the depth from `placeDepth.ts` and the name from the geocoder. `routeToPlace.ts` turns it into a route start or destination.
- `DepthForecastChart.tsx` is the "Average water depth" chart.
- `RouteDepthBadges.tsx` draws the depth badges on a route.
- `sidebar/NoSafeRouteMessage.tsx` is the no-route box, and `departureAdvice.ts` is its "wait until" line.

## What the data gates

The chart posts the route points to `POST flood/forecast` (`FORECAST_STEPS = 8`, 15-minute steps) and draws nothing when the answer has no columns.
With no raster for the current hour, the answer is `{"columns": []}` and a visitor sees no chart.
On 2026-10-13 this was the case, because `flood_mapping_full` was paused and `GET flood/mode` answered `LIVE`.

The no-route box shows when a route request fails with an exception that ends in `ConnectionNotFoundException`.
It then posts the route points to `POST route/departures`. The backend owns the clock, and the box shows the advice or "Timing check unavailable".

## Compare the live app with the mockup

Use the Aside browser at 1366x768.
Serve a copy of the mockup from `127.0.0.1`, because the bundle needs a web origin. The frames are the six `.dv-card` elements, in the order 2a, 2b, 2c, 2f, 2d, 2e.
Test points stay inside the model border (`.claude/CLAUDE.md`). A route that works is `21.0250,105.7550` to `21.0255,105.7620` with the truck profile.
To see the chart and depth badges when the server has no current raster, set the page clock inside the stored storm. Override `Date` with `Page.addScriptToEvaluateOnNewDocument`, for example to 2026-10-10 18:20 UTC.
To see the no-route and "wait until" boxes, answer `POST route` with a 400 that has the `ConnectionNotFoundException` hint, and optionally answer `route/departures` with an `ok` body. The screenshots then show the real UI code with a forced state.
Evidence from the first pass is in `artifacts/docs/stories/evidence/US-076/`.
