---
date_drafted: 2026-09-24
type: user-story
us_ids: ["US-023", "US-024", "US-025", "US-026"]
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

- **Story 1 (US-023): Route to a place from the place popup.**
  As a user who tapped a place on the map, I want to start a route to it from the popup, so I
  don't retype the place in the destination field.
  Given the place popup from [[frontend-depth-features]] Story 1 is open, when the user clicks the
  route button in the card header (or the route pill on the map pin), then the routing panel opens
  with that place's name pre-filled as the destination and the start field empty, matching mockup
  screen 2f.
  Priority: P1. Status: Done. Estimate: S. Sprint: 3. Dependencies: [[frontend-depth-features]]
  Story 1. The existing right-click menu (`floodmap/graphhopper-maps/src/map/ContextMenuContent.tsx`)
  already has a route-to action to reuse for the click handler.
  Evidence: ![[frontend-route-to-place-live-check.png|420]] ![[frontend-route-to-place-preview-check.png|420]]
  Details:
  1. What: the place popup has a 36 px round blue route button in its header, as in mockup screen 2b. Clicking it opens the routing panel with the place's name as the destination and closes the popup, as in screen 2f.
  2. How: `destinationForPlace` in `routeToPlace.ts` moves the last query point to the tapped coordinate and names it after the place, or after the coordinates when the place has no name. `App.tsx` dispatches `SetPoint` with it and opens the panel. `showSidebar` moved up from `LargeScreenLayout` into `App` for that. The other query points stay as they are, so a start the user already set is kept and an empty start stays empty.
  3. Why: a user who tapped a place should not retype it in the destination field.
  4. Effect: checked on a preview build on the server. With an empty start, the panel shows an empty From and "Trường Trung học phổ thông Tây Mỗ" in To. With a start set (`21.0000,105.7450`), the route is planned to the place. The pin on the map does not get its own route pill, which the story allowed as an alternative. The small-screen layout keeps its search panel open all the time, so it needs no change. Deployed 2026-09-30 (`5d08b99`). On the live site the button gives an empty From and "Trường Trung học phổ thông Tây Mỗ" in To, and with a start set (`21.0000,105.7450`) it plans the route to "Đường Đại Việt" (`frontend-route-to-place-live-check.png`).

- **Story 2 (US-024): Verify the first-load, empty-panel, and autofill screens against the mockup.**
  As a product owner, I want screens 2a, 2c, and 2d checked against the approved mockup on the live
  app, so the "already matched" claim in [[flood-routing-mockup-frontend-gap]] is confirmed, not
  assumed.
  Given the frontend is rebuilt and running on the remote host, when each screen is opened in a
  1366x768 browser window, then screen 2a shows the "Search Floodmap" pill with Map on and Flood
  off, screen 2c shows both empty inputs with the placeholder text, and screen 2d shows autofill
  suggestions for a query such as "C5" and for "Hồ Gươm" with no results from outside Vietnam. Any
  difference is logged as a new story or blocker.
  Priority: P2. Status: Done. Estimate: S. Sprint: 3, last row (re-cut 2026-09-29). Dependencies: Sprint 3's UI stories, so one pass checks the finished screens. Closes the
  `needs-revalidation` autofill item in `TODOS.md` and re-verifies the `vi` locale fix, which needs
  a rebuild and redeploy.
  Evidence: ![[live-2a-first-load-check.png|300]] ![[live-2c-empty-panel-check.png|300]] ![[live-2d-autofill-c5-check.png|300]] ![[live-2d-autofill-ho-guom-check.png|300]]
  Mockup side: ![[mockup-2a-first-load.png|300]] ![[mockup-2c-empty-panel.png|300]] ![[mockup-2d-autofill.png|300]]
  Details:
  1. What: screens 2a, 2c, and 2d of the mockup were compared with the live app at `100.67.84.55:8082`, at 1366x768, and every difference was logged.
  2. How: the mockup file was opened locally and each card captured. The live app was captured on first load, with the routing panel opened, and with "C5" and "Hồ Gươm" typed into From.
  3. Why: to confirm that these screens match the approved design, not to assume it.
  4. Effect: the autofill closes its `needs-revalidation` item. "Hồ Gươm" returns Hanoi results first and every result is in Vietnam, so the `vi` locale fix holds. The screens do not match on three counts, logged below. Screen 2a: the app opens in Flood mode, and the mockup opens with Flood off. `FloodStore.ts` sets that as a "demo default", and the user decided to keep it (D-008 in [[decision-log]]). Screen 2c: [[mockup-screen-coverage]] Story 3. Screen 2d: Story 4.

