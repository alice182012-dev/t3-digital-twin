---
date_drafted: 2026-10-09
type: user-story
us_id: "US-098"
story_label: "2"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P2
estimate: S
sprint: 15
subsystem: routing, frontend
related: ["[[EP-16-precaution-depth-routing]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the recommended route and the through-water option in the app"
---

# US-098 Show the recommended route and the through-water option in the app

As a driver, I want to see both routes with a label that says the second one passes through water between the precaution depth and my limit.
Given a response with two options, when the route panel opens, then it shows the recommended route first and the through-water route as a second tab with its label and its deepest road.
With one option, it shows one route.
The no-route message changes to match D-021.
Dependencies: `US-097`, `US-076`, and the design of the no-route state in `US-084`.
Evidence: None yet.

## Status history

- **2026-10-12, not picked.** The product owner asked to add every backend story to [[SPR-014-finish-the-remaining-backend|SPR-014]]. This story is left out: its backend, [[US-097-recommend-a-route-that-avoids-the-precaution|US-097]], is `Done`, so what remains is the route panel, which is frontend work, and its dependencies [[US-076-compare-the-live-app-with-the-mockup|US-076]] and the design of [[US-084-design-the-no-route-and-wait-until|US-084]] have not started.
- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, owner answer.** The design of [[US-084-design-the-no-route-and-wait-until|US-084]] is approved, so this story no longer waits for it.
- **2026-10-14, In progress.** Started after the owner approved the design of [[US-084-design-the-no-route-and-wait-until|US-084]], within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

![[two-options-through-water-1366.png|420]]

1. What: with two route options the tabs read "Recommended" first and "Through water" second, each with its time and maximum depth from [[US-082-show-the-travel-time-and-the-maximum|US-082]] (for example "13 min · 22 cm"). With the through-water tab open, an amber line reads "Passes through water between 18 cm and 35 cm deep. Deepest road 22 cm." and replaces "Route avoids flooded areas". The second sentence shows once the depth is known. A single `recommended` answer shows one tab, "Route 1". A single `through_water` answer shows one tab, "Through water". The no-route message keeps the wording approved in US-084.
2. How: the real `POST /route` answer carries the hint `td.kinds` (`recommended`, `recommended,through_water`, or `through_water`, one word per path), with `td.limit_cm` and `td.precaution_cm` (35 and 18 for the truck). The frontend read only `limit_cm` before. `routingResultsView.ts` now reads `td.kinds`, and falls back to the old labels when the hint is missing, has an unknown word, or its length differs from the number of paths. In 40 random pairs inside the border, about a quarter of truck pairs and a fifth of car pairs gave two options. jest (328 tests in 37 suites) and `tsc --noEmit` pass. `RoutingResults` renders from the real hint shape in a test.
3. Evidence: `evidence/US-098/` holds `two-options-recommended-1366.png`, `two-options-through-water-1366.png`, `two-options-through-water-390.png`, `one-option-1366.png`, and `two-options-fake-depth-1366.png`. The pair `21.0002,105.7798` to `21.0002,105.7317` (truck) gives two options.
4. Not checked: a flooded through-water route. The real pairs were dry at the selected step, so they read "Deepest road 0 cm", and `td.status` was `unknown` for every pair. Only `two-options-fake-depth-1366.png` is faked (depths of 3 cm and 22 cm from a faked `POST /flood/profile`). Fonts and the server rebuild are not checked. At 390x844 the legend sits beside the sheet, as set by [[US-145-stop-the-legend-from-covering-the-map-controls|US-145]].
5. Open: [[decision-log|D-021]] defines no separate no-route text, so the approved wording stays. "Via road" and more than one alternative are for the grilled story the owner asked for.
6. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows one route option, "Route 1 3 min · 0 cm", with "Route avoids flooded areas". The pair was dry, so the two-option state stays the evidence in `evidence/US-098/`. Screenshot: `evidence/server-check-2026-10-14/server-route-panel.jpg`. The owner accepted the story on 2026-10-14.
