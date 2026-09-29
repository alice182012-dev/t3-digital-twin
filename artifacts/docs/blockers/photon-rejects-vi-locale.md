---
date_open: 2026-09-24
date_closed: 2026-09-28
type: blocker
status: resolved
severity: P1
subsystem: floodmap-frontend
approaches_tried: 2
approaches_remaining: 0
tags: [blocker, geocoding, photon, frontend, backend]
related: ["[[frontend-polish]]", "[[graphhopper-backend]]"]
last_updated: 2026-09-28
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

Confirmed on 2026-09-24 after the frontend was rebuilt on the server. Place search returns
suggestions again, the request carries `locale=en`, and the browser console has no errors.

![[frontend-en-geocoder-check.png|500]]

Was open: relevance. The search for "Hồ Gươm" listed "Hồ Gươm Plaza" in Hanoi first, then "Ho Guom" in
Ottawa, the Hoàn Kiếm Lake third, and another "Ho Guom" in Munich. `place_search.py` passed only `q`,
`lang`, and `limit` to Photon, so the `point` and `location_bias_scale` the frontend sends were ignored.
One side effect of Approach 1 remains: `setTranslation` also sets the UI language, so every
label switches from Vietnamese to English ("Từ" becomes "From", "Ô tô" becomes "Car").

### Approach 2

Forward the frontend's existing `point` and `location_bias_scale` to Photon (splitting `point`'s
`"lat,lng"` string into Photon's separate `lat`/`lon` params), and always send `countrycode=VN`, with
a response-side backstop that drops any hit whose `properties.countrycode` isn't `VN` in case Photon
doesn't honor the request-side filter. `server.py`'s `/geocode` route parses and forwards the two new
query params, reusing `place_search.py`'s existing `_optional_number` validation so a malformed
`point` or an out-of-range `location_bias_scale` returns 400, the same as other validation errors on
this endpoint. `main` at `6429923`.

Verified live on 2026-09-28: "Hồ Gươm" now returns only Vietnam results, with "Hồ Gươm Plaza" (Hanoi)
first, "Hoàn Kiếm Lake" (Hanoi) second, and "Ho Guom Theatre" (Hanoi) third. Neither Ottawa nor Munich
appears anywhere in the response. A malformed `point` returns HTTP 400. A request with no bias (the
Enter-key path and `NavBar`'s URL resolution, neither of which sends `point`) still returns
Vietnam-only results, because the `countrycode=VN` filter doesn't depend on a bias point being
present.

## Decision and explanation

Both approaches shipped. Approach 1 fixed the 502 (an unsupported `locale` reaching Photon). Approach
2 fixed relevance (same-name places outside Vietnam outranking the real Hanoi result). The originally
proposed first candidate (map `locale` to a supported value inside `geocode_gh_shape` rather than
changing the frontend's default) was not needed: the frontend's `en` default already avoids sending an
unsupported locale, so the backend's remaining fragility to some other unsupported locale is accepted,
not revisited here.

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
- **2026-09-24, monitoring.** Deployed the `en` default (commit `6155f09`). Place search works on the live
  UI. Relevance is the remaining issue: results from Ottawa and Munich appear. Close the blocker when
  the user accepts that, or after results are biased toward Hanoi.
- **2026-09-28, resolved.** Shipped Approach 2: forward `point`/`location_bias_scale` to Photon and
  filter to `countrycode=VN` (`main` at `6429923`). Deployed and verified live: "Hồ Gươm" returns
  Hanoi-only results, ranked correctly, Ottawa and Munich no longer appear.

