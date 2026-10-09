---
date_drafted: 2026-10-08
type: user-story
us_id: "US-093"
story_label: "4"
epic: "[[EP-14-routing-paper-experiments]]"
status: Not started
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
Priority: P2. Status: Not started. Estimate: S. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
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
