---
date_drafted: 2026-10-07
type: user-story
us_id: "US-085"
story_label: "10"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Time out a route request in the client"
---

# US-085 Time out a route request in the client

As a user on a slow connection, I want a route request to end with a message, so the panel does not show loading bars for ever.
Given a route request that gets no answer, when it has waited longer than a limit the story sets from the numbers of `US-035`, then the request is cancelled, the panel shows a retry message, and the loading bars stop.
A request that answers in time is not affected.
Dependencies: None.
Blocker tracking: [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]]
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, In progress.** Started after [[US-148-show-the-place-name-in-the-destination-field|US-148]] was `Reviewed`, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

Timed out after 30 s: ![[live-timed-out.jpg|420]]
Answered in time: ![[live-normal.jpg|420]]

1. What: a pair of route requests with no answer after 30 s is cancelled, the panel shows "The route request took too long. Please try again." in the yellow box of the no-route state, and the loading bars stop. A request that answers in time is not affected.
2. How: `route()` in `floodmap/graphhopper-maps/src/api/Api.ts` wraps the request in an `AbortController` and a 30 s timer (`ROUTE_TIMEOUT_MS`). `RouteRequestFailed` carries a `timedOut` flag, `QueryStore` stores it on the sub-request, `ErrorStore` shows no error bar for it, and `routingResultsView.ts` has a new `timedOut` view that `RoutingResults.tsx` renders. The text is plain English like the no-route text, with no translation key. The tests are in `test/routing/Api.test.ts`, `test/stores/ErrorStore.test.ts`, `test/stores/QueryStore.test.ts`, and `test/sidebar/routingResultsView.test.ts`. The whole jest suite (328 tests) and `tsc --noEmit` pass on the merged tree.
3. Why 30 s: [[US-035-revalidate-loading-is-very-slow|US-035]] measured the slowest `/route` answer at 0.35 to 1.54 s, and [[BL-018-route-panel-stuck-on-loading-bars|BL-018]] saw one wait of 9 to 20 s that did not reproduce and names about 30 s. The limit sits above every wait seen, so a slow but valid answer still arrives.
4. Checked in Aside against the server backend, with the page's `fetch` overridden so that `/route` never resolves: grey loading bars at 4 s, the yellow box after about 34 s. A user retry is covered only by a unit test.
5. Found on the way: the guard `routeNumber > lastRouteNumber` in `routeWithDispatch` drops the answer of an earlier request when a later one finishes first, and the dropped request stays `SENT` for ever. That can keep the loading bars on without any timeout, and it is a likely cause of [[BL-018-route-panel-stuck-on-loading-bars|BL-018]]. It is not fixed here.
6. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows a route answer arriving without a stuck loading state. The 30 s timeout path was not rerun on the server and stays covered by the Aside check against the server backend and the unit test. Screenshot: `evidence/server-check-2026-10-14/server-route-panel.jpg`. The owner accepted the story on 2026-10-14.
