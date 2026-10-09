---
date_drafted: 2026-10-08
type: user-story
us_ids: ["US-090", "US-091", "US-092", "US-093"]
status: draft
subsystem: routing, paper
source_ideas: []
related: ["[[sprint-plan-3]]", "[[paper-handoff-routing-and-system]]", "marie-curie/idea-routing-paper-reviewer-questions.md", "marie-curie/vehicle-limit-sources.md", "[[sprint-plan-4]]", "[[sticky-routing-reference]]", "[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[rain-replay-test-environment-stories]]", "[[routing-first-consumer-stories]]", "[[schedule-routing-paper-experiments-and-move-frontend]]"]
tags: [user-story, epic, routing, paper, experiments, sprint-12]
---

# Epic: routing paper experiments

Four experiments that Paper A (routing) needs before its Results section can be written. They answer the three
questions a reviewer would ask in `marie-curie/idea-routing-paper-reviewer-questions.md` (Questions 1, 2, and 3). The
handoff [[paper-handoff-routing-and-system]] lists them as work items P1 to P4. Those names are working names only. Each
story has its own `US-nnn`.

All four are in Sprint 12 of [[sprint-plan-3]]. The user decided on 2026-10-08: "We need to finish the routing first."
Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]], needed because the base shape has no per-row scheduling field (`.claude/CLAUDE.md`, rule 2). A
story reaches `Done` only with evidence and numbered details, recorded here and in `sprint-plan-3.md`. These are
backend and analysis stories with no UI, so the evidence is the verbatim command output rendered to an image, with a
caption that gives the capture time and host.

## Rules that apply to every story here

1. Name the storm behind every result. The real 2026-09-16 IMERG replay (`scripts/rain_events/hanoi_20260916_storm.csv`,
   12 hours, 53.88 mm, peak 8.73 mm/h) is real rain. The constant 50 mm/h storm of 2026-10-02 is synthetic. A result
   that mixes both says so, and a table row names its storm.
2. The depths are 3Di model output, not observations. A violation rate is a rate in the model driven by that rain. No
   result is described as a measured rate of drivers meeting closed roads.
3. Every coordinate stays inside the model border (`.claude/CLAUDE.md`, "Test points stay inside the model border").
   The pair set drops a pair that gives `Cannot find point` and counts the drops.
4. The vehicle limits (motorbike 20 cm, car 30, truck 35, foot 40) are policy parameters. No result calls a limit
   "safe". `VEHICLE_PROFILES` in `flood_utils.py` is the one owner of the deployed values (`US-074`). An experiment
   passes a limit as a parameter and never edits that file.
5. Where the depth comes from is stated in each result. The edge depth table keeps only the newest 3 runs
   (`EDGE_TABLE_KEEP_RUNS=3`), so the copy of the tables of a replay must be made before the replay's retention
   removes them. `flood_road_values` has no retention but is keyed by road segment and not by graph edge.

- **Story 1 (US-090): Write the FIFO lemma and the correctness proof of the sticky-closure forward search.**
  As the author of Paper A, I want a written lemma and proof that the sticky-closure search is exact, so a reviewer who
  cites the hardness result of Kleff et al. finds the answer on a page and not in a sketch.
  Given the sketch in Question 3 of the reviewer-questions note, the closure rule in `StickyClosure` (Java) and
  `scripts/routing_reference/sticky_reference.py`, when the proof is written, then the page
  `artifacts/docs/concepts/sticky-closure-proof.md` holds these parts, each checkable by reading it:
  1. The closing time of an edge, defined with the 10-minute margin the implementation uses. The note's sketch has
     no margin, so the page shows that the edge is open for arrivals before `c(e) - margin` and closed from then on.
  2. The lemma that the arrival function of each edge is non-decreasing, which is the FIFO property.
  3. The theorem that a forward time-dependent Dijkstra over arrival times is exact, with the cost in the same order
     as a static search. It cites Kaufman and Smith 1993 and Dean 2004 only from the sources the review opened.
  4. The step-boundary cases: arrival exactly on a step, the window end exactly on a step (included), a departure
     between two steps, a depth equal to the limit (closes), and a road that drained before the departure (ignored).
     Each case names a test that covers it. `test_the_end_of_the_window_is_included`,
     `test_a_depth_equal_to_the_limit_closes_the_road`, and `test_water_that_drained_before_departure_does_not_close_the_road`
     in `scripts/routing_reference/test_sticky_reference.py` cover three of them. A case with no test gets a new one,
     written first.
  5. A statement on the landmark heuristic. `LandmarkLowerBoundTest` (`US-049`) shows that landmark bounds stay valid
     for a raise-only weighting. The search of `US-050` does not use landmarks, so the page says what holds and does
     not claim that the engine uses them.
  6. A plain list of what the proof does not say: it does not solve Kleff's problem with reopening windows, and it is
     exact for the sticky rule and not for the true arrival-time rule.
  The suite of `scripts/routing_reference/` passes after the new tests.
  Priority: P1. Status: Done. Estimate: M. Sprint: 12 ([[sprint-plan-3]]; 2026-12-07 to 2026-12-13).
  Dependencies: None. The user's confirmation of "sticky from departure" is already in place (2026-10-02).
  Evidence: None yet.

