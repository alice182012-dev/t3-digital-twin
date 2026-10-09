---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-006", "US-007", "US-008", "US-009", "US-010", "US-057", "US-061"]
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[BL-006-mobile-flood-legend-covered-by-search-panel|mobile-flood-legend-covered-by-search-panel]]", "[[BL-008-photon-rejects-vi-locale|photon-rejects-vi-locale]]"]
tags: [user-story, epic, frontend, sprint-1]
---

# Epic: frontend polish, no backend dependency

The two [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]] goals that need no new backend endpoint, plus one
already-shipped fix logged for traceability. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- [[US-006-add-per-mode-travel-time-under-the|US-006]] Add per-mode travel time under the four mode icons. Story 1.
- [[US-007-add-the-updated-date-time-line-to|US-007]] Add the "Updated `date` `time`" line to the flood legend. Story 2.
- [[US-008-switch-the-search-geocoder-s-default-locale|US-008]] Switch the search geocoder's default locale to `vi`. Story 3.
- [[US-009-show-no-route-and-a-clear-message|US-009]] Show no route and a clear message when the selected mode has none. Story 4.
- [[US-010-do-not-blank-the-app-when-a|US-010]] Do not blank the app when a route description is a list. Story 5.
- [[US-057-show-only-the-no-safe-route-available|US-057]] Show only the "No safe route available" box when a mode has no connection. Story 6.
- [[US-061-show-the-place-name-faster-after-a|US-061]] Show the place name faster after a map tap. Story 7.

## Status history

- **2026-09-23, draft.** Drafted from [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]'s Goals 2 and 6, and
  the locale fix from that PRD's Risks and open questions and Decisions sections.
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
- **2026-09-25, draft.** Story 2's "Updated" line shows the selected timestep's time, which is a forecast, so it can read as a future
  time (for example "Updated 21:40" at 21:22). Tracked as [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]. The story stays `Done` against its
  written criteria, and its label may change once the team decides what the map shows.
- **2026-09-29, draft.** Story 2's caption no longer says "Updated". `timestepLabel.ts` returns
  "As of `time`" for a step at or before now and "Forecast for `time`" for a future step, because
  the timestep shows when the data is valid, not when it was updated. The written criteria and the
  evidence screenshot still show "Updated". Retake the screenshot if the story is to stay `Done`,
  and confirm the wording against the mockup with the user ([[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]).
- **2026-09-28, draft.** Story 2's mobile overlap is fixed: the legend moved to bottom-right on
  mobile (`main` at `e5b155a`). Verified live at 390x844 (full legend visible) and 1440x900 (desktop
  unchanged). [[BL-006-mobile-flood-legend-covered-by-search-panel|mobile-flood-legend-covered-by-search-panel]] is resolved.
- **2026-09-29, draft.** Story 4 added: the scenario from [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]], kept as the
  acceptance test for the fix. It is unscheduled until the user picks a sprint.
- **2026-09-29, draft.** Story 4 scheduled in Sprint 3 at the user's request.
- **2026-09-30, draft.** Story 4 built and `Reviewed`. `route_error_payload()` in `server.py` passes GraphHopper's error body through, and `RouteStore.ts` clears the route on `RouteRequestFailed`. Tests: `test_route_error.py` (4) and a new `RouteStore` test, with all 208 frontend tests passing. A local run of `server.py` against a stub GraphHopper answered 400 with `message` and `hints`. Still to do: deploy, check the pair `21.014103,105.764718` to `21.014534,105.768982` on the server, and save a screenshot.
- **2026-09-30, draft.** Story 4 is `Done`. Deployed and checked on the live UI, see Details. [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]] is `resolved`.
- **2026-09-30, draft.** Story 5 added for [[BL-017-route-description-list-blanks-app|route-description-list-blanks-app]], found while checking the place popup's route button.
- **2026-09-30, draft.** Story 5 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 5 is `Done`: deployed at `5d08b99` and checked on the live site.
- **2026-09-30, draft.** Story 6 (`US-057`) added: with no connection, only the yellow "No safe route available" box shows. It refines Story 4 (`US-009`), whose criteria named the red bar.
- **2026-09-30, draft.** Story 6 built and `Reviewed`. See Details.
- **2026-09-30, draft.** Story 6 is `Done`: deployed at `f87ffb9` and checked on the live site.
- **2026-10-02, draft.** Story 7 (`US-061`) added, not started, with no sprint. The user reported about 4 seconds from a map tap to the place name and set it to the lowest priority. See [[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]].
