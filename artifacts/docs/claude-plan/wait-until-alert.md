---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-10, frontend, alert, departures, us-054]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[route-departures-endpoint]]", "[[frontend-polish]]", "[[departure-time-advice-research]]", "[[sprint-plan-3]]"]
---

# Plan: show "wait until" in the no-route alert (US-054)

## Context

Acceptance, from [[time-aware-routing-engine-stories]] Story R9. Given a failed route request with no connection, the client asks `POST /route/departures`, and the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe route in the next 2 hours. Check again after the next forecast run." Given a clear route, no advice appears. Given the fallback flag, the alert shows "timing check unavailable". The alert keeps its advice to reach the safest location or stay put, and says "clear in the forecast", not "safe".

The alert is `NoSafeRouteMessage`, the box of [[frontend-polish]] Story 4 (`US-009`), shown when the route view is `empty`.

## Design

1. **Only a missing connection asks.** The view is also `empty` after a timeout or a server error, and advice for those would mislead. `SubRequest` now remembers `noConnection` (set from `RouteRequestFailed`), and `noConnectionTarget` gives the failed request's points and profile only when every sub-request has finished, none succeeded, and the failure was a missing connection.
2. **The request** carries the points and the profile. The clock, the margin, and the limit are the server's.
3. **The text** comes from `adviceFromAnswer`: `clear_from` (the earliest clear `leave_at`, as HH:MM in the viewer's zone, and the run's HH:MM from its name), `none` (no clear step, and at least one step shown blocked), or `unavailable` (the server says so, the request fails, the body is not an answer, or no step could be judged). A forecast that could not judge any step gives no verdict, so the box says the timing check is unavailable and does not claim the route is closed.
4. **Never hide the alert.** A failed or slow advice request leaves the base message in place. A new pair of points asks again and clears the old advice. Leaving the box aborts the request.
5. **Wording.** The strings of the story are used as written. "Safe" appears only in the second string, which the acceptance quotes. The first states a forecast: "clear from".

## Steps

Tests first.

1. Pure functions and the loader in `src/floodmap/departureAdvice.ts` (19 tests).
2. `QueryStore` remembers `noConnection` (1 new test).
3. `NoSafeRouteMessage.tsx` and its states (5 tests with a fake `fetch`), wired into `RoutingResults`.
4. `tsc` and the production build.

## Risks

- **Time zones.** The run label is the HH:MM of the run name, which is Hanoi time, and the clear time is in the viewer's zone. For a viewer outside Vietnam the two can differ. The map's own captions already use the viewer's zone, so the same limit applies there.
- **The fallback flag.** The box shows "Timing check unavailable" when the table is unavailable. `td.status: fallback` on a successful route is not shown in this story, because the story ties the message to the no-route alert.
- **The endpoint on a real route** is proved in `US-055`.

## Status history

- **2026-10-05, active.** Plan written and built, tests first. 25 new frontend tests, 304 in all pass, `tsc` is clean, and the production build compiles. Three changes each fail a test: advice for any failure, a verdict claimed with no blocked step, and a swallowed abort. Left: the check on the server in `US-055`.