- **Story 2 (US-091): Measure how often a single-timestep route meets a closed road on arrival.**
  As the author of Paper A, I want the violation rate of today's single-timestep routes, so the case for time-aware
  routing is a number and not an argument.
  Given pairs sampled inside the model border, in three length classes (under 2 km, 2 to 5 km, over 5 km), for each of
  the four vehicles and each departure step, when the backend plans each route with the single-timestep model (the
  flag off) and the checker re-walks it with the arrival time of each edge, then a result file records the violation
  rate by vehicle, trip length class, departure step, and storm stage (cold start, one hour, three hours). The file
  reports three arrival-step rules side by side: the step at or before the arrival, the nearest step, and the worse of
  the two around it. It also records the severity (depth over the limit at the worst edge, and the number of violating
  edges) and the time to the first violation along the route.
  The story builds the harness that `US-092` reuses: the pair sampler, the call that plans a route, the re-walk, and
  the result writer. It sits on `scripts/routing_reference/` and the crossings check of `scripts/routing_proof/`.
  The sticky engine is run on the same pairs as a test. Its violation count must be 0, so the experiment also checks
  the engine. Arrival times assume free flow, so the story adds one sensitivity case that slows travel on deep
  edges, labelled as a sensitivity case.
  Needs no new engine.
  Priority: P1. Status: In progress. Estimate: M. Sprint: 12 ([[sprint-plan-3]]; 2026-12-07 to 2026-12-13).
  Dependencies: `US-047` (the reference and the checker, `Done`), `US-050` and `US-052` (the engine behind the flag,
  `Done`), and the depth tables of the 12-hour replay of `US-089` (copied before retention removes them, see rule 5).
  The server run reads the engine proof of `US-055`, which is `In progress`. The sticky-engine check inside this story
  needs the same server state that `US-055` proved on 2026-10-07.
  Evidence: None yet.

- **Story 3 (US-092): Test how the vehicle limits change the result.**
  As the author of Paper A, I want a sensitivity analysis of the motorbike and truck limits, so the paper answers "why
  20 and 35 cm" with a measured range and not with a source that does not exist.
  Given the harness and the pair set of `US-091`, when the motorbike limit runs over 10, 15, 20, 25, 30, and 40 cm, the
  truck limit over 25, 30, 35, 40, 50, and 60 cm, and the precaution fraction of D-021 at 0.25, 0.5, and 0.75 of the
  limit, then a result file records for each setting the closed road length, the share of origin and destination pairs
  that still have a route, the mean detour, and the violation rate of `US-091`. It also holds a regret table: plan
  with limit A, judge against limit B. A short list names the settings where the conclusion changes. The file states
  whether Hanoi shows the "no noticeable change" that Kasmalkar reported over 1 to 12 inches.
  The provenance of the four limits is already searched (`marie-curie/vehicle-limit-sources.md`, 2026-10-08). This story
  does not repeat the search. It copies the verdicts into the result file: car 30 cm supported for a small passenger
  car, motorbike 20 cm partly supported, truck 35 cm no source, foot 40 cm partly supported and conservative.
  Copy the note out of `marie-curie/` first, because that folder is disposable.
  Priority: P2. Status: Not started. Estimate: M. Sprint: 12 ([[sprint-plan-3]]; 2026-12-07 to 2026-12-13).
  Dependencies: `US-091` (its harness and its pair set), so the two stories sit in one sprint and the second starts
  when the first has a working harness. If the harness slips, this story moves to Sprint 13 of [[sprint-plan-4]]
  (the rule is in the Risks table of [[sprint-plan-3]]).
  Evidence: None yet.

