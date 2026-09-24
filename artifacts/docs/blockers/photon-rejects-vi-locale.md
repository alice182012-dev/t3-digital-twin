---
date_open: 2026-09-24
date_closed: 
type: blocker
status: open
severity: P1
subsystem: floodmap-frontend
approaches_tried: 0
approaches_remaining: 2
tags: [blocker, geocoding, photon, frontend, backend]
related: ["[[frontend-polish]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-24
---

# Photon rejects the vi locale, so place search fails

## Description

Place search returns no suggestions on the live frontend. Every query fails, not only Vietnamese
ones.

The frontend sends `locale=vi` (the fix in [[frontend-polish]]'s Story 3).
`floodmap/graphhopper-flood-road/backend/place_search.py` passes that value to Photon unchanged, as
`lang=vi` (in `geocode_gh_shape`). Photon accepts only four languages and answers HTTP 400:

`{"lang":[{"message":"Language is not supported. Supported are: default, de, en, fr","value":"vi"}]}`

The backend catches the `HTTPError` and raises `PlaceSearchUnavailable`, so the frontend receives a
502 with "Place search is temporarily unavailable." The same request with `lang=default` or
`lang=en` returns HTTP 200 from the server. This was checked on 2026-09-24 from inside the
`floodmap-backend` container.

![[frontend-vi-geocoder-check.png|500]]

The screenshot shows "Hồ Gươm" typed into the live search box with no suggestion list. The browser's
network log for that request shows `locale=vi` and the correctly encoded query, then a 502.

## Why this matters

A user cannot find a place by name. Entering coordinates still works. The story that introduced the
change was marked done without a check on the live server, because it needed a frontend rebuild
that had not happened yet.

## Approaches tried

None yet.

## Decision and explanation

Pending. Two candidate fixes, neither tried.

1. Map the locale in `geocode_gh_shape`: pass `locale` to Photon only when it is `default`, `de`,
   `en`, or `fr`, and otherwise send `default`. This fixes every unsupported locale, and it needs a
   backend rebuild.
2. Change the frontend to send `locale=default`. This is a one-line change but leaves the backend
   fragile to any other unsupported locale.

The first candidate is safer, since the backend is the component that knows what Photon supports.

## Concerns

`lang=default` ranks results by Photon's own rules, not by Vietnamese relevance. The original
problem was same-name places outside Vietnam appearing in suggestions. The fix may need a location
bias as well, so check "Hồ Gươm" after the change and confirm the Hanoi lake is the first result.

## Related topics

- [[frontend-polish]], Story 3
- [[graphhopper-backend]]

## Status history

- **2026-09-24, open.** Found while capturing evidence for [[frontend-polish]]'s Story 3, which was
  marked done without a live check. Confirmed in the browser, in the backend log, and against Photon
  directly.
