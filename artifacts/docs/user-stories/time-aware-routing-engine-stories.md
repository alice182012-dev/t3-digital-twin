---
date_drafted: 2026-09-29
type: user-story
status: draft
subsystem: floodmap-backend, floodmap-frontend
source_ideas: ["[[sticky-c-lite-routing]]"]
related: ["[[time-aware-routing-engine]]", "[[sprint-plan-2]]", "[[sprint-plan-3]]", "[[frontend-polish]]", "[[edge-depth-table-stories]]", "[[routing-not-time-aware]]", "[[failed-route-shows-previous-mode-route]]", "[[departure-time-advice-research]]"]
tags: [user-story, epic, routing, graphhopper, sprint-5, sprint-6, sprint-8, sprint-9, sprint-10]
---

# Epic: time-aware routing engine (sticky C-lite)

The requirements are in [[time-aware-routing-engine]]. The depth data the engine reads is in
[[edge-depth-table-stories]]. The order of work is in [[sprint-plan-2]] (Sprints 5 to 8) and [[sprint-plan-3]] (Sprints 9 to 12).

Each row carries Priority, Status, Estimate, Sprint, and Dependencies. The base Epic shape in
[[user-story-types]] has no per-row scheduling field. This file adds those fields on purpose, as the
project's sprint-delegation convention allows. Sprint numbers continue from [[sprint-plan]], which covers
Sprints 1 to 4. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`sprint-plan-2.md` or `sprint-plan-3.md`, whichever holds the story.

