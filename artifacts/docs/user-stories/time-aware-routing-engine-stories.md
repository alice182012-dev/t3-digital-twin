---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-046", "US-047", "US-048", "US-049", "US-050", "US-051", "US-052", "US-053", "US-054", "US-055"]
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

- **Story R1 (US-046): Record the routing baselines on the server.**
  As the team, I want the server's latency, edge count, image revision, and step length written down, so
  every later story has a real baseline instead of a guess.
  Given the running stack on the server, when the measurements run, then the blocker page lists the p50 and
  p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of
  `hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and
  count of one real run.
  Priority: P0. Status: Done. Estimate: S. Sprint: 5. Dependencies: None. The latency numbers waited for the `US-037` knob, which settled on 2026-10-02.
  Evidence: ![[us-046-baselines-check-output.png|700]]
  Details:
  1. What: the server's baselines are written in "Baselines on the server" of [[routing-not-time-aware]]. The graph has 67,833 edges, the image's source is GraphHopper commit `d7dc1b06`, a run has 8 steps 15 minutes apart, and the p50 and p95 of `POST /route` are recorded for a short, a medium, and a long trip in four setups.
  2. How: `scripts/backend_soak/soak_checks.py latency` ran inside `airflow_new-floodmap-backend-1` on 2026-10-02 from 02:39 to 02:49 +07, with 30 requests per cell in flexible mode with LM, for the motorbike and the car. The setups are GraphHopper alone, GraphHopper with the run's flood model, the backend with its area cache, and the backend without it. The edge count, image, and step facts come from read-only commands on the server. Tests came first (29 in `scripts/backend_soak/`).
  3. Why: the PRD leaves the latency factor open until a baseline exists, and two PRD assumptions were wrong (2,000,000 edges and 9 steps).
  4. Effect: GraphHopper alone answers in 8 to 21 ms at the p50, and the flood model raises that to 153 to 1,857 ms. The app's own path takes 126 to 2,759 ms, and a miss of the 30-second area cache adds 0.6 to 1.0 s. The user can now set the latency factor. `US-049` can pin commit `d7dc1b06`. The numbers were taken under pipeline load (load average about 10 on 12 CPUs), so a quiet host can be faster.

- **Story R2 (US-047): Build the synthetic scenarios, the offline reference, and the offline checker.**
  As an engineer, I want a slow reference implementation and a route checker, so the fast engine has
  something to be compared against.
  Given a synthetic flood on a real Hanoi corridor in `marie-curie/` with a throwaway PostGIS, when the
  four scenarios of [[routing-not-time-aware]] run through a time-dependent Dijkstra reference, then the
  results match the sticky column of the test table. Given any returned route, when the checker re-walks it
  with per-edge times, then it reports whether the route crosses an edge that is impassable at its arrival
  step.
  Priority: P0. Status: Done. Estimate: M. Sprint: 5. Dependencies: None.
  Evidence: ![[us-047-reference-check-output.png|700]]
  Details:
  1. What: a slow reference search under sticky closure, a route checker, and the four scenarios of the blocker's test table ([[sticky-routing-reference]]).
  2. How: `scripts/routing_reference/`. `StickyClosure` applies the PRD's rule: a road is closed when its depth reaches the vehicle limit at any step from the departure to the arrival plus 10 minutes. `earliest_arrival` is Dijkstra over arrival times, which is exact because closures only grow with arrival time. `find_crossings` re-walks a route with per-edge times. `corridor.py` builds a road network from `roads.geojson`, and `scenarios.py` holds the table. Tests came first (54 tests). The search matches an exhaustive search on 300 random graphs, and three deliberate changes to the rule each fail a test.
  3. Why: the engine (`US-050`) needs an answer to compare with that does not share its code, and the server proof (`US-055`) needs a checker for the routes GraphHopper returns.
  4. Effect: on real Hanoi roads (21.0250, 105.7550 to 21.0255, 105.7620, 15 edges, 1,488 m), all 16 runs (4 scenarios, `motorbike` and `car`, with and without a detour) match the sticky column and the returned routes have 0 crossings. The plain shortest route crosses a closed road in the 8 blocked runs, so the checker catches today's fault. Two departures from the story's wording. No throwaway PostGIS is used, because the scenarios assign depth per edge and need no spatial query. The code lives in `scripts/routing_reference/` and not in `marie-curie/`, which git does not track, so `US-050` and `US-055` can reuse it. The reference has not yet been compared with a GraphHopper response.

- **Story R3 (US-048): Show "no route" for a mode that has none.**
  As a driver, I want the app to say that my mode has no route, so I never see another mode's route under my
  mode's icon.
  Given the reproduction in [[failed-route-shows-previous-mode-route]], when the car request fails with
  `ConnectionNotFoundException`, then the map clears the previous route, the alert shows a message with text,
  and the backend passes GraphHopper's error body through in a shape `Api.ts` reads.
  This is todo 13 in [[frontend-todos-and-backend-dependencies]]. The user scheduled the same fix as
  [[frontend-polish]] Story 4 in [[sprint-plan]] Sprint 3 (2026-10-05 to 2026-10-11) on 2026-09-29, so this story is
  superseded by US-009 and left out of [[sprint-plan-2]].
  Priority: P1. Status: Superseded by [[frontend-polish]] Story 4. Estimate: S. Sprint: none. Dependencies: None.

- **Story R4 (US-049): Build the Java module skeleton, the image, and the CI job.**
  As an engineer, I want a module that builds against the pinned GraphHopper version and runs in our image, so
  the engine work has a place to live and a way to be tested.
  Given the pinned version and the revision from Story R1, when CI runs, then the module builds, the image
  starts with the stock profiles unchanged, and a unit test reports whether a weighting that only raises
  weights keeps LM's lower bounds valid. If the test fails, the story records that the search must run
  without LM.
  Priority: P0. Status: Done. Estimate: L. Sprint: 6. Dependencies: Story R1.
  Evidence: ![[us-049-image-smoke-test-output.png|700]]
  Details:
  1. What: a Java module in `java/time-aware-routing/` that builds against the pinned GraphHopper commit `d7dc1b06` (`12.0-SNAPSHOT`), an image that starts from the stock image's digest and runs the module, and a GitHub Actions job. `TimeAwareGraphHopper` returns the stock weighting for now.
  2. How: a shadow copy of `GraphHopperManaged` makes the web server build `TimeAwareGraphHopper`. The stock `graphhopper.sh` starts with `java -jar`, which ignores the classpath, so `run-time-aware.sh` starts `GraphHopperApplication` from a classpath with the module jar first. Tests first (9). CI builds the pinned commit, then runs `mvn test` (run 1, commit `ef5ef4c`, passed in 1 minute 34 seconds). `smoke-test.sh` builds the image on the server, starts it on port 8990 with its own graph cache, and compares routes.
  3. Why: the engine work needs a place to live and a way to be tested, and the web server has no setting to pick another GraphHopper class. The module also had to answer whether landmark (LM) lower bounds survive a weighting that only raises weights.
  4. Effect: LM stays valid for a raise-only weighting, so the search can use LM ([[routing-not-time-aware]]). `LandmarkLowerBoundTest` covers 10 random graphs, with a control that lowers weights and does break the bounds. On the server the image logged `TimeAwareGraphHopper active`, and 12 routes (4 profiles, 3 pairs inside the model border) matched the live service in distance, time, and point count. `US-039` and `US-050` can build on the module. The module was compiled for Java 17 and ran on the stock image's JRE.
  5. Limits: the pairs are few and the flood changes the routes from run to run, so the comparison shows the stock profiles unchanged for these pairs and not for all. The test container `graphhopper-time-aware` stays on the server until `smoke-test.sh cleanup` runs. The rendered evidence is built from output the user pasted.

- **Story R5 (US-050): Build the time-aware weighting and search for `motorbike` and `car`.**
  As a traveller, I want the route to account for the time I reach each road, so I am not sent into water that
  floods before I arrive.
  Given a synthetic depth table in the format of [[edge-depth-table-stories]] Story E2, when the four
  scenarios run for `motorbike` and `car`, with and without a detour, then the results match the reference
  from Story R2 and the checker finds no crossing of an impassable edge. The search carries the arrival time
  in its label, applies sticky closure from the departure step with a 10-minute margin, and reads the vehicle
  limit from the profile.
  Priority: P0. Status: Done. Estimate: L. Sprint: 8. Dependencies: Stories R2, R4, E2. Gate cleared: the user
  confirmed the sticky-from-departure wording on 2026-10-02.
  Evidence: ![[us-050-scenario-check-server-output.png]]
  Details:
  1. What: the time-aware weighting and search of the sticky C-lite engine in `java/time-aware-routing/`: `StickyClosure` (the closure rule), `TimeAwareDijkstra` (labels of weight and time), `StickyChecker`, `TimeAwareRouter` (hooks into GraphHopper's `route()`), and `ScenarioReport` with `scenario-check.sh`.
  2. How: tests first, 41 new module tests (98 in all). A road is closed for an arrival when a step in `[departure, arrival + 10 min]` has a depth at or above the limit, and steps before the departure are ignored. The search keeps several labels per node and drops one only when another is no heavier and no later, so it stays exact when weight and time differ. A request with the hint `td_departure` on a profile with `td_limit_cm` gets this search, and every other request goes the stock way. A snap in the middle of a road is mapped to the road's edge id (`VirtualEdgeIterator` is not a `VirtualEdgeIteratorState`, so the search detaches the edge). A random-graph test against an exhaustive search passes. Five changes each fail a test: no dominance rule, never closing, no virtual-edge mapping, a fixed limit, and an excluded window end.
  3. Why: a road that is dry at the request step and floods before the traveller arrives is a safety fault in today's single-step routing, and GraphHopper's weighting has no arrival time, so the search has to carry it.
  4. Effect: on the server, the image build ran all module tests and then `ScenarioReport` ran the 4 scenarios for motorbike and car, with and without a detour. All 16 runs match the sticky column of the blocker's test table with 0 crossings, and the plain shortest route crosses the closed road in all 8 blocked runs. `US-051` can add `truck` and `foot` as profiles with `td_limit_cm`. `US-052` connects `LatestTableSource` through `setTableSupplier`, adds the server flag, the request clock, and the fallback flag. `US-055` measures latency.
  5. Limits: the scenarios run on a hand-built corridor with exact minutes, not on real Hanoi roads (`US-055`). No server request is time-aware yet, because nothing sets the table supplier or the departure hint. The search skips landmarks and contraction hierarchies, so it visits more nodes than today's search, and the latency is not measured. Turn costs are handled in the code and are not tested. The evidence image is rendered from output the user pasted.

- **Story R6 (US-051): Add the `truck` and `foot` time-aware profiles.**
  As a truck driver or a pedestrian, I want the same timing check for my mode, so the four modes behave alike.
  Given Story R5's engine, when `truck` and `foot` requests run on the synthetic scenarios, then each uses its
  own depth limit (35 cm and 40 cm) and passes the checker.
  Priority: P1. Status: Reviewed. Estimate: S. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Story R5.
  Built on 2026-10-05, tests first. `td_limit_cm` 35 for `truck` and 40 for `foot` in `config.yml`. The engine needed no change, because it reads the limit from the profile. Tests: each of the four vehicles at depths 15, 25, 32, 37, and 45 cm through `route()` and through the search, a depth equal to the limit closes the road, `ScenarioReport` now runs 32 runs (4 scenarios, 4 vehicles, with and without a detour) and passes, and a test in each language keeps `config.yml` equal to the report's limits and to `flood_utils.py`. The blocker that stopped a `foot` profile (`graphhopper-vehicle-profile-rejection`) was `resolved` on 2026-09-23 and the profile is in `config.yml`. Not yet seen: the server run (`scenario-check.sh`, in the rollout of `US-055`).

- **Story R7 (US-052): Integrate the engine into the backend with a flag and a fallback.**
  As an operator, I want a switch and a safe fallback, so a problem with the table never takes routing down
  or hides that timing was skipped.
  Given a depth table for the running graph, when the flag is on, then `_handle_route` uses the `td` profile,
  takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run
  for the whole request, and returns `unknown` for a trip that ends after the last step. Given the flag off,
  then the response body equals today's. Given a missing, stale, or mismatched table, then the backend routes
  with today's model and the response carries a fallback flag.
  Tests cover the flag off, a departure between steps, the horizon edge, run pinning, and the hash mismatch.
  Priority: P0. Status: Reviewed. Estimate: M. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Stories R5, E5.
  Built on 2026-10-05, tests first: in Java `TableProvider`, the once-per-request decision, the response hints, the departure floored to its step, and the table folder loaded after the graph (`TimeAwareRouter`, `TimeAwareGraphHopper`; 118 module tests); in Python `time_aware_route.py` (27 tests) and `server.py`; `td_limit_cm` for `motorbike` and `car` in `config.yml`; the compose `graphhopper` service on the time-aware image with the table volume mounted read-only, and `TIME_AWARE_ROUTING` (default off) on the backend. The flag-on path through the real handler passes `test_server.py` against a PostGIS and a stub GraphHopper. Not yet seen: the deployed image on the server (`US-055`). Plan: [[time-aware-backend-integration]].

- **Story R8 (US-053): Build `POST /route/departures`.**
  As a traveller with no route now, I want to know the earliest time a route opens, so I can decide whether to
  wait.
  Given a real depth table and a route between two points, when the endpoint runs, then it requests the
  flood-free route with `edge_id` and `time` details, reads depth by edge id, applies sticky closure from each
  candidate departure with a 10-minute margin, and returns each candidate as `clear`, `blocked`, or
  `unknown`, the earliest clear departure, the run, and the run's age. Candidates start at the step that
  contains now. The client sends no clock value, margin, or policy.
  Priority: P1. Status: Not started. Estimate: M. Sprint: 9 ([[sprint-plan-3]]). Dependencies: Stories E2, E3, E4, R7.

- **Story R9 (US-054): Show "wait until" in the no-route alert.**
  As a traveller whose route is blocked, I want the alert to say when a route opens, so I have a next step
  besides staying put.
  Given a failed route request with no connection, when the client requests `POST /route/departures`, then
  the alert shows a loading line, then "The usual route is clear from HH:MM (forecast run HH:MM)", or "No safe
  route in the next 2 hours. Check again after the next forecast run." Given a clear route, then no advice
  appears. Given the fallback flag, then the alert shows "timing check unavailable". The alert keeps the
  existing advice to reach the safest location or stay put, and says "clear in the forecast", not "safe".
  Priority: P1. Status: Not started. Estimate: S. Sprint: 10 ([[sprint-plan-3]]). Dependencies: Story R8, and [[frontend-polish]] Story 4 in place of the superseded Story R3.

- **Story R10 (US-055): Prove the engine on the server and roll it out.**
  As the team, I want evidence on the server before the flag goes on, so the change ships with numbers and not
  hopes.
  Given the deployed image and a real run, when the four scenarios run for `motorbike` and `car`, then the
  results pass the checker. Given the baseline from Story R1 and the factor the user sets, when the p50 and
  p95 of `POST /route` are measured, then both are inside the factor. Given a fixed set of pairs, when the
  same pairs run against today's model and the reference, then the percentage of pairs whose route changes
  and the median detour ratio are recorded. The concept page [[graphhopper-backend]] and
  [[routing-not-time-aware]] are updated, and the blocker moves to `resolved` only with this evidence.
  Priority: P0. Status: Not started. Estimate: M. Sprint: 10. Dependencies: Stories R6, R7, R9, E7. Gate cleared:
  the user set the latency factor of 2 on 2026-10-02, so the p50 and p95 of each trip and vehicle stay within 2 times the baseline of Story R1.

## Status history

- **2026-09-29, draft.** Written from [[time-aware-routing-engine]]. No story has started.
- **2026-09-29, draft.** Re-cut with the plans: Stories R1 to R2, R4, and R5 stay in [[sprint-plan-2]] (Sprints 5 to 8). Stories R6 to R10
  moved to [[sprint-plan-3]] (Sprints 9 and 10). Story R3 is superseded by [[frontend-polish]] Story 4 in Sprint 3 of [[sprint-plan]].
- **2026-10-01, draft.** Story R2 (`US-047`) is `Done`: the reference and checker pass 54 tests, and all 16 scenario runs on real Hanoi roads match the sticky column with no crossing. Output rendered as `us-047-reference-check-output.png`. See [[sticky-routing-reference]].
- **2026-10-01, draft.** Story R1 (`US-046`) is `In progress`. The edge count (67,833), the source revision (commit `d7dc1b06`), and the step length and count (15 minutes, 8 steps) are recorded in [[routing-not-time-aware]]. The p50 and p95 wait for the `US-037` knob.
- **2026-10-02, draft.** Story R1 (`US-046`) is `Done`: the p50 and p95 of `POST /route` are recorded after the `US-037` knob settled, next to the edge count, the image revision, and the step length and count. Evidence: `us-046-baselines-check-output.png`.
- **2026-10-02, draft.** The gates of Stories R5 and R10 are cleared. The user confirmed the sticky-from-departure wording and set the latency factor to 2 (see [[time-aware-routing-engine]]).
- **2026-10-05, draft.** Story R4 (`US-049`) is `Reviewed`. The module, `Dockerfile`, entrypoint, and CI workflow are written, and the 9 tests pass on the Mac side (Maven, JDK 21 running the Java 17 target). LM stays valid for a raise-only weighting (see [[routing-not-time-aware]]). Not done: a green CI run, and the image built and started on the server. The acceptance check reads "when CI runs".
- **2026-10-05, draft.** Story R4 (`US-049`) is `Done`: CI run 1 passed and the image smoke test passed on the server (12 of 12 routes equal to the live service, `TimeAwareGraphHopper active` in the log). Evidence: `us-049-image-smoke-test-output.png`.
