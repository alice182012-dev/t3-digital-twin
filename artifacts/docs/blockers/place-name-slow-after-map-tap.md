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
related: ["[[frontend-polish]]", "[[frontend-depth-features]]", "[[place-depth-popup-on-map-tap]]", "[[photon-rejects-vi-locale]]", "[[graphhopper-backend]]"]
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
- [[frontend-polish]] Story 7 (`US-061`)
- [[photon-rejects-vi-locale]]

## Status history

- **2026-10-02, open.** Reported by the user: about 4 seconds from a tap to the place name. Measured 2.1 to 2.8 seconds on the backend call and 2.4 to 2.9 seconds on Photon alone, so the wait is Photon. Lowest priority, with no sprint. Story `US-061` is in the backlog of [[sprint-plan-3]].
