---
date_open: 2026-10-02
date_closed: 
type: blocker
status: open
severity: P3
subsystem: floodmap-backend, floodmap-frontend
approaches_tried: 0
approaches_remaining: 4
tags: [blocker, frontend, places, photon, latency]
related: ["[[EP-02-frontend-polish|frontend-polish]]", "[[EP-01-frontend-depth-features|frontend-depth-features]]", "[[place-depth-popup-on-map-tap]]", "[[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]", "[[graphhopper-backend]]"]
last_updated: 2026-10-02
---

# The place name takes seconds to show after a map tap

## Description

The user reported on 2026-10-02 that after a tap on the map, the popup takes about 4 seconds to show the name of the place. The user set this to the lowest priority, to tackle later.

The popup reads the depth and the place name from two separate calls ([[place-depth-popup-on-map-tap]]): `GET /flood/points` for the depth and `GET /places/reverse` for the name. `GET /places/reverse` in `place_search.py` asks Photon, a public geocoder, for the place at that point.

## What was measured

On 2026-10-02, from the Mac, for the point 21.0250, 105.7550 (inside the model border):

| Call | Seconds (6 runs, then 3 runs) |
| ---- | -------------------------- |
| `GET /api/gh/places/reverse` on the live app | 2.13 to 2.82 |
| `GET https://photon.komoot.io/reverse` directly | 2.44 to 2.88 |

1. The backend call takes almost exactly as long as Photon alone, so the wait is Photon's answer time. The backend adds little.
2. Every call returned the same place ("Đại đội 26"), and nothing is cached, so each tap pays the full wait.
3. The user's 4 seconds is more than the 2.1 to 2.8 measured here. The browser, the network, and Photon's own variation may add to it. This is not explained.
4. `PHOTON_TIMEOUT_SECONDS` is 5 in `place_search.py`, so a slower answer than 5 seconds gives no name.

## Measured again on 2026-10-13, from the server

Run from inside `floodmap-backend`, which is the network that the backend uses.

| Measurement | Result |
| ----------- | ------ |
| `GET /places/reverse`, 6 points, first call of each | 2.97 to 4.05 s |
| The same 6 points again | 3.72 to 4.93 s (nothing is cached) |
| `GET https://photon.komoot.io/reverse` directly, 3 points | 3.9, 4.5, and 6.1 s |
| One call to Photon, split into steps (6 calls) | DNS 0.002 to 0.010 s, TCP connect 0.22 to 0.28 s, TLS 0.45 to 0.51 s, then 4.0 to 6.5 s of waiting for the first byte (median 5.9 s) |
| The same split from the Mac (6 calls) | 6.0 to 10.8 s of waiting for the first byte (median 7.9 s) |
| 12 later calls of `GET /places/reverse` | 11 answered HTTP 504 "Place search timed out" after about 5.7 s, and 1 answered in 5.6 s |

1. The wait is Photon's own processing. The connection steps take about 0.7 s together, so a keep-alive connection would save little.
2. The answer time is worse than on 2026-10-02 (2.4 to 2.9 s), and `PHOTON_TIMEOUT_SECONDS` of 5 now cuts most calls, so the popup often gets no name at all and not only a late one.
3. Caveat: these tests sent about 60 calls to a public service in about 20 minutes, and its fair-use limit may have slowed the later ones. The first run, taken before the burst, was 3.0 to 4.9 s. A public instance has no promise of speed, so the dependency is the cause in both cases.
4. Photon 1.x publishes a planet database of 63 GB and a planet JSON dump of 27 GB. The Vietnam extract of GraphHopper (`photon-db-vn-250720.tar.bz2`, 142 MB) is in the older format of July 2025. Which Photon version reads it is not verified.
5. Option D is not available: `graph_edge` has no road names, and `road_segment` is deleted by [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]].

## Why this matters

A tap shows the depth quickly and the name late, so the popup looks unfinished for a few seconds. It does not block anything else. The user rated it lowest priority.

## Approaches tried

None.

## Candidate approaches

| Option | What it does | Cost and risk |
| ------ | ------------ | ------------- |
| A. Show the coordinates at once | The popup shows the depth and the coordinates immediately, with a short "looking up the place" line that the name replaces. | XS, frontend only. Does not make the name faster. |
| B. Cache by rounded point | `floodmap-backend` keeps recent answers by the point rounded to about 4 decimals, for a day. | S. Helps repeat taps only. A first tap still waits. |
| C. Run Photon ourselves | Host a Photon index for Vietnam next to the backend, so a lookup takes milliseconds. | M to L. Needs the index download, disk, and updates. Removes the dependency on a public service. |
| D. Use local road names | Take the nearest road name from `road_segment`, and use Photon only for named places. | S to M. Fast, but gives street names, not places. A product call. |

A first, B next, and C only if the wait still matters after A and B.

## Decision and explanation

Pending. Not scheduled. The user said to tackle it later.

## Related topics

- [[place-depth-popup-on-map-tap]]
- [[EP-02-frontend-polish|frontend-polish]] Story 7 (`US-061`)
- [[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]

## Status history

- **2026-10-13, open.** Measured again from the server (section above): the wait is Photon's processing, and most calls now exceed the timeout of 5 s. The backend part is closed as far as a measurement goes. The structural fix is a Photon that we host ([[US-141-host-photon-for-vietnam-next-to-the-backend|US-141]]), and the frontend part stays with [[US-061-show-the-place-name-faster-after-a|US-061]]. No change to `approaches_remaining`.

- **2026-10-02, open.** Reported by the user: about 4 seconds from a tap to the place name. Measured 2.1 to 2.8 seconds on the backend call and 2.4 to 2.9 seconds on Photon alone, so the wait is Photon. Lowest priority, with no sprint. Story `US-061` is in the backlog of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
