---
date_drafted: 2026-10-08
type: user-story
us_id: "US-091"
story_label: "2"
epic: "[[EP-20-routing-paper-experiments]]"
status: Reviewed
kind: spike
priority: P1
estimate: M
sprint: 
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[US-102-replay-the-storm-with-the-us-101-fix-to]]", "[[BL-026-sticky-closure-clock-anchored-at-floored-departure]]"]
title: "Measure how often a single-timestep route meets a closed road on arrival"
---

# US-091 Measure how often a single-timestep route meets a closed road on arrival

As the author of Paper A, I want the violation rate of today's single-timestep routes, so the case for time-aware routing is a number and not an argument.
Given pairs sampled inside the model border, in three length classes (under 2 km, 2 to 5 km, over 5 km), for each of the four vehicles and each departure step, when the backend plans each route with the single-timestep model (the flag off) and the checker re-walks it with the arrival time of each edge, then a result file records the violation rate by vehicle, trip length class, departure step, and storm stage (cold start, one hour, three hours).
The file reports three arrival-step rules side by side: the step at or before the arrival, the nearest step, and the worse of the two around it.
It also records the severity (depth over the limit at the worst edge, and the number of violating edges) and the time to the first violation along the route.
The story builds the harness that `US-092` reuses: the pair sampler, the call that plans a route, the re-walk, and the result writer.
It sits on `scripts/routing_reference/` and the crossings check of `scripts/routing_proof/`.
The sticky engine is run on the same pairs as a test.
Its violation count must be 0, so the experiment also checks the engine.
Arrival times assume free flow, so the story adds one sensitivity case that slows travel on deep edges, labelled as a sensitivity case.
Needs no new engine.
Dependencies: `US-047` (the reference and the checker, `Done`), `US-050` and `US-052` (the engine behind the flag, `Done`), and the depth tables of the 12-hour replay of `US-089` (copied before retention removes them, see rule 5).
The server run reads the engine proof of `US-055`, which is `In progress`.
The sticky-engine check inside this story needs the same server state that `US-055` proved on 2026-10-07.
Evidence: see the Evidence and details section.

## Status history

- **2026-10-10, carried from the retired TODOS note.** The harness is in `scripts/routing_experiments/` (41 tests pass).
  Three things to know.
  First, the runner walks engine routes from the time of the request since `US-096`.
  Second, the sticky engine cannot be checked on the old replay tables, because the backend departs at the later of the step time and now, so the sticky check needs live tables.
  Third, the single-timestep plan reads the database flood areas and the re-walk reads the edge depth table of the same run, which are two depth sources, and the result file must say so.
- **2026-10-10, preliminary run on the 12-hour data (not the result).** The harness plans through the backend, and the backend keeps flood areas for the newest 8 runs only (`FLOOD_EXTENT_KEEP_RUNS=8`), so only the last 8 runs of the second replay (23:15 to 01:00 +07) can be planned.
  `experiment.py run --model single_timestep` on those 8 tables, 30 pairs (10 per length class, seed 1), 4 vehicles, departure steps 0 and 1, against the backend with the flag off (`model_check`: 0 routes of another model) took 11 min 42 s and planned 1,486 routes (434 of 1,920 had no route).
  Result file: `marie-curie/us-091/single_timestep_late_seed1.json`.
  Violation rate under the rule "step at or before the arrival": 119 of 1,486 routes (8.0 percent), 120 under the nearest step, and 139 under the worse of the two.
  By vehicle it is 18.2 percent (car), 6.3 (truck), 3.8 (foot), and 3.2 (motorbike).
  By length class it is 13.5 percent under 2 km, 2.8 from 2 to 5 km, and 7.9 over 5 km.
  By departure step it is 7.4 (step 0) and 8.6 (step 1).
  The sticky rule would close an edge on 120 of the 1,486 routes.
  Limits: one stage only (late storm, no cold-start, one-hour, or three-hour stages), 30 pairs, and free-flow arrival times.
  The depth sources differ (backend flood areas to plan, edge depth tables to re-walk).
  The sticky engine check on the same pairs is not done.
  The remaining stages need a replay with `FLOOD_EXTENT_KEEP_RUNS` raised (about 60).
- **2026-10-10, reviewed.** The spike is built and measured, and its status moves from In progress to Reviewed, not Done.
  The owner accepts the measurement at the review.
