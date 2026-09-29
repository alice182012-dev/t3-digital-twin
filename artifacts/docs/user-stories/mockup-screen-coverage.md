---
date_drafted: 2026-09-24
type: user-story
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[frontend-depth-features]]", "[[frontend-polish]]", "[[depth-forecast-chart]]", "[[truck-routing-profile]]", "[[sprint-plan]]"]
tags: [user-story, epic, frontend, mockup, sprint-2, sprint-3]
---

# Epic: mockup screen coverage

`artifacts/raw/frontend-mockups/Flood Routing Mockups v2.dc.html` has six screens, 2a to 2f. This
epic maps each screen to the stories that build it, and adds the two stories that no existing
story covered. Rows carry Priority, Estimate, and Sprint per this vault's user-story
sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint planning").

## Screen-to-story map

| Screen | What it shows | Stories that build it | Gap |
| ------ | ------------- | --------------------- | --- |
| 2a | First load: search pill, Map on, Flood off | Story 2 below (verification only, code exists) | Covered by the new Story 2 |
| 2b | Place popup with name, address, coordinates, depth, and a route button; legend with "Updated" line | [[frontend-depth-features]] Story 1 (card and depth), [[frontend-polish]] Story 2 (legend line), Story 1 below (route button) | The route button was in no story |
| 2c | Empty routing panel | Story 2 below (verification only) | Covered by the new Story 2 |
| 2d | Typing, autofill suggestions | Story 2 below (verification only), [[frontend-polish]] Story 3 (`vi` locale, done) | Covered by the new Story 2 |
| 2e | Route result: per-mode times, route tabs, depth chart, steps, depth badges | [[frontend-polish]] Story 1, [[depth-forecast-chart]], [[frontend-depth-features]] Stories 2 and 3, [[truck-routing-profile]] | None |
| 2f | Panel opens with the destination pre-filled after "route to" | Story 1 below | The action that leads here was in no story |

No existing story duplicates Story 1 or Story 2. The nearest overlap is the `TODOS.md` item
"Address autofill/geolocation search for the user", which Story 2 absorbs.

## Stories

- **Story 1: Route to a place from the place popup.**
  As a user who tapped a place on the map, I want to start a route to it from the popup, so I
  don't retype the place in the destination field.
  Given the place popup from [[frontend-depth-features]] Story 1 is open, when the user clicks the
  route button in the card header (or the route pill on the map pin), then the routing panel opens
  with that place's name pre-filled as the destination and the start field empty, matching mockup
  screen 2f.
  Priority: P1. Status: Not started. Estimate: S. Sprint: 3. Dependencies: [[frontend-depth-features]]
  Story 1. The existing right-click menu (`floodmap/graphhopper-maps/src/map/ContextMenuContent.tsx`)
  already has a route-to action to reuse for the click handler.

- **Story 2: Verify the first-load, empty-panel, and autofill screens against the mockup.**
  As a product owner, I want screens 2a, 2c, and 2d checked against the approved mockup on the live
  app, so the "already matched" claim in [[flood-routing-mockup-frontend-gap]] is confirmed, not
  assumed.
  Given the frontend is rebuilt and running on the remote host, when each screen is opened in a
  1366x768 browser window, then screen 2a shows the "Search Floodmap" pill with Map on and Flood
  off, screen 2c shows both empty inputs with the placeholder text, and screen 2d shows autofill
  suggestions for a query such as "C5" and for "Hồ Gươm" with no results from outside Vietnam. Any
  difference is logged as a new story or blocker.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 3, last row (re-cut 2026-09-29). Dependencies: Sprint 3's UI stories, so one pass checks the finished screens. Closes the
  `needs-revalidation` autofill item in `TODOS.md` and re-verifies the `vi` locale fix, which needs
  a rebuild and redeploy.

## Not scheduled

The mockup's "Try next" ideas (a second dashed line for the selected mode's depth limit, route
tabs with time and maximum depth, a mobile version of 2e) are not screens in the mockup. They stay
out of the sprints until someone decides to build them.

## Status history

- **2026-09-24, draft.** Mapped screens 2a to 2f against every existing story and found two gaps:
  the route button on the popup (2b to 2f), and no check that the unchanged screens (2a, 2c, 2d)
  match the mockup.
- **2026-09-29, draft.** Story 2 moved from Sprint 2 to the end of Sprint 3, so one pass verifies the finished screens.
