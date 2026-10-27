---
date_open: 2026-09-30
date_closed: 
type: blocker
status: monitoring
severity: P2
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 1
tags: [blocker, frontend, routing, loading, cache]
related: ["[[EP-02-frontend-polish|frontend-polish]]", "[[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]]", "[[graphhopper-backend]]"]
last_updated: 2026-10-14
---

# The route panel stayed on its grey loading bars

## Description

The user opened the route panel for Vietnam National Convention Center (Road No. 5, picked from the search
suggestions) to `21.00776,105.776798` on a motorbike. The panel showed its two grey loading bars and never
showed a route or a message. Seen on 2026-09-30, shortly after the frontend was recreated for `US-057`.

The panel shows the loading bars while any of its route requests is still marked sent. The app sends two
requests for a pair, a fast one and a slower one that asks for alternatives, and `selectRoutingResultsView`
says on purpose that "loading beats empty", so the "No safe route available" box waits for both.

## What was checked

None of this reproduced the stuck state.

- **The exact pair on the live site.** By coordinates, and by picking the "Road No. 5" suggestion and typing
  the destination, the panel showed the yellow "No safe route available" box and no loading bars.
- **Timing in the browser.** Both requests, the fast one and the alternatives one (`max_paths` 3), finished in
  about 260 ms with a 400 (no connection) for that pair.
- **The backend.** `POST /route` answered in 0.03 to 0.9 s for motorbike, car, and foot on that pair. Motorbike and
  car have no connection once the flood is applied (they do without it), and foot routes 2.5 km.
- **The servers.** No restarts and no out-of-memory kill for GraphHopper or `floodmap-backend`. GraphHopper is
  healthy. In the last 3 hours the backend logged 161 answers of 400 and 88 of 200 for `POST /route`, and its only
  errors were `BrokenPipeError`, which is a browser that closed the connection.

## Likely cause

Not confirmed. The user's guess is a stale browser page. It fits: the frontend container was recreated 9 minutes
before this was checked, and a page that was open during that moment can hold a request the browser never completes.
The code has one gap that would make such a request stick: `Api.route` has no client-side timeout, so a request that
hangs leaves the panel in "loading" until the page is reloaded.

## Approaches tried

### Approach 1: reproduce it (2026-09-30)

Steps and results are in "What was checked". It did not reproduce, so no code was changed.

## Candidate approaches

1. **Wait and watch.** A hard reload should clear a cached page. If it does not recur, close this.
2. **A timeout on the route request.** If it recurs, add an abort after about 30 seconds in `Api.route`, so the panel
   ends in a message with text and never stays on the loading bars. Frontend change, XS. Not scheduled.

## Decision and explanation

Monitoring, at the user's call. No story or sprint row yet, because nothing was fixed. If it recurs, open the
browser's Network tab first and note whether a `/route` request is still pending, and for how long.

## Related topics

- [[EP-02-frontend-polish|frontend-polish]], Stories 4 and 6 (`US-009`, `US-057`)
- [[graphhopper-backend]]

## Status history

- **2026-09-30, open.** Reported with a screenshot of the panel on its loading bars. Not reproduced, see "What was checked".
- **2026-09-30, monitoring.** The user judged it probably a cached page and asked to keep the blocker on `monitoring`.
- **2026-09-30, monitoring.** Observed on the live site with a fresh headless browser: a no-connection pair (20.999844, 105.742304 to 21.004652, 105.752604, motorbike) kept the grey loading bars for more than 9 seconds, then showed the yellow "No safe route available" box after about 20 seconds. So the bars can be a slow no-connection answer, not only a cached page. Not a fix, only a second explanation.
- **2026-09-30, monitoring.** The wait for a no-connection pair is now part of [[EP-07-carried-over-backlog|carried-over-backlog]] Story 4 (`US-035`, Sprint 4), so a measurement will confirm or rule out the slow-answer explanation.
- **2026-10-01, monitoring.** `US-035` measured the wait with Aside against port 8082. For a pair with no motorbike or truck connection, the yellow box appeared 1.5 to 2.6 s after page start in 17 loads, and the slowest of the 13 `/route` requests took 0.35 to 1.54 s. The requests start within about 10 ms of each other, so the four per-mode requests do not add up. The 9 to 20 s wait of 2026-09-30 did not reproduce. Still `monitoring`: the cause of that wait is unknown, and `Api.route` still has no timeout (candidate approach 2).
- **2026-10-14, monitoring.** While building [[US-085-time-out-a-route-request-in-the|US-085]], a worker read `routeWithDispatch` and found a path to the stuck state without any slow request. The guard `routeNumber > lastRouteNumber` drops the answer of an earlier-numbered request when a later-numbered one finishes first, and the dropped request stays `SENT`, so the panel keeps its loading bars. This is a hypothesis and was not reproduced. US-085 adds a 30 s timeout as a net, which ends the bars after the timeout but does not fix this path. The owner decides whether a story is written for it.
- **2026-10-14, monitoring.** The owner will recreate the stuck panel first and wants no story or fix before that. The hypothesis stays unproven.
