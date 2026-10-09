---
date_drafted: 2026-09-24
type: user-story
us_id: "US-058"
story_label: "5"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Fill From when the user taps a second point after choosing a destination"
---

# US-058 Fill From when the user taps a second point after choosing a destination

As a user planning a route on the map, I want to tap a second point and have it become the start, so I can
build a route with taps alone and never type a place.
The flow the user described on 2026-09-30:
1. The user opens the map.
2. The user taps a point. The place popup opens.
3. The user clicks the route button (the arrow) in the popup. That point becomes the destination ([[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 1, `US-023`, already done).
4. The user taps another point. That point becomes the start, and the From field fills in at once, with no arrow click.
Given the destination is set and From is empty, when the user taps another point on the map, then that point fills
From with its reverse-geocoded place name (or its coordinates when it has no name), the destination stays as it was,
and the route is planned because both points are set.
Decided by the user on 2026-09-30: the tap itself fills From, and the place popup still opens on that tap, so the user
sees the depth at the point. The user does not need to click the arrow for From to fill.
Given the popup of that second point is open and From is already filled by the tap, when the user clicks the arrow, then
the point moves from From to To. It replaces the old destination, and From goes back to empty until the next tap fills
it. A route from a point to itself never occurs.
When both points are empty, a tap opens the popup and the arrow sets the destination, as in `US-023`. When both points
are set, a tap opens the popup and the arrow replaces the destination, as in `US-023`, and a tap does not change From.
This story changes only the case of a set destination with an empty From.
`App.tsx` decides today what a map tap does, and `destinationForPlace` in
`floodmap/graphhopper-maps/src/floodmap/routeToPlace.ts` always moves the last query point. The story adds the rule
that picks the point a tap fills.
Priority: P2. Status: Done. Estimate: S. Sprint: 3 (follow-up to US-023, placed 2026-09-30). Dependencies: US-023.
Evidence: ![[frontend-tap-fills-from-live-check.png|420]] ![[frontend-tap-arrow-empties-from-live-check.png|420]] ![[frontend-tap-fills-from-preview-check.png|420]] ![[frontend-tap-arrow-empties-from-preview-check.png|420]]
Details:
1. What: with a destination set and From empty, a tap in flood mode fills From at once. The popup still opens with the depth and the arrow. The arrow on that point moves it to To and empties From.
2. How: `startForTap`, `namedStart`, and `pointsForRoute` in `routeToPlace.ts` decide the points, and `App.tsx` dispatches them with `SetPoint` (`d0502f0`). A subagent built it tests first, 12 new tests, and I reviewed the diff. The popup's `useJson` also stopped reusing the previous tap's lookup while a new one loads. That would have named a new From after the old place.
3. Why: a user builds a route with taps alone and never types a place.
4. Effect: checked on a preview build and then on the live site at `100.67.84.55:8082` (2026-09-30), with the destination tapped at 21.025484, 105.761959 and the start at 21.025003, 105.754921. From filled with "Đại đội 26", the popup showed the depth, and a 1.8 km route planned itself. The arrow then gave To "Đại đội 26" and an empty From. One side effect is logged as [[BL-016-no-safe-route-box-shown-with-empty-start|no-safe-route-box-shown-with-empty-start]] and Story 6: after the arrow, the panel shows the yellow "No safe route available" box although From is empty.  Test points: two points inside the model border, for example 21.0250, 105.7550 and 21.0255, 105.7620
(`.claude/CLAUDE.md`, "Test points stay inside the model border").
