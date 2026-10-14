---
date_drafted: 2026-10-07
type: user-story
us_id: "US-082"
story_label: "7"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P3
estimate: M
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the travel time and the maximum depth on each route tab"
---

# US-082 Show the travel time and the maximum depth on each route tab

As a user choosing between routes, I want each tab to show its time and its deepest water, so I pick one without opening each.
Given a route with alternatives, when the tabs render, then each tab shows the road name, the travel time, and the maximum depth along that route in centimetres.
Dependencies: Story 2 (the tab text).
The depth comes from `POST /flood/profile` for each alternative, so check the cost of one request per tab first.
Covers the second "Try next" line (G6).
Evidence: see below.

## Status history

- **2026-10-10, estimate S to M.** Compared with US-006 (M: a travel time for each of four modes, one request each).
  One depth request for each tab has the same shape, and the cost of those requests is unknown.
- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, In progress.** Started after [[US-081-draw-a-second-dashed-line-for-the|US-081]] was `Reviewed` and US-149 was `Blocked`, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance. The screenshot shows one tab on a dry route.

## Evidence and details

![[live-tab-time-depth.jpg|420]]

1. What: each route tab shows its label and, on a second line, its travel time and its maximum depth in centimetres, for example "3 min · 0 cm". With no depth yet, the tab shows the time alone and is never blocked. A tab with no road description still reads "Route N".
2. Cost check, done first: the `/route` answer carries no depth per path (its `hints` hold `td.limit_cm`, `td.precaution_cm`, `td.status`, `td.run`, and `td.kinds`), so one `POST /flood/profile` per alternative is needed. On the server, one request took a median of 113 ms (worst 247 ms, 10 runs), and three in parallel took a median of 117 ms for the whole batch (worst 215 ms, 8 runs). The timestep was `2026-10-11T00:45+07`, which has a raster, and the route is dry at that step, but the query cost does not depend on depth. No backend change is needed.
3. How: `maxDepthCm(samples)` in `src/floodmap/depthBadges.ts` returns the deepest sample in whole centimetres. `useDepthProfile.ts` fetches once per route and timestep and caches the promise (up to 50 entries, a failed request is not cached), so the depth badges and the tabs share the request, and `useMaxDepthsCm` fires all alternatives in parallel. `buildRouteTabs` in `src/sidebar/routingResultsView.ts` builds the `detail` text, and `RouteTabs.tsx` and `RoutingResult.module.css` show it on a second line. One behaviour change: the request is no longer aborted when the component unmounts. The whole jest suite (336 tests) and `tsc --noEmit` pass on the merged tree.
4. Not checked: several tabs in the browser (the server answered one path, so that case is covered by unit tests only), a non-zero depth in the browser, and a change of the flood step end to end. The tab shows no road name in the screenshot because the route answer has no description (see the owner's question about "Via road" in [[TODOS]]).
5. Left for `Done`: the server rebuild, a server screenshot, and the update of [[floodmap-frontend]].
