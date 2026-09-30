---
date_open: 2026-09-30
date_closed: 2026-09-30
type: blocker
status: resolved
severity: P3
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, frontend, routing, panel]
related: ["[[mockup-screen-coverage]]", "[[frontend-polish]]", "[[route-panel-stuck-on-loading-bars]]"]
last_updated: 2026-09-30
---

# No safe route box shown with empty start

## Description

On the live site (2026-09-30), the user taps a destination and presses the arrow, taps a second point so it fills From, and a route shows. Pressing the arrow on that second point moves it to To and empties From. The panel then shows the yellow "No safe route available" box, although From is empty and no route was asked for (`frontend-tap-arrow-empties-from-live-check.png`).

`selectRoutingResultsView` in `floodmap/graphhopper-maps/src/sidebar/routingResultsView.ts` returns `empty` when there are no paths, no request is pending, and `currentRequest.subRequests` is not empty. After a route was shown, the earlier requests stay in `subRequests`. Emptying a point clears the paths, so the view reads `empty`. Whether a manual clear of From does the same was not compared, because the browser tool could not clear the field.

## Why this matters

The arrow after an auto-fill is a step of the flow in [[mockup-screen-coverage]] Story 5. The box tells the user no safe route exists, when the panel is only waiting for a start. It blocks no story of Sprint 4 (rule 11), so it is fixed in Sprint 3 as Story 6 (`US-059`).

## Approaches tried

None yet.

## Decision and explanation

Pending. The likely fix is to select `idle` when either query point is not initialized, and to pass the points to `selectRoutingResultsView`.

## Related topics

- [[route-panel-stuck-on-loading-bars]]: the same panel's loading state. On the live site a no-connection pair kept the grey loading bars for more than 9 seconds before the yellow box appeared (2026-09-30).

## Status history

- **2026-09-30, open.** Found in the live check of `US-058`. Not reproduced by clearing From by hand.
- **2026-09-30, open.** Fix built as `5193d86` (`US-059`) and checked on a preview build: the arrow empties From and no box shows. It moves to `resolved` after the live check.
- **2026-09-30, resolved.** `5193d86` is deployed. On the live site the arrow empties From and no box shows (`frontend-no-message-empty-from-live-check.png`).
