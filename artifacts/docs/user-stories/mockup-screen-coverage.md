---
date_drafted: 2026-09-24
type: user-story
us_ids: ["US-023", "US-024", "US-025", "US-026", "US-058", "US-059"]
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
  Priority: P3. Status: Not started. Estimate: S. Sprint: 3 (moved from Sprint 4 by the user on 2026-09-30). Dependencies: None.

- **Story 4 (US-026): Match the autofill rows to screen 2d.**
  As a user typing a place, I want each suggestion to show the place name and its district on one line, so I can tell places apart quickly.
  Given "C5" is typed into an input, when the suggestions show, then each row has a pin icon, the name in bold, and its district at the right edge, as in the mockup's four rows.
  The live rows show a bold name with the full address on a second line, up to six rows, and no pin icon. The results themselves are correct: all are in Vietnam, and "Hồ Gươm" ranks the Hanoi lake first.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 3 (moved from Sprint 4 by the user on 2026-09-30). Dependencies: None.

- **Story 5 (US-058): Fill From when the user taps a second point after choosing a destination.**
  As a user planning a route on the map, I want to tap a second point and have it become the start, so I can
  build a route with taps alone and never type a place.
  The flow the user described on 2026-09-30:
  1. The user opens the map.
  2. The user taps a point. The place popup opens.
  3. The user clicks the route button (the arrow) in the popup. That point becomes the destination ([[mockup-screen-coverage]] Story 1, `US-023`, already done).
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
  4. Effect: checked on a preview build and then on the live site at `100.67.84.55:8082` (2026-09-30), with the destination tapped at 21.025484, 105.761959 and the start at 21.025003, 105.754921. From filled with "Đại đội 26", the popup showed the depth, and a 1.8 km route planned itself. The arrow then gave To "Đại đội 26" and an empty From. One side effect is logged as [[no-safe-route-box-shown-with-empty-start]] and Story 6: after the arrow, the panel shows the yellow "No safe route available" box although From is empty.  Test points: two points inside the model border, for example 21.0250, 105.7550 and 21.0255, 105.7620
  (`.claude/CLAUDE.md`, "Test points stay inside the model border").

- **Story 6 (US-059): Show no result message while From or To is empty.**
  As a user who just pressed the arrow on a point that filled From, I want the panel to say nothing about routes until both points are set, so I am not told there is no safe route when I have not asked for one.
  Given a route was shown and the user presses the arrow on the point that filled From, when From goes back to empty, then the panel shows no route result and no "No safe route available" box. With both points set and no route, the box still shows.
  Cause and evidence are in [[no-safe-route-box-shown-with-empty-start]].
  Priority: P2. Status: Not started. Estimate: XS. Sprint: 3 (follow-up to US-058, found 2026-09-30). Dependencies: US-058, US-057.
  Blocker tracking: [[no-safe-route-box-shown-with-empty-start]]

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
- **2026-09-30, draft.** Story 5 (`US-058`) added from the user's tap-to-route flow: the second tapped point fills From. It follows Story 1 (`US-023`). The user decided on 2026-09-30 that the tap itself fills From, that the popup still opens with depth and arrow, and that the arrow then moves the point to To and empties From. Sprint 3 confirmed.
- **2026-09-30, draft.** Stories 3 (`US-025`) and 4 (`US-026`) moved from Sprint 4 to Sprint 3 at the user's request. `US-032` stays in Sprint 4.
- **2026-09-30, draft.** Story 5 (`US-058`) is `Done`: deployed and checked on the live site. Story 6 (`US-059`) added for a side effect found in that check: the yellow box shows while From is empty.
