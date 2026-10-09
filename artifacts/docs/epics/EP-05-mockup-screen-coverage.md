---
date_drafted: 2026-09-24
type: user-story
us_ids: ["US-023", "US-024", "US-025", "US-026", "US-058", "US-059"]
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[EP-01-frontend-depth-features|frontend-depth-features]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[US-001-depth-forecast-chart|depth-forecast-chart]]", "[[US-022-truck-routing-profile|truck-routing-profile]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
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
| 2b | Place popup with name, address, coordinates, depth, and a route button; legend with "Updated" line | [[EP-01-frontend-depth-features|frontend-depth-features]] Story 1 (card and depth), [[EP-02-frontend-polish|frontend-polish]] Story 2 (legend line), Story 1 below (route button) | The route button was in no story |
| 2c | Empty routing panel | Story 2 below (verification only) | Covered by the new Story 2 |
| 2d | Typing, autofill suggestions | Story 2 below (verification only), [[EP-02-frontend-polish|frontend-polish]] Story 3 (`vi` locale, done) | Covered by the new Story 2 |
| 2e | Route result: per-mode times, route tabs, depth chart, steps, depth badges | [[EP-02-frontend-polish|frontend-polish]] Story 1, [[US-001-depth-forecast-chart|depth-forecast-chart]], [[EP-01-frontend-depth-features|frontend-depth-features]] Stories 2 and 3, [[US-022-truck-routing-profile|truck-routing-profile]] | None |
| 2f | Panel opens with the destination pre-filled after "route to" | Story 1 below | The action that leads here was in no story |

No existing story duplicates Story 1 or Story 2. The nearest overlap is the `TODOS.md` item
"Address autofill/geolocation search for the user", which Story 2 absorbs.

## Stories

- [[US-023-route-to-a-place-from-the-place|US-023]] Route to a place from the place popup. Story 1.
- [[US-024-verify-the-first-load-empty-panel-and|US-024]] Verify the first-load, empty-panel, and autofill screens against the mockup. Story 2.
- [[US-025-match-the-empty-routing-panel-to-screen|US-025]] Match the empty routing panel to screen 2c. Story 3.
- [[US-026-match-the-autofill-rows-to-screen-2d|US-026]] Match the autofill rows to screen 2d. Story 4.
- [[US-058-fill-from-when-the-user-taps-a|US-058]] Fill From when the user taps a second point after choosing a destination. Story 5.
- [[US-059-show-no-result-message-while-from-or|US-059]] Show no result message while From or To is empty. Story 6.

## Not scheduled

The mockup's "Try next" ideas (a second dashed line for the selected mode's depth limit, route
tabs with time and maximum depth, a mobile version of 2e) are not screens in the mockup. They stay
out of the sprints until someone decides to build them.

## Status history

- **2026-09-24, draft.** Mapped screens 2a to 2f against every existing story and found two gaps:
  the route button on the popup (2b to 2f), and no check that the unchanged screens (2a, 2c, 2d)
  match the mockup.
- **2026-09-29, draft.** Story 2 moved from Sprint 2 to the end of Sprint 3, so one pass verifies the finished screens.
- **2026-09-30, draft.** Story 1 built and `Reviewed`. See Details. Found on the way: [[BL-017-route-description-list-blanks-app|route-description-list-blanks-app]].
- **2026-09-30, draft.** Story 1 is `Done`: deployed at `5d08b99` and checked on the live site.
- **2026-09-30, draft.** Story 2 is `Done`. The comparison found a decision to make (the opening mode) and two differences, added as Stories 3 and 4. They have no sprint yet: which sprint is still to be chosen.
- **2026-09-30, draft.** The opening-mode difference is decided: the app opens in Flood mode until further notice (D-008 in [[decision-log]]). Stories 3 and 4 are still waiting for a sprint.
- **2026-09-30, draft.** Stories 3 (`US-025`) and 4 (`US-026`) are placed in Sprint 4, ahead of the accessibility story `US-032`.
- **2026-09-30, draft.** Story 5 (`US-058`) added from the user's tap-to-route flow: the second tapped point fills From. It follows Story 1 (`US-023`). The user decided on 2026-09-30 that the tap itself fills From, that the popup still opens with depth and arrow, and that the arrow then moves the point to To and empties From. Sprint 3 confirmed.
- **2026-09-30, draft.** Stories 3 (`US-025`) and 4 (`US-026`) moved from Sprint 4 to Sprint 3 at the user's request. `US-032` stays in Sprint 4.
- **2026-09-30, draft.** Story 5 (`US-058`) is `Done`: deployed and checked on the live site. Story 6 (`US-059`) added for a side effect found in that check: the yellow box shows while From is empty.
- **2026-09-30, draft.** Stories 3, 4, and 6 (`US-025`, `US-026`, `US-059`) are `Reviewed`: built and checked on a preview build. Story 4 also changed `place_search.py`, because the backend dropped Photon's `district`.
- **2026-09-30, draft.** Stories 3, 4, and 6 (`US-025`, `US-026`, `US-059`) are `Done`: deployed and checked on the live site.
