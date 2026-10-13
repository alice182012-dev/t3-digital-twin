---
date_drafted: 2026-10-07
type: user-story
us_id: "US-076"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P1
estimate: M
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Compare the live app with the mockup in Aside at 1366x768"
---

# US-076 Compare the live app with the mockup in Aside at 1366x768

As a product owner, I want the live app and the mockup captured side by side, so the spacing, color, and type are checked and not only the text.
Given the live app and the mockup file, when each of screens 2a to 2f and the two states the mockup lacks (no route, and "wait until") is opened in Aside at 1366x768, then each pair is saved as a screenshot, and every difference is logged as a row of this epic or as a blocker.
A difference that [[frontend-mockup-recheck-and-sprint-11-start]]
already lists (G1 to G7) is marked with its ID, not logged twice.
Dependencies: None.
It reads best after `US-055`, so the flag is on and the "wait until" alert is real.
Evidence: None yet.

## Status history

- **2026-10-10, estimate S to M.** Compared with US-024 (S for three screens).
  This story covers six screens and two missing states, so it is about three times that, with a screenshot pair for each.
- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-13, In progress.** Started as the first story of [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-13, Reviewed.** Screens 2a to 2f and the two states are captured at 1366x768 and the differences are logged in [[EP-19-frontend-against-the-mockup|EP-19]]. It waits for the owner's acceptance.

## Evidence and details

Pairs are in `artifacts/docs/stories/evidence/US-076/`: `mock-2a` to `mock-2f` and `live-2a`, `live-2b`, `live-2b-named`, `live-2c`, `live-2d`, `live-2e`, `live-2f`, `live-state-no-route`, `live-state-wait-until` (all `.jpg`).

1. What: the mockup frames come from `raw/frontend-mockups/Flood Routing Mockups v2.html`, served from a copy on `127.0.0.1`. The live app is `100.67.84.55:8082`, driven in Aside at 1366x768. The 2e shot is a route with depth badges and the chart (`21.02172,105.76616` to `21.02171,105.765886`, truck), taken with the page clock set to 2026-10-10 18:20 UTC, because the server has no raster for the current hour (`flood/forecast` answers `{"columns": []}` and the chart stays hidden).
2. Forced states: the no-route shot answers `POST /route` with a 400 `ConnectionNotFoundException` in the page, and the real `route/departures` answer is "Timing check unavailable". The wait-until shot also fakes the departures answer ("clear from 23:02"). Both show the real UI code, not a real routing failure.
3. Result: 7 gaps from the earlier list (`G1` to `G7`) are confirmed and 7 new rows (`N1` to `N7`) are in [[EP-19-frontend-against-the-mockup|EP-19]].
4. Not covered: the step list with depth per turn, and the depth badges on a long route. The shot of 2e shows the panel and the chart only.
5. Found on the way: with no raster for the hour, the chart is hidden and the mode is `LIVE` (`GET /flood/mode`), because `flood_mapping_full` is paused. A visitor sees no chart until the pipeline runs.
