---
date: 2026-10-07
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, frontend, mockup, sprint-11, todos]
related: ["[[mockup-screen-coverage]]", "[[flood-routing-mockup-frontend-gap]]", "[[sprint-plan-3]]", "[[routing-first-consumer-contract]]", "[[map-shows-forecast-not-now]]", "[[route-panel-stuck-on-loading-bars]]", "[[decision-log]]"]
---

# Plan: start Sprint 11, recheck the frontend against the mockup

## Context

On 2026-10-07 the user asked for three things: start Sprint 11 today, compare the current frontend with the mockup, and check the plan for missing work. The 48-hour replay ends at 00:00 +07 on 2026-10-08, and no image builds on the server until then. So today's work is local and read-only on the server.

## How the comparison was done

The mockup is `artifacts/raw/frontend-mockups/Flood Routing Mockups v2.dc.html`. I read its text, which has six screens (2a to 2f) and a "Try next" line. I did not open it in a browser, and I did not open the live app. I compared the mockup text with the code in `floodmap/graphhopper-maps/src` and with the stories in [[mockup-screen-coverage]], [[frontend-polish]], and [[frontend-depth-features]]. Spacing, color, and type were not compared. A browser pass at 1366x768 is the next step if you want those checked.

The mockup's six screens already have stories, and all of them are `Done` (`US-002` to `US-010`, `US-023` to `US-026`, `US-057` to `US-059`). The differences that follow are the ones no story records.

## Differences with no story

| Id | Mockup | App | Evidence |
| -- | ------ | --- | -------- |
| G1 | The depth chart has 5 columns of 30 minutes and labels only the full hours. | The chart has 8 columns of 15 minutes and labels every column with `HH:MM`. | `FORECAST_STEPS = 8` in `DepthForecastChart.tsx`, `FORECAST_STEP_MS` in `depthForecast.ts`. The PRD decision of 2026-09-23 says "30 minutes, matching the mockup". The pipeline later moved to 15 minutes, and no story records the chart change. |
| G2 | Screen 2e puts the names of the start and the destination on the map pins ("GO Thăng Long", "FPT Shop"). | The pins carry no text. | `layers/UseQueryPointsLayer.tsx` and `map/Marker.tsx` have no label code. |
| G3 | Route tabs read "Via Phạm Hùng". | A tab shows `path.description`, or "Route N" when the text is missing or repeated. | `buildRouteTabs` in `sidebar/routingResultsView.ts`. |
| G4 | The page and the search pill say "Floodmap". | The pill says "Search Floodmap", but the page title and `og:title` say "GraphHopper Maps | Route Planner", and the empty panel shows "Powered by GraphHopper". | `src/index.html` lines 17 and 31. [[mockup-screen-coverage]] Story 3 left the panel extras as a product call. |
| G5 | The legend line reads "Updated `date` `time`". | It reads "As of `time`" or "Forecast for `time`". The `US-007` screenshot still shows "Updated". | `timestepLabel.ts`. Open product call in [[map-shows-forecast-not-now]]. |
| G6 | "Try next" lists a second dashed line for the selected mode's depth limit, route tabs with time and maximum depth, and a mobile version of 2e. | None of the three exists. | [[mockup-screen-coverage]] "Not scheduled". The engine now has per-mode limits (`truck` 35 cm, `foot` 40 cm in `config.yml`), so the dashed line has data. |
| G7 | The mockup has no state for "no route" and no "wait until" advice. | `US-009`, `US-057`, and `US-054` added them. Nobody has compared their wording or layout with a design. | [[frontend-polish]] Stories 4 and 6, [[wait-until-alert]]. |

Differences that are on purpose, and stay as they are: the app opens in Flood mode (D-008 in [[decision-log]]), and the legend has seven bands instead of five (PRD decision of 2026-09-23).

## Gaps in the plan

1. No Sprint 11 story touches the frontend. `US-033` (`DESIGN.md`) extracts tokens from the shipped UI, so it should come after any story that changes the UI. Otherwise the file records tokens that change a week later.
2. `Api.route` has no client timeout, and [[route-panel-stuck-on-loading-bars]] is `monitoring` with no story. `US-035` measured it and left it open.
3. `US-072` and `US-073` can be built today, but their server evidence waits for `US-055`, which waits for the end of the replay. They cannot reach `Done` before 2026-10-08.
4. `US-055` is the proof that turns `US-051` to `US-054` from `Reviewed` to `Done`. Its runbook builds the frontend, so a browser pass with the flag on is the place to check G7.
5. `TODOS.md` still held 17 `Done` items from 2026-10-05 and earlier. The next-day rule says they go. They were deleted in this pass.

## Candidate stories

The user chose, on 2026-10-07, to make every candidate a story in Sprint 12, and to add a browser comparison in Aside. They are now `US-076` to `US-085` in [[frontend-mockup-recheck-stories]]. The mapping is in the status history. The text below is the original list.

1. G1 and G3 together: match the chart columns and the tab text to screen 2e (S).
2. G2: show the place names on the start and destination pins (S).
3. G4: rename the page title and `og:title`, and decide on the "Powered by" line (XS, needs your call on the line).
4. G5: decide "Updated" or "As of", then retake the `US-007` screenshot (XS, needs your call).
5. G6: a second dashed line for the selected mode's limit (S). Tabs with time and maximum depth (S). A mobile 2e (M).
6. G7: write down a design for the no-route and "wait until" states, then match the UI to it (S).
7. Route timeout: add a client timeout to `Api.route` and close [[route-panel-stuck-on-loading-bars]] (S).

## Order today

1. Start Sprint 11 in [[sprint-plan-3]] and move its six rows into `TODOS.md`. Done in this pass.
2. Ask which candidate stories to schedule, and in which sprint.
3. Build `US-071` first, then `US-075` and `US-074`, when you say go.
4. Read the 24-hour storage and timing numbers on the server for `US-069` and `US-045`, run by you.

## Status history

- **2026-10-07, active.** Plan written. Sprint 11 started, `TODOS.md` rolled over, and the comparison recorded. No story added.
- **2026-10-07, active.** The user decided: all candidates become stories in Sprint 12, "Powered by GraphHopper" goes if possible, the legend keeps "As of" (D-010), and a browser comparison in Aside joins Sprint 12. Stories written: `US-076` (Aside comparison), `US-077` (candidate 1, G1 and G3), `US-078` (candidate 2, G2), `US-079` (candidate 3, G4), `US-080` (candidate 4, G5), `US-081`, `US-082`, and `US-083` (candidate 5, the three "Try next" lines), `US-084` (candidate 6, G7), and `US-085` (candidate 7, the route timeout). The next free ID is `US-086`.
- **2026-10-07, active.** The user confirmed two follow-ups. `US-033` (`DESIGN.md`) moved from Sprint 11 to the last place in Sprint 12, after the UI stories. `US-079` also removes the settings box links to `graphhopper.com`. Sprint 11 now has five rows.
