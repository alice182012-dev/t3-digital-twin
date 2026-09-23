---
date_drafted: 2026-09-23
type: user-story
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[flood-routing-mockup-frontend-gap]]", "[[sprint-plan]]", "[[mobile-flood-legend-covered-by-search-panel]]"]
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
  Priority: P2. Status: Reviewed. Estimate: M. Sprint: 1. Dependencies: None. Known risk: four separate route
  requests per query may add visible delay. Accepted for now since this isn't shown to real users
  yet (see [[flood-routing-mockup-frontend-gap]]'s Decisions).

- **Story 2: Add the "Updated `date` `time`" line to the flood legend.**
  As a user reading the flood legend, I want to know how current the flood-depth data is, so I can
  judge whether the map reflects the latest simulation cycle.
  Given flood mode is on, when the legend renders, then it shows an "Updated" line below the color
  bands with the selected timestep's date and time.
  Priority: P2. Status: Reviewed. Estimate: S. Sprint: 1. Dependencies: None.

- **Story 3 (done): Switch the search geocoder's default locale to `vi`.**
  As a user searching for a Vietnamese address, I want Vietnam-relevant results, so I'm not shown
  same-name places outside Vietnam mixed into the suggestion list.
  Given the search input's autofill geocoding, when a query like "Hồ Gươm" is typed, then the
  results are correctly encoded and prioritize Vietnam-relevant matches instead of mixing in
  unrelated same-name places elsewhere. Verified live against `http://100.67.84.55:8082` before the
  code fix (correct encoding, wrong relevance). Not yet re-verified after the fix, which needs a
  rebuild and redeploy on the remote host.
  Priority: P2. Status: Done. Estimate: S. Sprint: 1 (completed outside formal sprint tracking, 2026-09-23).
  Dependencies: None.

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
