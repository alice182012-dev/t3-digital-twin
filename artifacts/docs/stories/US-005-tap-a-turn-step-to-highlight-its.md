---
date_drafted: 2026-09-23
type: user-story
us_id: "US-005"
story_label: "4"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P3
estimate: XS
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-01-frontend-depth-features]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Tap a turn step to highlight its segment on the map"
---

# US-005 Tap a turn step to highlight its segment on the map

As a user reading the turn list, I want to tap a step and see its segment on the map, so I can tell where the
step is and where its depth applies.
Given a route with per-step depth ([[EP-01-frontend-depth-features|frontend-depth-features]] Story 2), when the user clicks a step in the
expanded instructions list, then that step's segment is highlighted on the map and the map pans or zooms to
it, the same as the route-hint buttons do.
Reuse the click handler of `RHButton` in `RoutingResults.tsx`, which dispatches `PathDetailsElevationSelected`
and `SetBBox`.
Dependencies: Story 2 lands first, so there is a
depth to show for the highlighted segment.
Evidence: ![[frontend-tap-step-highlight-live-check.png|420]] ![[frontend-tap-step-highlight-preview-check.png|420]]
Details:
1. What: clicking a step in the expanded instructions list highlights that step's segment on the map and zooms to it. The step popup still opens at the step's start.
2. How: `stepHighlight` in `stepHighlight.ts` turns the step's points into a lat/lng segment and a bounding box. The step's `onClick` in `Instructions.tsx` dispatches `PathDetailsElevationSelected` with the segment and `SetBBox` with the box, the same two actions the route-hint buttons use.
3. Why: a user can tell where a step is on the map and where its depth applies.
4. Effect: checked on a preview build on the server (port 8083), real backend: clicking "Turn left onto Phố Cầu Cốc" (422 m) zoomed the map to that stretch and drew it in red. A step that is a single point, such as the arrival, gets a padded box. Deployed 2026-09-30 (`448a434`). On the live frontend at 8082 the same step zooms and draws in red (`frontend-tap-step-highlight-live-check.png`). Clicking the same step twice does not toggle the highlight off.
