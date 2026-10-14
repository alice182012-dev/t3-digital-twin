---
date_drafted: 2026-10-12
type: user-story
us_id: "US-131"
title: "Show the demo flood banner and the pinned frame"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P2
estimate: M
sprint: 15
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]", "[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[test-dataset]]"]
tags: [user-story]
---

# US-131 Show the demo flood banner and the pinned frame

As a visitor, I want a warning and a still frame of the demo flood when no flood is forecast, so I know the map shows a past storm.

Part four of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], and the only part that is frontend work, so it is not in the backend sprint.
The map reads the mode from [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]].
In `DEMO` mode it shows the pinned frame with no slider and no animation, and the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.
In `PENDING` mode it shows a dry map and a warning that the simulation is running.

Given mode `DEMO`, when a visitor opens the flood map, then the pinned frame and the exact warning show.
Given mode `PENDING`, then the map is dry and the warning says the simulation is running.
Given mode `LIVE`, then the map shows the real result as today.

Dependencies: [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] is `Done`.

## Acceptance check

On the server, with a screenshot of each mode.

## Status history

- **2026-10-12, draft.** Split from [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]. It stays in the backlog because it is frontend work and the sprint covers the backend.
- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started after [[US-081-draw-a-second-dashed-line-for-the|US-081]] was `Reviewed` and US-149 was `Blocked`, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build with the answer of `GET flood/mode` faked in the page, because the server answers `LIVE`. It waits for the one frontend rebuild on the server, the owner's decision on the date, and the owner's acceptance.

## Evidence and details

`DEMO`: ![[local-demo.jpg|420]]
`PENDING`: ![[local-pending.jpg|420]]
`LIVE`: ![[local-live.jpg|420]]
`DEMO` at 390x844: ![[local-mob.jpg|420]]

1. What: in `DEMO` mode the map shows the pinned step and an amber card at the bottom centre reads "No flood forecasted, displaying the demo flood of Oct 10, 2026". In `PENDING` mode the map draws no flood layer and the card reads "The flood simulation is running. The map stays dry until it finishes.". In `LIVE` mode nothing changes and no card shows.
2. How: `src/floodmap/floodMode.ts` holds the typed union `FloodMode` (`LIVE`, `PENDING`, `DEMO` with the pinned step), `parseFloodMode`, and `floodView(mode)`, which returns the banner text and whether the flood layer draws. `FloodStore.ts` reads `flood/mode` first in `loadFloodTimesteps`. In `DEMO` it replaces the timestep list with the pinned step and converts its time to +07:00, because the tile folders are named by local time. `FloodBanner.tsx` and its CSS draw the card, and `App.tsx` renders it in both layouts. The tests are in `test/floodmap/floodMode.test.ts` and `test/floodmap/FloodStore.test.ts`. The whole jest suite (346 tests) and `tsc --noEmit` pass on the merged tree.
3. The frontend has no slider, play button, or animation anywhere (a search for them in the flood UI finds none), so "no slider and no animation" holds without code.
4. The date: the backend's `DEMO` answer carries the pinned step (`valid_time` `2026-10-10T19:00:00+00:00`, run `20261011T001500`). The banner shows its UTC date, "Oct 10, 2026", and falls back to the story's "Sep 16, 2026" only when the answer has no pinned step. The legend caption beside it reads "As of 11/10/2026 02:00" (local time), so the two dates disagree on screen. The owner decides the wording and whether the banner shows the UTC or the local date.
5. Not checked: the flood frame itself (the tile server is not reachable from the Mac, so only the tile URLs of the pinned run were confirmed), a screenshot at 1366x768 (the Aside window was 1440x900), and a real `DEMO` or `PENDING` answer from the server. The 390x844 shot uses an iframe of that size, and the mobile offset assumes a legend of about 220 px.
6. Left for `Done`: the server rebuild, a screenshot of each mode on the server (the server needs a `DEMO` and a `PENDING` row in `forecast_mode`, which is the owner's call), and the update of [[floodmap-frontend]].
