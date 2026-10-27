---
date_drafted: 2026-10-07
type: user-story
us_id: "US-081"
story_label: "6"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P3
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Draw a second dashed line for the selected mode's depth limit"
---

# US-081 Draw a second dashed line for the selected mode's depth limit

As a user who drives a motorbike, a car, or a truck, I want the chart to show my vehicle's limit, so I see when the route depth crosses it.
Given a route and a selected mode, when the chart renders, then a second dashed line marks that mode's limit in centimetres, labelled, and it moves when the user selects another mode.
The limits come from one owner (`US-074`).
Dependencies: Story 2, and `US-074` for the limits.
Covers the first "Try next" line of the mockup (G6).
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, In progress.** Started after [[US-080-keep-as-of-and-bring-the-us|US-080]] was `Reviewed`, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance. The screenshots show a dry route, so they do not show the line at a height that differs from the top of the chart.

## Evidence and details

Truck (35 cm): ![[live-limit-truck.jpg|420]]
Car (30 cm): ![[live-limit-car.jpg|420]]
Motorbike (20 cm): ![[live-limit-motorbike.jpg|420]]

1. What: the depth chart draws a second dashed line, in red, for the selected mode's depth limit, labelled "35 cm", "30 cm", or "20 cm" in the right gutter, next to the dark dashed line of the "now" column. The label follows the selected mode.
2. How: the limit is the hint `td.limit_cm` that the `/route` answer already carries, which GraphHopper sets from `td_limit_cm`. A test keeps it equal to `VEHICLE_PROFILES` in `flood_utils.py` (motorbike 20, car 30, truck 35, foot 40), so the frontend holds no copy ([[US-074-give-the-vehicle-thresholds-one-owner|US-074]]). `shapeDepthChart` in `floodmap/graphhopper-maps/src/floodmap/depthForecast.ts` takes the limit and returns its line position, and the axis grows to `max(10, limit, tallest column)`. `DepthForecastChart.tsx` and its CSS draw the line, and `RoutingResults.tsx` and `App.tsx` pass the value. If the hint is missing, no line is drawn. Three new tests in `test/floodmap/depthForecast.test.ts` cover the scale, an axis that grows to a limit above the columns, and no limit. The whole jest suite (331 tests) and `tsc --noEmit` pass on the merged tree.
3. The screenshots come from a local dev build with the page clock set to 2026-10-10 18:20 UTC and a copy of `config-local.js.example` in the container, for `21.0250,105.7550` to `21.0255,105.7620`. The route is dry at that time, so every column is 0 and the limit line sits at the top, because the scale equals the limit.
4. Not checked: a wet route, where the limit line sits between the columns. The two right-gutter labels (limit and "now") overlap when the limit and the "now" depth are close, and that case is not handled. With `TIME_AWARE_ROUTING` off, the backend may omit the hint.
5. Left for `Done`: the server rebuild, a server screenshot on a wet route, and the update of [[floodmap-frontend]].