- **Story 4 (US-093): Measure how often the sticky rule gives no route or a longer route than an arrival-only reference.**
  As the author of Paper A, I want the cost of sticky closure measured, so the paper states how conservative the rule
  is with a number.
  Given random origin and destination pairs inside the model border and the real depth tables of the replay, when the
  sticky route and an arrival-only route are computed for each pair, vehicle, and departure step, then a result file
  records the share of cases with no sticky route where an arrival-only route exists, the share with a longer sticky
  route, and the distribution of the extra time, by vehicle and storm stage.
  The arrival-only rule closes a road only if its depth at the arrival step reaches the limit. `sticky_reference.py`
  does not have this rule today. The story adds it as a second search that keeps several labels per node, because
  the arrival-only function is not FIFO. If that search needs more than a label-correcting variant of
  `earliest_arrival`, the estimate grows from S to M, and the first hour of work decides it. The decision goes in
  Status history.
  This is the backlog row "Measure how many routes arrival-only closure would change" of [[sprint-plan-3]], converted
  into a story. The row said it needed the engine shipped first. The engine is deployed behind the flag (`US-052`,
  `Done`), and the sticky side can come from the reference with a real table, so only the arrival-only search and the
  depth tables are missing.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 12 ([[sprint-plan-3]]; 2026-12-07 to 2026-12-13).
  Dependencies: `US-047` (the reference), `US-050` (the engine, for a cross-check of the sticky side on a sample of
  pairs), the depth tables of the 12-hour replay (rule 5), and the pair sampler of `US-091` if it is ready. The sampler
  can be copied if not.
  Evidence: None yet.

## Status history

- **2026-10-08, draft.** Written at the user's request: "From P1-P4 lets move them to sprint 12, and the front end can be
  sprint 13. We need to finish the routing first." The four stories come from the work items P1 to P4 of
  [[paper-handoff-routing-and-system]]. P5 (open the Vu 2024 report) is replaced by the source search of 2026-10-08, so
  it has no story. IDs `US-090` to `US-093`, in the order P1, P2, P3, P4.
- **2026-10-09, active.** Story 1 (`US-090`) is `Done`: [[sticky-closure-proof]], two new tests, evidence `us-090-proof-check-output.png`. The proof found the clock error of the engine, now `US-096` ([[sticky-closure-clock-anchored-at-floored-departure]]).
- **2026-10-09, active.** Story 2 (`US-091`): the harness is built (`scripts/routing_experiments/`, 42 tests). After `US-096` the runner walks engine routes from the time of the request and starts the sticky window at `td.departure` (`88c151c`). The server run and the storm stages wait for the second replay (D-020).
- **2026-10-09, active.** Stories 3 and 4 (`US-092`, `US-093`) are `In progress`. The offline code is merged on `modular` (`fc14d81` to `bb00594`): `arrival_only.py`, `sticky_cost.py`, `limit_sweep.py`. The first hour of `US-093` did not need more than a label-correcting search, so the estimate stays S. Open: the cost-band sweep of `US-092` (the reference has no cost factors) and a graph with node ids for a real run.
- **2026-10-09, active.** [[edge-export-has-no-node-ids]] is `resolved`. `scripts/routing_experiments/real_graph.py` builds the reference `Graph` from the format-2 export of the server (67,833 edges, `b34cd0e`), and a smoke sweep of `sweep_fraction` ran on it with a replay table. Stories 3 and 4 now wait only for the second replay (D-020). Any real result must state that one-way roads are open both ways and that travel time is length at one speed.
- **2026-10-09, active.** D-021 replaces the cost band of Story 3 with the precaution fraction. The sweep records, for each fraction, the share of pairs with a recommended route, the share that fall back to the hard-limit route, and the extra time of the recommended route. The engine change is `US-097` ([[US-097-098-precaution-depth-routing-stories]]).