- **Decision made: the app opens in Flood mode, until further notice.**
  Screen 2a opens with Map on and Flood off, with no legend. The app opens in Flood mode with the legend and the flood
  layer, because `FloodStore.ts` sets `mapMode: 'flood'` and `userChoseMapMode: true` as a "demo default". The user decided on
  2026-09-30 to keep it, because the app is in its building phase and Flood mode is the mode being built. The difference from
  screen 2a is on purpose. See D-008 in [[decision-log]].

- **Story 3 (US-025): Match the empty routing panel to screen 2c.**
  As a first-time user, I want the empty panel to read like the approved design, so it tells me what to type.
  Given the routing panel is opened with no points, when it renders, then the inputs read "Choose starting point, or click on the map" and "Choose destination", and the mode row lists car, motorbike, walking, and truck in that order.
  The live panel differs in these ways: the placeholders read "From" and "To", the modes run motorbike, car, truck, walking with motorbike selected, and it also shows a settings gear, "Add location", "Settings", and "Powered by GraphHopper", which the mockup does not. Whether to keep those extras is a product call.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 4 (2026-10-12 to 2026-10-18, placed by the user on 2026-09-30). Dependencies: None.

- **Story 4 (US-026): Match the autofill rows to screen 2d.**
  As a user typing a place, I want each suggestion to show the place name and its district on one line, so I can tell places apart quickly.
  Given "C5" is typed into an input, when the suggestions show, then each row has a pin icon, the name in bold, and its district at the right edge, as in the mockup's four rows.
  The live rows show a bold name with the full address on a second line, up to six rows, and no pin icon. The results themselves are correct: all are in Vietnam, and "Hồ Gươm" ranks the Hanoi lake first.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 4 (2026-10-12 to 2026-10-18, placed by the user on 2026-09-30). Dependencies: None.

## Not scheduled

The mockup's "Try next" ideas (a second dashed line for the selected mode's depth limit, route
tabs with time and maximum depth, a mobile version of 2e) are not screens in the mockup. They stay
out of the sprints until someone decides to build them.

## Status history

- **2026-09-24, draft.** Mapped screens 2a to 2f against every existing story and found two gaps:
  the route button on the popup (2b to 2f), and no check that the unchanged screens (2a, 2c, 2d)
  match the mockup.
- **2026-09-29, draft.** Story 2 moved from Sprint 2 to the end of Sprint 3, so one pass verifies the finished screens.
- **2026-09-30, draft.** Story 1 built and `Reviewed`. See Details. Found on the way: [[route-description-list-blanks-app]].
- **2026-09-30, draft.** Story 1 is `Done`: deployed at `5d08b99` and checked on the live site.
- **2026-09-30, draft.** Story 2 is `Done`. The comparison found a decision to make (the opening mode) and two differences, added as Stories 3 and 4. They have no sprint yet: which sprint is still to be chosen.
- **2026-09-30, draft.** The opening-mode difference is decided: the app opens in Flood mode until further notice (D-008 in [[decision-log]]). Stories 3 and 4 are still waiting for a sprint.
- **2026-09-30, draft.** Stories 3 (`US-025`) and 4 (`US-026`) are placed in Sprint 4, ahead of the accessibility story `US-032`.

