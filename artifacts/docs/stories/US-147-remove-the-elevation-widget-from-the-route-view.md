---
date_drafted: 2026-10-13
type: user-story
us_id: "US-147"
title: "Remove the Elevation widget from the route view"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
kind: story
priority: P3
estimate: XS
sprint: 15
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-147 Remove the Elevation widget from the route view

As a user reading a route in a flood app, I want no elevation chart, so the map shows only what the design shows.

Difference `N4` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The stock GraphHopper elevation widget (`src/pathDetails/ElevationInfoBar.tsx`) shows at the bottom left of every route result. Mockup screen 2e has none, and the area is flat, so the chart reads "-" with a 0 m line.

Given a route result at 1366x768, when the panel shows the route, then no elevation widget, path-detail selector, or play button shows, and the map and the legend are unchanged.
Given the path-detail popup code, then the story removes or leaves it by a decision recorded here, and no console error appears.

Dependencies: None. Ask the owner whether any path detail (surface, road class) is wanted before it is removed.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.
- **2026-10-14, owner answer.** No path detail (surface, road class) is wanted, so the Elevation widget goes with no replacement. A worker builds it.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.

![[after-route-panel.jpg|420]]

1. What: the Elevation widget, its path-detail selector, and the play button are gone from the route view. The map and the legend are unchanged, and the Map and Flood tiles that the widget hid are visible.
2. How: `ElevationInfoBar`, `ElevationWidget` with its chart code, and `PathDetailPopup` are deleted, with the `PathDetailsHover` and `PathDetailsRangeSelected` actions. `PathDetailsStore` keeps the highlighted segments, which the route hint buttons use. `elevationWidget/colors.ts` stays, because `RouteStats` uses it. jest went from 350 to 294 tests, because the tests of the deleted chart code went too, and `tsc --noEmit` passes.
3. Evidence: `evidence/US-147/` holds before and after screenshots of the route panel and of the map. The console shows no page error. The only errors are 404s from the unreachable `/flood-extent` proxy, which were there before.
4. Not checked: a route at 390 px with the old Details panel open.
5. Left over: the directory name `elevationWidget/` is misleading and a rename is a separate refactor. The unused `elevation` and `path_details` keys stay in `tr.json`.
6. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows a route result with no Elevation widget, selector, or play button at the bottom left. Screenshot: `evidence/server-check-2026-10-14/server-route-panel.jpg`. The owner accepted the story on 2026-10-14.
