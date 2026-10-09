---
date_drafted: 2026-09-23
type: user-story
us_id: "US-008"
story_label: "3"
epic: "[[EP-02-frontend-polish]]"
status: Reviewed
priority: P2
estimate: S
sprint: 1
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Switch the search geocoder's default locale to `vi`"
---

# US-008 Switch the search geocoder's default locale to `vi`

As a user searching for a Vietnamese address, I want Vietnam-relevant results, so I'm not shown
same-name places outside Vietnam mixed into the suggestion list.
Given the search input's autofill geocoding, when a query like "Hồ Gươm" is typed, then the
results are correctly encoded and prioritize Vietnam-relevant matches instead of mixing in
unrelated same-name places elsewhere. Verified live against `http://100.67.84.55:8010/geocode`
directly (2026-09-28): "Hồ Gươm" returns only Hanoi results, ranked correctly, with Ottawa and
Munich gone. Not yet re-verified through the actual browser UI at `100.67.84.55:8082`, only against
the backend endpoint the frontend calls, so the story stays `Reviewed`, not `Done`.
Priority: P2. Status: Reviewed. Estimate: S. Sprint: 1 (completed outside formal sprint tracking, 2026-09-23).
Dependencies: None.
Evidence: ![[frontend-vi-geocoder-check.png|420]]
Details:
1. What: the geocode backend now forwards the frontend's existing `point`/`location_bias_scale` to
   Photon and filters to `countrycode=VN`.
2. How: `place_search.py`'s `geocode_gh_shape()` and `server.py`'s `/geocode` route, `main` at `6429923`.
3. Why: Vietnam-relevant suggestions, and no unsupported-locale 502.
4. Effect: place search works on the live UI (locale fix) and now also ranks Vietnam results correctly
   (relevance fix). See [[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]] (resolved).
