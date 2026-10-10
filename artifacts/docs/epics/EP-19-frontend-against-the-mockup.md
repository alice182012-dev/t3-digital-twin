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

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-19")
SORT file.name ASC
```

## Status history

- **2026-10-10, active.** Created from the Scrum adoption ([[decision-log|D-024]]). It merges the archived epics `EP-01`, `EP-02`, `EP-05`, and `EP-11`, and takes the frontend stories of `EP-07`. The Sprint 13 to 16 placement of the recheck stories is dropped, so they wait in the backlog.
