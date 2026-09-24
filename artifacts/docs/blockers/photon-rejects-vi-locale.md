---
date_open: 2026-09-24
date_closed: 
type: blocker
status: open
severity: P1
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 1
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

### Approach 1

Change the frontend default from `vi` to `en`, at the user's request, in `src/index.tsx`
(`setTranslation(locale || 'en')`). The geocoder's locale comes from that translation language, so
the request now carries `locale=en`, and Photon answers HTTP 200 for `lang=en` (checked from the
server on 2026-09-24). This is the second candidate below, done on the frontend side only.

Not yet confirmed. The frontend must be rebuilt on the server, and place search must return
suggestions on the live UI. One side effect: `setTranslation` also sets the UI language, so every
label switches from Vietnamese to English ("Từ" becomes "From", "Ô tô" becomes "Car").

## Decision and explanation

Pending confirmation on the live UI. Two candidate fixes. The second is in progress (Approach 1).

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
- **2026-09-24, monitoring.** Changed the frontend default locale to `en` (Approach 1). Waiting for a
  rebuild and a live check. Reopen if place search still fails, and note that `en` brings back the
  original concern about same-name places outside Vietnam.
- **2026-09-24, open (pending).** Deferred at the user's request. The `en` default is committed
  (`88e821b`) but not pushed, deployed, or checked on the live UI. The `TODOS.md` item stays active.
  Pick this up later by rebuilding `flood-routing-frontend` on the server and checking place search.

