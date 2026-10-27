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

Story-level progress lines up to 2026-10-10 are in [[EP-02-frontend-polish-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-23, draft.** Drafted from [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]'s Goals 2 and 6, and
  the locale fix from that PRD's Risks and open questions and Decisions sections.
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
- **2026-09-30, draft.** Story 5 added for [[BL-017-route-description-list-blanks-app|route-description-list-blanks-app]], found while checking the place popup's route button.
- **2026-09-30, draft.** Story 6 (`US-057`) added: with no connection, only the yellow "No safe route available" box shows. It refines Story 4 (`US-009`), whose criteria named the red bar.
- **2026-10-02, draft.** Story 7 (`US-061`) added, not started, with no sprint. The user reported about 4 seconds from a map tap to the place name and set it to the lowest priority. See [[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]].