- **2026-10-10, reviewed.** The single-timestep model ran on departure steps 0 and 1 only.
  The backend keeps flood areas for the first two steps of each run (`/flood/timesteps` lists 2), so later steps fail the model's own precondition.
  The earlier plan said steps 0 to 6, and that was wrong.
  The harness precondition in `scripts/routing_experiments/experiment.py` now applies only to the single_timestep model (commit "Let the sticky run use steps that the backend has no flood area for").
- **2026-10-10, reviewed.** The dependency of this story is [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]], the replay, and not US-089.
  The plan already names US-102.
  The Dependencies line in the body still names US-089, and the owner decides at the review whether to correct it.
- **2026-10-10, reviewed.** The preliminary late-stage figure of 8.0 percent in the note above agrees with the final late stage of 7.9 percent.
- **2026-10-10, severity added.** The severity figures and the time to the first violation were added from the result file.
  The figures are in Detail 7 of "Evidence and details".

## Evidence and details

The images are rendered output, not live screenshots.

![[us-091-single-timestep-result-output.png|900]]

Rendered output of `marie-curie/us-091/single_timestep_seed1.json`, captured 2026-10-10 18:55 +07 on gods-macbook.local (the Mac), from a harness run on the server worker from 18:22 to 18:49 +07.

![[us-091-live-sticky-mid-step-output.png|900]]

Rendered output of the three live sticky result files for the cold, 1h, and 3h stages, captured 2026-10-10 18:41 +07 on gods-macbook.local (the Mac), against the server 100.67.84.55.

1. What was built: the harness in `scripts/routing_experiments/`, which samples the pairs, plans each route, re-walks it, and writes the result, run on 60 pairs (20 per length class, seed 1) and four vehicles.
2. How: the single-timestep model (flag off) ran on the server worker with departure steps 0 and 1 over the three storm tables and the last eight runs (20261010T163000 to 20261010T181500), labelled late.
   The sticky engine (flag on for floodmap-backend only) ran on the cold (20261010T051500), 1h (20261010T061500), and 3h (20261010T081500) tables with departure steps 0 to 5.
   Free flow was the only arrival-time case.
   The model check found 0 routes from another model in every run.
3. Why: the story needs a number for time-aware routing, not an argument.
   The single-timestep run planned 3,911 routes out of 5,280 requests, and 1,369 had no route (26 percent).
   Violating routes were 307 (7.8 percent) under "step at or before the arrival", 310 (7.9 percent) under "nearest", and 346 (8.8 percent) under "worse of the two".
4. Results by group, with the step-at-or-before rule: cold 7.1 percent (30 of 423), 1h 3.7 percent (15 of 402), 3h 13.0 percent (49 of 376), and late 7.9 percent (213 of 2,710).
   By vehicle, car is 10.8 percent, motorbike 10.4, foot 5.9, and truck 4.9.
   By trip length, under 2 km is 5.4 percent, 2 to 5 km is 7.8, and over 5 km is 10.3.
   By departure step, step 0 is 7.9 percent and step 1 is 7.8 percent.
5. Sticky engine: the three live readings had 0 crossings, and their planned routes were 1,292 (cold), 1,253 (1h), and 1,215 (3h).
   The 636 routes that departed between two forecast steps had 0 crossings, the check that [[BL-026-sticky-closure-clock-anchored-at-floored-departure|BL-026]] asked for.
   The sticky rule would close an edge on 316 of the single-timestep routes, so the harness prints `passed=false` for that model, which is expected and is not an engine failure.
6. What it changes: the result is the number that Paper A needs for the case for time-aware routing.
   Two depth sources differ: the single-timestep plan reads the backend flood areas, and the re-walk reads the edge depth tables, as the sticky engine does.

7. What was added: the severity and the time to the first violation for the 307 violating routes under the rule "step at or before the arrival".
   The figures come from `marie-curie/us-091/single_timestep_seed1.json`, and the script output is `marie-curie/us-091/single_timestep_severity.txt`.
   The depth over the vehicle limit at the worst edge has a median of 16 cm, a 75th percentile of 24 cm, and a maximum of 140 cm.
   A violating route has a median of one violating edge, a mean of 1.0, and a maximum of four.
   The time from departure to the first violation has a median of 513 s, a 25th percentile of 218 s, and a 75th percentile of 644 s.

Not yet in this story: only the sensitivity case that slows travel on deep edges (every result is free flow).

Decision: pending, the owner decides at the review.
