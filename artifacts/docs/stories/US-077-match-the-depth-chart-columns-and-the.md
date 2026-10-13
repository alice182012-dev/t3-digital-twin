---
date_drafted: 2026-10-07
type: user-story
us_id: "US-077"
story_label: "2"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P2
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Match the depth chart columns and the route tab text to screen 2e"
---

# US-077 Match the depth chart columns and the route tab text to screen 2e

As a user comparing routes, I want the chart to show the next hours at a glance and each tab to name its road, so I read the chart and the tabs the way the approved design shows them.
Given a route with a depth forecast, when the chart renders, then it shows 5 columns that are 30 minutes apart (every second 15-minute step), only full hours are labelled, and the "now" column is the latest step at or before now, in green, with the dashed line at its depth.
Given a route with a road description, when the tabs render, then each tab reads "Via `road`", and a tab with no unique description still reads "Route N".
The pipeline publishes 15-minute steps, so the chart takes every second step.
The PRD decision of 2026-09-23 ("30 minutes, matching the mockup") stays true for the chart.
Dependencies: Story 1 (screenshots of the chart and the tabs).
Covers G1 and G3.
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-13, In progress.** Started after [[US-076-compare-the-live-app-with-the-mockup|US-076]] was accepted.
- **2026-10-13, Reviewed.** Built and checked in a local build of the frontend against the server backend. It waits for a rebuild of the frontend on the server and the owner's acceptance.

## Evidence and details

![[live-2e-via-tabs-and-30-min-chart.jpg|420]]

1. What: the chart shows up to five columns 30 minutes apart on the clock's `:00` and `:30`, the second one being the latest half hour at or before now ("Now", green, with the dashed line). Only the "Now" bar and the full hours carry a label. A route tab reads "Via `road`", and a tab with no unique description reads "Route N".
2. How: `shapeDepthChart` in `floodmap/graphhopper-maps/src/floodmap/depthForecast.ts` picks the columns by `valid_time`, and the request asks for 9 steps of 15 minutes from 30 minutes before the half hour. `buildRouteTabs` in `sidebar/routingResultsView.ts` adds "Via". The tests are in `test/floodmap/depthForecast.test.ts` and `test/sidebar/routingResultsView.test.ts`, and 153 tests of `test/floodmap` and `test/sidebar` pass in a throwaway Node container, with `tsc --noEmit` and `prettier --check` clean.
3. Why the grid sits on the clock: a grid anchored on the current 15-minute step puts the columns on `:15` and `:45` half of the time, so no hour label shows. The cost is that the "Now" bar can be up to 29 minutes behind the map's current step.
4. The screenshot comes from a local build served on `127.0.0.1`, with the page clock set to 2026-10-10 18:20 UTC (inside the stored storm) and a faked `/route` answer that adds three street names, because the live backend sends no `description` (a request for 3 alternatives gave one path with none). Four of the five columns show, because the stored run ends at 02:15.
5. Open for the owner: the backend returns no road description, so on the server the tabs still read "Route 1" until the backend sends one. A story is needed if the owner wants "Via road" live.
