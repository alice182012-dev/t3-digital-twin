---
date_drafted: 2026-10-08
type: user-story
us_id: "US-093"
story_label: "4"
epic: "[[EP-20-routing-paper-experiments]]"
status: Done
kind: spike
priority: P2
estimate: S
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Measure how often the sticky rule gives no route or a longer route than an arrival-only reference"
---

# US-093 Measure how often the sticky rule gives no route or a longer route than an arrival-only reference

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
This is the backlog row "Measure how many routes arrival-only closure would change" of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], converted
into a story. The row said it needed the engine shipped first. The engine is deployed behind the flag (`US-052`,
`Done`), and the sticky side can come from the reference with a real table, so only the arrival-only search and the
depth tables are missing.
Priority: P2. Status: In progress. Estimate: S. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: `US-047` (the reference), `US-050` (the engine, for a cross-check of the sticky side on a sample of
pairs), the depth tables of the 12-hour replay (rule 5), and the pair sampler of `US-091` if it is ready. The sampler
can be copied if not.
Evidence: None yet.
Blocker tracking: [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

## Status history

- **2026-10-09, active.** The real-graph runner ran the sticky versus arrival-only comparison on the 3 copied tables: all 2,520 comparisons (30 pairs, 21 settings, 4 vehicles) came back `INEXACT`. The arrival-only search in `scripts/routing_reference/arrival_only.py` keeps distinct arrival times per node, and on a graph where every road is open both ways the cycles fill the cap of 16 labels per node before the destination is reached. Caps of 64 and 256 stay inexact and take 7 s and 35 s per pair. No share of "no route" or "longer route" is reported. Fixing it needs a decision on the reference (for example, allow only simple paths, or add a dominance rule), which changes what "arrival-only" means in the paper. The story stays `In progress`.
- **2026-10-09, active.** First storm-wide run on the 30 depth tables of the second replay that existed at 21:15 +07 (`20261009T130000` to `20261009T211500`; four tables from `T194500` to `T203000` are missing and the cause is not checked). Setting: 30 node pairs (10 per length class), 4 vehicles, departure steps 0 and 4, budget 3,000,000 expansions, seed 1, 7,200 searches in 18.3 minutes. 7,149 were exact (0.993; 0.987 for the lowest vehicle, the motorbike). All 51 inexact searches have a sticky route and a proven upper bound on the extra time (median 6.7 s, 90th percentile 38.6 s, maximum 245 s). No search broke the nesting check.
  - Of the 7,149 exact searches, 6,503 were `same`, 291 `sticky_longer` (4.1%), 9 `sticky_no_route` (0.1%), and 346 `neither` (4.8%, no route for either rule). Among the 6,803 searches where arrival-only has a route, sticky is longer in 4.3% and has no route in 0.13%. Counting every inexact search as `sticky_longer` gives a range of 4.0% to 4.7% over all 7,200.
  - By length class, sticky is longer in 0.0% under 2 km, 3.8% for 2 to 5 km, and 8.5% over 5 km. By vehicle it is longer in 3.5% (car), 3.4% (foot), 5.1% (motorbike), and 4.2% (truck). By storm hour it is longer in 6.4% and 6.9% in the first two hours and 2.2% to 3.5% from hour 4.
  - Limits of this run: it covers the storm up to 21:15 +07 and not the end, 16 of the 30 pairs account for all the `sticky_longer` cases, so the samples are not independent, and the runner did not record the extra time of the exact `sticky_longer` cases (fixed for the next run). The story stays `Active`. The final run needs the tables after 00:45 +07, copied before `replay.ps1 stop`. Result files: `marie-curie/us-099/us093_storm_seed1.json` and `summarize_storm.py`.
- **2026-10-10, active.** The depth tables of the second replay are copied from the worker to `marie-curie/edge_tables_replay2_final_2026-10-10/` (48 files, 45 of the second replay `20261009T130000` to `20261010T010000` and 3 of the first, SHA-256 equal to the worker's). The four missing tables (`20261009T194500` to `20261009T203000`) are not a fault: the gate skipped those four runs (19:30 to 20:15 +07). The final full-table run uses these files.
- **2026-10-10, correction.** The entry above calls the four missing tables "not a fault". The user corrected this: they are the P0 blocker [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]], because the flood stands after the rain stops. The final run waits for `US-101`.
- **2026-10-10, active.** The final run on the current tables started at 01:49 +07 on the Mac only, at the user's choice (next action 1, option a): `marie-curie/edge_tables_replay2_final_2026-10-10/`, the 45 tables of the second replay (`20261009T130000` to `20261010T010000`, with the 4 missing tables named in [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] and a cold start at 20:30 +07), 30 pairs, departure steps 0 and 4, seed 1, budget 3,000,000, 5 workers. Result file: `marie-curie/option_a_real_replay2_final_seed1.json`. The result must name the gap and the cold start.
- **2026-10-10, active.** The exact-enough bar for the arrival-only reference is 97 percent of searches exact per vehicle ([[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]]). The storm-wide run on 30 tables meets it (lowest: motorbike 0.987). The final run on 45 tables must confirm it, and the result reports the inexact rest with its proven bound.
- **2026-10-10, carried from the retired TODOS note.** The arrival-only search and the comparison with sticky closure have 24 tests in `scripts/routing_experiments/test_sticky_cost.py`. A seeded property test on 300 graphs shows that sticky closure never ends earlier than arrival-only.
- **2026-10-10, final run on the 12-hour data (result).** `marie-curie/option_a_real_replay2_final_seed1.json`: the 45 tables of the second replay (the one-hour gap at 19:30 to 20:15 +07 and the cold start at 20:30 +07 are in the sample), 30 pairs (10 per length class, seed 1), departure steps 0 and 4, 4 vehicles, budget 3,000,000, 5 workers, 32.7 minutes, 10,800 searches. **Exact: 10,730 (0.9935), above the 97 percent bar for every vehicle** (motorbike 0.988, car 0.991, truck 0.997, foot 0.998). Outcomes: same route 9,830, sticky longer 405, sticky has no route where arrival-only has one 12, neither rule has a route 483, inexact 70 (62 of them with a proven upper bound on the extra time). Where arrival-only has a route (10,247 searches), sticky gives the same route in 95.9 percent, a longer route in 3.95 percent, and no route in 0.12 percent. Sticky longer, by vehicle: 5.1 percent (motorbike), 4.1 (truck), 3.5 (car), 3.2 (foot). By length class: 0 percent under 2 km, 4.0 from 2 to 5 km, 8.0 over 5 km. By chain: 4.5 percent in chain 1 and 3.1 in chain 2. The extra time of the 405 longer routes has a median of 9 s, a mean of 30 s, a 90th percentile of 102 s, and a maximum of 229 s. Limits: 30 pairs, free-flow travel time at 30 km/h, one-way roads open both ways, 3Di depths on a graph of the model and not measured depths, one storm. The result is read by the paper, which cites it as the price of sticky closure ([[decision-log|D-023]]).
- **2026-10-10, done.** The user approved closing the story on the final run of the second replay. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]] is `resolved`.

