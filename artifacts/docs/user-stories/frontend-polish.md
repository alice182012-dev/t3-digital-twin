---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[sprint-plan]]", "[[mobile-flood-legend-covered-by-search-panel]]", "[[photon-rejects-vi-locale]]"]
tags: [user-story, epic, frontend, sprint-1]
---

# Epic: frontend polish, no backend dependency

The two [[flood-routing-mockup-frontend-gap]] goals that need no new backend endpoint, plus one
already-shipped fix logged for traceability. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- **Story 1: Add per-mode travel time under the four mode icons.**
  As a user comparing routes, I want a travel time under each of the four mode icons at once, so I
  can compare modes without selecting each one in turn.
  Given a route exists between two points, when the route result renders, then each of the four mode
  icons in the profile row shows a travel time below it, and the selected mode's time is visually
  distinguished (bold, matching mockup screen 2e), without the user selecting each mode in turn to
  see its time.
  Priority: P2. Status: Done. Estimate: M. Sprint: 1. Dependencies: None. Known risk: four separate route
  requests per query may add visible delay. Accepted for now since this isn't shown to real users
  yet (see [[flood-routing-mockup-frontend-gap]]'s Decisions).
  Evidence: ![[frontend-per-mode-travel-time.png|420]]
  Details:
  1. What: a travel time under each mode icon, with the selected mode in bold.
  2. How: `useProfileTimes` sends one route request per profile for each query.
  3. Why: compare modes without switching.
  4. Effect: four requests per query. Truck is missing until Sprint 4, and every mode uses the motorbike flood limit ([[flood-routing-vehicle-type-always-motorbike]]).

- **Story 2: Add the "Updated `date` `time`" line to the flood legend.**
  As a user reading the flood legend, I want to know how current the flood-depth data is, so I can
  judge whether the map reflects the latest simulation cycle.
  Given flood mode is on, when the legend renders, then it shows an "Updated" line below the color
  bands with the selected timestep's date and time.
  Priority: P2. Status: Done. Estimate: S. Sprint: 1. Dependencies: None.
  Evidence: ![[frontend-legend-updated-line.png|420]]
  Details:
  1. What: an "Updated" line under the legend bands.
  2. How: `FloodLegend` formats the selected timestep with `formatTimestepTime`, in the viewer's local time.
  3. Why: it shows how current the flood data is.
  4. Effect: the legend is one line taller, and the mobile search panel covers it ([[mobile-flood-legend-covered-by-search-panel]]).

- **Story 3 (blocked): Switch the search geocoder's default locale to `vi`.**
  As a user searching for a Vietnamese address, I want Vietnam-relevant results, so I'm not shown
  same-name places outside Vietnam mixed into the suggestion list.
  Given the search input's autofill geocoding, when a query like "Hồ Gươm" is typed, then the
  results are correctly encoded and prioritize Vietnam-relevant matches instead of mixing in
  unrelated same-name places elsewhere. Verified live against `http://100.67.84.55:8082` before the
  code fix (correct encoding, wrong relevance). Not yet re-verified after the fix, which needs a
  rebuild and redeploy on the remote host.
  Priority: P2. Status: Blocked. Estimate: S. Sprint: 1 (completed outside formal sprint tracking, 2026-09-23).
  Dependencies: None.
  Evidence: ![[frontend-vi-geocoder-check.png|420]]
  Details:
  1. What: the frontend sends `locale=vi` to the geocoder.
  2. How: the request now carries `locale=vi` with the accents encoded correctly.
  3. Why: Vietnam-relevant suggestions.
  4. Effect: place search fails on the live UI, because Photon rejects `lang=vi` and the backend answers 502. See [[photon-rejects-vi-locale]].

## Status history

- **2026-09-23, draft.** Drafted from [[flood-routing-mockup-frontend-gap]]'s Goals 2 and 6, and
  the locale fix from that PRD's Risks and open questions and Decisions sections.
- **2026-09-23, draft.** Stories 1 and 2 built and reviewed, commits on `flood-on-points`. Both
  work in a real browser against a stub backend, and typecheck and 186 tests pass. Status is
  `Reviewed`, not `Done`, because neither has run against the live GraphHopper and flood backend.
  Story 1 adds four route requests per query, and their real latency is unmeasured.
- **2026-09-23, draft.** Story 2's legend is covered by the mobile search panel at phone width.
  Tracked as [[mobile-flood-legend-covered-by-search-panel]]. The story stays `Reviewed`: the line
  renders, but the legend is not fully visible on mobile.
- **2026-09-24, draft.** Stories 1 and 2 done. On the live frontend at `100.67.84.55:8082`, with a
  route loaded, the profile row shows a travel time under every mode at once and the selected mode
  is bold, and the flood legend shows "Updated 24/09/2026 17:36" below the depth bands. The browser
  console had no errors. The row lists three modes, since `truck` is not in the deployed config
  ([[truck-routing-profile]]). The mobile legend overlap remains open.
- **2026-09-24, draft.** Story 3 moved from `Done` to `Blocked`. Checking it on the live UI for
  evidence showed that place search returns no suggestions: the frontend sends `locale=vi`, Photon
  rejects that language, and the backend answers 502. See [[photon-rejects-vi-locale]]. Stories 1
  and 2 now carry evidence and details.
- **2026-09-24, draft.** Story 3's goal changes. The default locale moves from `vi` to `en`, because
  Photon rejects `vi` ([[photon-rejects-vi-locale]]). The story stays `Blocked` until place search is
  checked on the live UI after a rebuild. `en` also switches the UI labels to English, and it no
  longer biases results toward Vietnam. Check "Hồ Gươm" after the rebuild.
- **2026-09-24, draft.** The `en` default is deployed and place search works again
  ([[photon-rejects-vi-locale]]), shown in ![[frontend-en-geocoder-check.png|300]]. The story's goal,
  Vietnam-relevant results, is still unmet, so Story 3 stays `Blocked`.
- **2026-09-25, draft.** Story 2's "Updated" line shows the selected timestep's time, which is a forecast, so it can read as a future
  time (for example "Updated 21:40" at 21:22). Tracked as [[map-shows-forecast-not-now]]. The story stays `Done` against its
  written criteria, and its label may change once the team decides what the map shows.

