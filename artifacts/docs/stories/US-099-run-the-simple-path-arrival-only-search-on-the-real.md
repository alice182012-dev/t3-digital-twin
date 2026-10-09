---
date_drafted: 2026-10-09
type: user-story
us_id: "US-099"
story_label: "5"
epic: "[[EP-20-routing-paper-experiments]]"
status: Done
kind: spike
priority: P2
estimate: S
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]", "[[US-093-measure-how-often-the-sticky-rule-gives]]", "[[arrival-only-simple-path-reference-bl-027]]"]
title: "Run the simple-path arrival-only search on the real graph and record its exact rate and runtime"
---

# US-099 Run the simple-path arrival-only search on the real graph and record its exact rate and runtime

As the author of Paper A, I want option A of [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]] run on the real Hanoi graph, so the paper and the decision in `US-100` rest on a measured exact rate and runtime and not on the four-node grid.
Given `marie-curie/arrival_only_simple_path.py` and the 3 depth tables in `marie-curie/edge_tables_replay_2026-10-09/`, when the search runs on the pair set of `US-093` with a stated label budget, then a result file records, for each vehicle limit, the share of exact comparisons, the time per pair (mean and maximum), the number of label expansions, and the pairs that ran out of budget.
The grid in `marie-curie/flood_scenario_grid.py` has four nodes, so it shows that option A and sticky closure differ, and it cannot show that option A scales.
It produced 654 cases, with counts of 94 and 72 that `US-100` cites.
If the real graph is much slower than the grid, that is a separate problem and goes to a new blocker page, not into this story.
The result file states that one-way roads are open both ways and that travel time is length at 30 km/h (`real_graph.py`).
`BL-027` and [[arrival-only-simple-path-reference-bl-027]] change only after this run: the blocker gets a third approach with the measured rate and runtime, and the plan gets a status entry.
Both cite the grid's 654 cases and the 94 and 72 counts as evidence, labeled as grid evidence.
Dependencies: the option A search and its brute-force test in `marie-curie/` (written, not yet run on the real graph), `scripts/routing_experiments/real_graph.py`, and the 3 copied replay tables.
The storm stages of `US-093` wait for the second replay (D-020), but this run needs only the tables that exist.
Evidence: the verbatim summary rendered to an image, captured 2026-10-09 19:27 +07 on the Mac (`gods-macbook.local`).

![[us-099-option-a-real-graph-output.png]]
Blocker tracking: [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]].

## Evidence and details

1. Built `marie-curie/run_option_a_real.py`, which runs option A for each table, step, vehicle, and pair, records exactness, seconds, and expansions, and classifies each exact pair against the sticky search.
   The search gained `search_counted`, which returns the expansion count.
2. Ran it on 15 pairs, 4 vehicles, 2 tables at steps 0 and 4, with a budget of 3,000,000 expansions: 240 searches in 618 s on 4 workers.
   A first run with 30 pairs and 10,000,000 was stopped after 2 hours 26 minutes, because it wrote nothing until the end.
   The runner now appends each record to a `.jsonl` file as it finishes.
3. Result: 114 of 240 searches were exact (0.475; motorbike 0.50, the other three 0.47).
   Exact searches took 0.08 s or less.
   Inexact searches used the full budget (mean 19 s), and the longest search took 27.6 s.
   All pairs under 2 km were exact, while 19 of 80 between 2 and 5 km and 15 of 80 over 5 km were.
   The result file states that one-way roads are open both ways and that travel time is length at 30 km/h.
4. Effect: option A is not an exact reference for every pair at this budget, and the exact set leaves out the blocked pairs `US-093` needs.
   `BL-027` stays open with approach 3 recorded, and `US-100` decides between option A, option B, and sticky closure.
   The grid evidence (654 scenarios, 94 earlier-arrival cases, 72 inexact cases) is cited in `BL-027` as evidence that the rules differ, not that option A scales.

## Status history

- **2026-10-09, not started.** Written from the user's list of next steps for `BL-027`.
  The user's order: run option A on the real graph first, update the blocker and the plan second, decide between option A and sticky separately (`US-100`).
- **2026-10-09, done.** Run finished and recorded in `BL-027` (approach 3) and the plan.
  Exact rate 0.475 at a budget of 3,000,000 expansions.
