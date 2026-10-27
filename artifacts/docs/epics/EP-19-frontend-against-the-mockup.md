---
date_drafted: 2026-10-10
type: epic
epic_id: "EP-19"
theme: frontend
status: active
subsystem: floodmap-frontend
tags: [epic, frontend, mockup]
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|archived PRD-001]]", "[[frontend-mockup-recheck-and-sprint-11-start]]", "[[BL-010-map-shows-forecast-not-now|BL-010]]", "[[BL-018-route-panel-stuck-on-loading-bars|BL-018]]", "[[decision-log]]"]
---

# EP-19 Frontend against the mockup

## Goal

The `floodmap/graphhopper-maps` app matches the approved mockup (`artifacts/raw/mockups/Flood Routing Mockups v2.dc.html`, screens 2a to 2f): a place popup with depth, a travel time under each mode, a depth chart over time, a depth on each turn, depth badges along the route, and the legend's "Updated" line. A recheck compares the live app with the mockup and fixes what differs.

## Why

The first comparison found elements in the mockup with no code behind them. The full gap list is in the archived [[PRD-001-flood-routing-mockup-frontend-gap|PRD-001]]. The legend bands (5, 10, 20, 30, 40, 50, 60 cm) differ from the mockup on purpose, to match the pipeline's color ramp.

## Dependencies and assumptions

- Depth data comes from the route-forecast query and `GET /flood/points` ([[EP-17-flood-data-pipeline-and-core-output|EP-17]]).
- The "wait until" text and the fallback message come from the routing engine ([[EP-18-time-aware-routing-engine|EP-18]]).
- A UI story takes its screenshot from the running UI, with test points inside the model border.

## Definition of done

1. Given a route on screen, when the user taps a map point, then a card shows the name, address, and "Water depth now: N cm".
2. Given a route, then each mode icon shows a travel time, and the selected mode is bold.
3. Given a route, then the panel shows a 30-minute depth chart with the "now" column and a dashed line, and each step shows depth beside distance.
4. Given a route, then the map shows depth badges where the depth changes.
5. Given flood mode, then the legend shows an "Updated" line.
6. The app fits a 390 px screen.

## Risks and open questions

- Four requests for four mode times may delay the screen. Add a loading state or a multi-profile query before real users see it.
- [[BL-010-map-shows-forecast-not-now|BL-010]] was resolved by the product owner on 2026-10-10, and [[BL-018-route-panel-stuck-on-loading-bars|BL-018]] is `monitoring`.
- `US-033` (`DESIGN.md`) must run after the UI is final, so its tokens do not go stale.

## Differences from the mockup

The list of [[US-076-compare-the-live-app-with-the-mockup|US-076]], found on 2026-10-13 by comparing the live app at `100.67.84.55:8082` with the mockup at 1366x768.
`G1` to `G7` come from the archived [[frontend-mockup-recheck-and-sprint-11-start]] and keep their IDs. `N1` to `N7` are new.
The legend bands (`5 to 10 cm` and so on) differ from the mockup on purpose, so they are not a row.

| ID | Screen | Difference | Story or blocker |
| -- | ------ | ---------- | ---------------- |
| G1 | 2e | The chart labels every 15-minute column, and the mockup has 5 columns of 30 minutes with only full hours labelled | [[US-077-match-the-depth-chart-columns-and-the\|US-077]] |
| G2 | 2e | The start and destination pins carry no names | [[US-078-show-the-place-names-on-the-start\|US-078]] |
| G3 | 2e | The tab reads "Route 1", and the mockup reads "Via `road`" | [[US-077-match-the-depth-chart-columns-and-the\|US-077]] |
| G4 | all | The page title is "GraphHopper Maps \| Route Planner", and the panel shows "Powered by GraphHopper" | [[US-079-name-the-page-floodmap-and-remove-the\|US-079]] |
| G5 | 2b, all | The legend and the popup say "As of `time`", and the mockup says "Updated" and "now" | [[US-080-keep-as-of-and-bring-the-us\|US-080]] |
| G6 | 2e | No second dashed line, no time and depth on the tabs, no mobile layout | [[US-081-draw-a-second-dashed-line-for-the\|US-081]], [[US-082-show-the-travel-time-and-the-maximum\|US-082]], [[US-083-build-a-mobile-version-of-screen-2e\|US-083]] |
| G7 | states | The no-route box and the "wait until" line have no approved design | [[US-084-design-the-no-route-and-wait-until\|US-084]] |
| N1 | 2a, 2b | The Map and Flood tiles are flat grey and blue-grey blocks, and the mockup shows photo thumbnails with a white border | [[US-144-use-the-mockup-thumbnails-for-the-map-and-flood-tiles\|US-144]] |
| N2 | 2b | The legend sits top-right and covers the zoom, locate, and layer buttons of the map, and the mockup puts the legend bottom-right with a tick scale | [[US-145-stop-the-legend-from-covering-the-map-controls\|US-145]] |
| N3 | 2c | The routing panel is the stock GraphHopper card (settings gear, "Add location", "Settings", GPX, "Details"), and the mockup has a full-height panel with a black selected-mode pill, a close X, and a dotted connector | [[US-146-match-the-routing-panel-frame-to-the-mockup\|US-146]] |
| N4 | 2e | An Elevation widget sits bottom-left, and the mockup has none | [[US-147-remove-the-elevation-widget-from-the-route-view\|US-147]] |
| N5 | 2b | The popup shows "Selected location" while the name is unresolved (still after 7 s), reads "Water depth as of `date time`: N cm" and has no district line, and the search pill keeps "Search Floodmap" where the mockup shows the place name | [[BL-021-place-name-slow-after-map-tap\|BL-021]], [[US-141-host-photon-for-vietnam-next-to-the-backend\|US-141]] |
| N6 | 2f | After "Route to this place" the destination field holds raw coordinates, and the mockup holds the place name | [[US-148-show-the-place-name-in-the-destination-field\|US-148]] |
| N7 | 2d | Autofill rows are one line with a pin icon and the district at the right edge, and the mockup has two lines (name, then district) with no icon. Six rows read "C5" and differ only by district | [[US-149-match-the-autofill-rows-to-the-mockup\|US-149]] |

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-19")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created from the Scrum adoption ([[decision-log|D-024]]). It merges the archived epics `EP-01`, `EP-02`, `EP-05`, and `EP-11`, and takes the frontend stories of `EP-07`. The Sprint 13 to 16 placement of the recheck stories is dropped, so they wait in the backlog.