- **Story R1: Record the routing baselines on the server.**
  As the team, I want the server's latency, edge count, image revision, and step length written down, so
  every later story has a real baseline instead of a guess.
  Given the running stack on the server, when the measurements run, then the blocker page lists the p50 and
  p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of
  `hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and
  count of one real run.
  Priority: P0. Status: Not started. Estimate: S. Sprint: 5. Dependencies: None.

- **Story R2: Build the synthetic scenarios, the offline reference, and the offline checker.**
  As an engineer, I want a slow reference implementation and a route checker, so the fast engine has
  something to be compared against.
  Given a synthetic flood on a real Hanoi corridor in `marie-curie/` with a throwaway PostGIS, when the
  four scenarios of [[routing-not-time-aware]] run through a time-dependent Dijkstra reference, then the
  results match the sticky column of the test table. Given any returned route, when the checker re-walks it
  with per-edge times, then it reports whether the route crosses an edge that is impassable at its arrival
  step.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 5. Dependencies: None.

- **Story R3: Show "no route" for a mode that has none.**
  As a driver, I want the app to say that my mode has no route, so I never see another mode's route under my
  mode's icon.
  Given the reproduction in [[failed-route-shows-previous-mode-route]], when the car request fails with
  `ConnectionNotFoundException`, then the map clears the previous route, the alert shows a message with text,
  and the backend passes GraphHopper's error body through in a shape `Api.ts` reads.
  This is todo 13 in [[frontend-todos-and-backend-dependencies]]. The user scheduled the same fix as
  [[frontend-polish]] Story 4 in [[sprint-plan]] Sprint 3 (2026-10-05 to 2026-10-11) on 2026-09-29, so this story is
  superseded and left out of [[sprint-plan-2]].
  Priority: P1. Status: Superseded by [[frontend-polish]] Story 4. Estimate: S. Sprint: none. Dependencies: None.

- **Story R4: Build the Java module skeleton, the image, and the CI job.**
  As an engineer, I want a module that builds against the pinned GraphHopper version and runs in our image, so
  the engine work has a place to live and a way to be tested.
  Given the pinned version and the revision from Story R1, when CI runs, then the module builds, the image
  starts with the stock profiles unchanged, and a unit test reports whether a weighting that only raises
  weights keeps LM's lower bounds valid. If the test fails, the story records that the search must run
  without LM.
  Priority: P0. Status: Not started. Estimate: L. Sprint: 6. Dependencies: Story R1.

- **Story R5: Build the time-aware weighting and search for `motorbike` and `car`.**
  As a traveller, I want the route to account for the time I reach each road, so I am not sent into water that
  floods before I arrive.
  Given a synthetic depth table in the format of [[edge-depth-table-stories]] Story E2, when the four
  scenarios run for `motorbike` and `car`, with and without a detour, then the results match the reference
  from Story R2 and the checker finds no crossing of an impassable edge. The search carries the arrival time
  in its label, applies sticky closure from the departure step with a 10-minute margin, and reads the vehicle
  limit from the profile.
  Priority: P0. Status: Not started. Estimate: L. Sprint: 8. Dependencies: Stories R2, R4, E2. Gate: the user
  confirms the sticky-from-departure wording before this sprint.

- **Story R6: Add the `truck` and `foot` time-aware profiles.**
  As a truck driver or a pedestrian, I want the same timing check for my mode, so the four modes behave alike.
  Given Story R5's engine, when `truck` and `foot` requests run on the synthetic scenarios, then each uses its
  own depth limit (35 cm and 40 cm) and passes the checker.
  Priority: P1. Status: Not started. Estimate: S. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Story R5.

- **Story R7: Integrate the engine into the backend with a flag and a fallback.**
  As an operator, I want a switch and a safe fallback, so a problem with the table never takes routing down
  or hides that timing was skipped.
  Given a depth table for the running graph, when the flag is on, then `_handle_route` uses the `td` profile,
  takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run
  for the whole request, and returns `unknown` for a trip that ends after the last step. Given the flag off,
  then the response body equals today's. Given a missing, stale, or mismatched table, then the backend routes
  with today's model and the response carries a fallback flag.
  Tests cover the flag off, a departure between steps, the horizon edge, run pinning, and the hash mismatch.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Stories R5, E5.

- **Story R8: Build `POST /route/departures`.**
  As a traveller with no route now, I want to know the earliest time a route opens, so I can decide whether to
  wait.
  Given a real depth table and a route between two points, when the endpoint runs, then it requests the
  flood-free route with `edge_id` and `time` details, reads depth by edge id, applies sticky closure from each
  candidate departure with a 10-minute margin, and returns each candidate as `clear`, `blocked`, or
  `unknown`, the earliest clear departure, the run, and the run's age. Candidates start at the step that
  contains now. The client sends no clock value, margin, or policy.
  Priority: P1. Status: Not started. Estimate: M. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Stories E2, E3, E4, R7.

- **Story R9: Show "wait until" in the no-route alert.**
  As a traveller whose route is blocked, I want the alert to say when a route opens, so I have a next step
  besides staying put.
  Given a failed route request with no connection, when the client requests `POST /route/departures`, then
  the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe
  route in the next 2 hours. Check again after the next forecast run." Given a clear route, then no advice
  appears. Given the fallback flag, then the alert shows "timing check unavailable". The alert keeps the
  existing advice to reach the safest location or stay put, and says "clear in the forecast", not "safe".
  Priority: P1. Status: Not started. Estimate: S. Sprint: 10 ([[sprint-plan-3]]). Dependencies: Story R8, and [[frontend-polish]] Story 4 in place of the superseded Story R3.

- **Story R10: Prove the engine on the server and roll it out.**
  As the team, I want evidence on the server before the flag goes on, so the change ships with numbers and not
  hopes.
  Given the deployed image and a real run, when the four scenarios run for `motorbike` and `car`, then the
  results pass the checker. Given the baseline from Story R1 and the factor the user sets, when the p50 and
  p95 of `POST /route` are measured, then both are inside the factor. Given a fixed set of pairs, when the
  same pairs run against today's model and the reference, then the percentage of pairs whose route changes
  and the median detour ratio are recorded. The concept page [[graphhopper-backend]] and
  [[routing-not-time-aware]] are updated, and the blocker moves to `resolved` only with this evidence.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 10. Dependencies: Stories R6, R7, R9, E7. Gate:
  the user sets the latency factor before this sprint.

## Status history

- **2026-09-29, draft.** Written from [[time-aware-routing-engine]]. No story has started.
- **2026-09-29, draft.** Re-cut with the plans: Stories R1 to R2, R4, and R5 stay in [[sprint-plan-2]] (Sprints 5 to 8). Stories R6 to R10
  moved to [[sprint-plan-3]] (Sprints 9 and 10). Story R3 is superseded by [[frontend-polish]] Story 4 in Sprint 3 of [[sprint-plan]].