## Evidence and details

**Evidence:** rendered output of `evidence/us-093-final-check.py`, which reads `marie-curie/option_a_real_replay2_final_seed1.json`.

![[us-093-final-check-output.png|900]]

**Details:**

1. Built: the share of routes where the sticky rule gives no route or a longer route than an arrival-only reference, measured on the real graph of Hanoi. The code is `scripts/routing_experiments/sticky_cost.py` and `scripts/routing_reference/arrival_only.py`, run by `marie-curie/run_option_a_real.py`.
2. How: 30 node pairs (10 per length class, seed 1) on the 45 tables of the second replay, 2 departure steps, 4 vehicles, 10,800 searches at a budget of 3,000,000 expansions each, in 32.7 minutes on the Mac with 5 workers. The reference is option A: the earliest arrival over routes that visit no node twice, with a fixed departure.
3. Why: the paper has to state what the cautious rule costs. Where arrival-only has a route, sticky gives the same route in 95.9 percent of searches, a longer route in 3.95 percent (median 9 s, mean 30 s, at most 229 s), and no route in 0.12 percent. The extra cost is 0 under 2 km, 4.0 percent from 2 to 5 km, and 8.0 percent over 5 km. The reference is exact for 99.35 percent of searches, above the 97 percent bar for every vehicle.
4. What it changes: the paper cites these shares as the price of sticky closure ([[decision-log|D-023]]). They hold for one storm, 30 pairs, free-flow travel time at 30 km/h, one-way roads open both ways, and 3Di depths on the model grid. The 70 inexact searches carry a proven upper bound (62 of them). The result names the one-hour gap (19:30 to 20:15 +07) and the cold start at 20:30 +07, which [[BL-028-rain-gate-stops-simulation-while-the-flood-still-stands|BL-028]] explains.
