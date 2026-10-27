---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-02-frontend-polish]]"]
---

# EP-02-frontend-polish: archived story-level history

Lines moved out of the Status history of [[EP-02-frontend-polish]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-09-23, draft.** Stories 1 and 2 built and reviewed, commits on `flood-on-points`. Both
  work in a real browser against a stub backend, and typecheck and 186 tests pass. Status is
  `Reviewed`, not `Done`, because neither has run against the live GraphHopper and flood backend.
  Story 1 adds four route requests per query, and their real latency is unmeasured.
- **2026-09-23, draft.** Story 2's legend is covered by the mobile search panel at phone width.
  Tracked as [[BL-006-mobile-flood-legend-covered-by-search-panel|mobile-flood-legend-covered-by-search-panel]]. The story stays `Reviewed`: the line
  renders, but the legend is not fully visible on mobile.
- **2026-09-24, draft.** Stories 1 and 2 done. On the live frontend at `100.67.84.55:8082`, with a
  route loaded, the profile row shows a travel time under every mode at once and the selected mode
  is bold, and the flood legend shows "Updated 24/09/2026 17:36" below the depth bands. The browser
  console had no errors. The row lists three modes, since `truck` is not in the deployed config
  ([[US-022-truck-routing-profile|truck-routing-profile]]). The mobile legend overlap remains open.
- **2026-09-24, draft.** Story 3 moved from `Done` to `Blocked`. Checking it on the live UI for
  evidence showed that place search returns no suggestions: the frontend sends `locale=vi`, Photon
  rejects that language, and the backend answers 502. See [[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]. Stories 1
  and 2 now carry evidence and details.
- **2026-09-24, draft.** Story 3's goal changes. The default locale moves from `vi` to `en`, because
  Photon rejects `vi` ([[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]). The story stays `Blocked` until place search is
  checked on the live UI after a rebuild. `en` also switches the UI labels to English, and it no
  longer biases results toward Vietnam. Check "Hồ Gươm" after the rebuild.
- **2026-09-24, draft.** The `en` default is deployed and place search works again
  ([[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]), shown in ![[frontend-en-geocoder-check.png|300]]. The story's goal,
  Vietnam-relevant results, is still unmet, so Story 3 stays `Blocked`.
- **2026-09-28, draft.** Story 3's relevance goal shipped: the backend forwards `point`/`location_bias_scale`
  to Photon and filters to `countrycode=VN` (`main` at `6429923`). Verified against the live
  `/geocode` endpoint directly. Story 3 moves from `Blocked` to `Reviewed`, not `Done`, pending a
  check through the actual browser UI. [[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]] is resolved.
- **2026-09-29, draft.** Story 4 scheduled in Sprint 3 at the user's request.
- **2026-09-30, draft.** Story 4 built and `Reviewed`. `route_error_payload()` in `server.py` passes GraphHopper's error body through, and `RouteStore.ts` clears the route on `RouteRequestFailed`. Tests: `test_route_error.py` (4) and a new `RouteStore` test, with all 208 frontend tests passing. A local run of `server.py` against a stub GraphHopper answered 400 with `message` and `hints`. Still to do: deploy, check the pair `21.014103,105.764718` to `21.014534,105.768982` on the server, and save a screenshot.
- **2026-09-30, draft.** Story 4 is `Done`. Deployed and checked on the live UI, see Details. [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]] is `resolved`.
- **2026-09-30, draft.** Story 5 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 5 is `Done`: deployed at `5d08b99` and checked on the live site.
- **2026-09-30, draft.** Story 6 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 6 is `Done`: deployed at `f87ffb9` and checked on the live site.
