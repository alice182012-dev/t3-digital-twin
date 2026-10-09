---
date_drafted: 2026-09-24
type: user-story
us_id: "US-023"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P1
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Route to a place from the place popup"
---

# US-023 Route to a place from the place popup

As a user who tapped a place on the map, I want to start a route to it from the popup, so I
don't retype the place in the destination field.
Given the place popup from [[EP-01-frontend-depth-features|frontend-depth-features]] Story 1 is open, when the user clicks the
route button in the card header (or the route pill on the map pin), then the routing panel opens
with that place's name pre-filled as the destination and the start field empty, matching mockup
screen 2f.
Priority: P1. Status: Done. Estimate: S. Sprint: 3. Dependencies: [[EP-01-frontend-depth-features|frontend-depth-features]]
Story 1. The existing right-click menu (`floodmap/graphhopper-maps/src/map/ContextMenuContent.tsx`)
already has a route-to action to reuse for the click handler.
Evidence: ![[frontend-route-to-place-live-check.png|420]] ![[frontend-route-to-place-preview-check.png|420]]
Details:
1. What: the place popup has a 36 px round blue route button in its header, as in mockup screen 2b. Clicking it opens the routing panel with the place's name as the destination and closes the popup, as in screen 2f.
2. How: `destinationForPlace` in `routeToPlace.ts` moves the last query point to the tapped coordinate and names it after the place, or after the coordinates when the place has no name. `App.tsx` dispatches `SetPoint` with it and opens the panel. `showSidebar` moved up from `LargeScreenLayout` into `App` for that. The other query points stay as they are, so a start the user already set is kept and an empty start stays empty.
3. Why: a user who tapped a place should not retype it in the destination field.
4. Effect: checked on a preview build on the server. With an empty start, the panel shows an empty From and "Trường Trung học phổ thông Tây Mỗ" in To. With a start set (`21.0000,105.7450`), the route is planned to the place. The pin on the map does not get its own route pill, which the story allowed as an alternative. The small-screen layout keeps its search panel open all the time, so it needs no change. Deployed 2026-09-30 (`5d08b99`). On the live site the button gives an empty From and "Trường Trung học phổ thông Tây Mỗ" in To, and with a start set (`21.0000,105.7450`) it plans the route to "Đường Đại Việt" (`frontend-route-to-place-live-check.png`).
