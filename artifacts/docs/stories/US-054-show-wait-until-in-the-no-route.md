---
date_drafted: 2026-09-29
type: user-story
us_id: "US-054"
story_label: "R9"
epic: "[[EP-09-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: S
sprint: 10
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
---

# US-054 Show "wait until" in the no-route alert

As a traveller whose route is blocked, I want the alert to say when a route opens, so I have a next step
besides staying put.
Given a failed route request with no connection, when the client requests `POST /route/departures`, then
the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe
route in the next 2 hours. Check again after the next forecast run." Given a clear route, then no advice
appears. Given the fallback flag, then the alert shows "timing check unavailable". The alert keeps the
existing advice to reach the safest location or stay put, and says "clear in the forecast", not "safe".
Priority: P1. Status: Done. Estimate: S. Sprint: 10 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]). Dependencies: Story R8, and [[EP-02-frontend-polish|frontend-polish]] Story 4 in place of the superseded Story R3.
Built on 2026-10-05, tests first, in `floodmap/graphhopper-maps`. `NoSafeRouteMessage` asks `POST /route/departures` only when the failure was a missing connection (`SubRequest.noConnection`), and shows the loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe route in the next 2 hours. Check again after the next forecast run.", or "Timing check unavailable" (the table is unavailable, the request fails, or no step could be judged). The base message and its advice stay. 25 new tests, 304 in all pass, `tsc` is clean, and the production build compiles. Plan: [[wait-until-alert]].
Evidence: ![[us-054-wait-until-alert-browser-2026-10-07.png]]
Details:
1. On 2026-10-07, host ADMIN, drove the deployed frontend (`localhost:8082`) by hand: typed coordinates `21.0215, 105.7610` to `21.0230, 105.7650` (a pair noted elsewhere as flaky, since the flood state changes run to run) as start/destination for `motorbike`.
2. `POST /route` failed (400, no connection), and the frontend automatically called `POST /route/departures`, which answered 200.
3. The alert rendered exactly the acceptance text: "No safe route available. Please consider getting to the safest location or stay where you are." and "No safe route in the next 2 hours. Check again after the next forecast run." — the no-clear-departure variant, since every candidate in the window was blocked.
4. Driving the UI needed real keystrokes (`type`, not a programmatic `fill`) and a fresh `Control+a`/`Backspace`/retype cycle per field; the app's address input only accepts a direct lat/lon pair after a real input event and `Enter`, and URL `?point=` params alone did not trigger routing.
