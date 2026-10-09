---
date: 2026-10-09
type: plan
status: in-progress
tags: [plan, routing, arrival-only, bl-027, us-093]
related: ["[[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]", "[[US-093-measure-how-often-the-sticky-rule-gives]]", "[[sticky-routing-reference]]"]
last_updated: 2026-10-09
---

# Arrival-only reference over simple paths (BL-027, option A)

## Goal

Build option A of BL-027 as an experiment in `marie-curie/`. The search returns the earliest arrival over routes that visit no node twice. Loop-and-wait is not allowed. The user ruled that out on 2026-10-09.

## Design

- The new search lives in `marie-curie/arrival_only_simple_path.py`. It reuses `ArrivalOnlyClosure` and `ArrivalOnlyResult` from `scripts/routing_reference/arrival_only.py`, so the closure rule is the same one.
- A label is a node, an arrival time, and a parent chain. A label may not extend to a node already on its own chain.
- The queue orders labels by arrival time plus the static travel time to the destination, ignoring closures. That value never overestimates, so the first destination label popped is the earliest arrival over simple paths. The result is exact without a label cap.
- A budget on label expansions bounds the run time. If the budget runs out before the destination is popped, the result is inexact. If the queue empties, the result is exact and has no route.

## Tests

`marie-curie/test_arrival_only_simple_path.py` checks the search against a brute-force oracle that enumerates every simple path, on seeded random graphs. It also holds a hand-built graph where the loop-and-wait route arrives earlier than any simple route, and a budget test that returns `exact=False`.

## Next

Run the search on 10 pairs of the first table of the real graph. Report the exact rate and the time per pair. The result informs the decision in BL-027 on option A versus option B.

## Result of the real-graph run

On 2026-10-09 the search ran on the real graph (`US-099`, 15 pairs, 4 vehicles, 2 tables at steps 0 and 4, budget 3,000,000 expansions): 114 of 240 searches were exact (0.475), with a mean of 10 s and a maximum of 27.6 s per search. Exact searches took 0.08 s or less, and every inexact search used the whole budget. The tests passed (5 tests against the brute-force oracle). Details are in [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], approach 3. The four-node grid (654 scenarios, 94 scenarios where the loop-allowed search arrives earlier, 72 inexact) is evidence that the rules differ, and it does not show scale.

## Pruned search and promotion

On 2026-10-09 the search gained two exact bounds (the latest feasible time per node, and the time left over roads that are ever open), and it moved from `marie-curie/` to `scripts/routing_reference/arrival_only.py` as `SimplePathSearch`. `earliest_arrival_arrival_only` keeps its name and now returns the simple-path answer. The `max_labels_per_node` argument became `max_expansions` in `scripts/routing_experiments/sticky_cost.py`. The capped loop search moved to `marie-curie/arrival_only_loops.py` for the four-node grid. The real-graph exact rate went from 0.475 to 0.979 (235 of 240) in 76 s instead of 618 s ([[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], approach 4). The three suites pass (77, 83, and 28 tests).

## Status history

- **2026-10-09, in progress.** Plan written.
- **2026-10-09, in progress.** Real-graph run done (`US-099`): exact rate 0.475 at a budget of 3,000,000. The search now returns an expansion count (`search_counted`) and the runner is `marie-curie/run_option_a_real.py`. Next is the decision in `US-100`.
- **2026-10-09, in progress.** The user chose option A as the definition. The search was pruned and moved to `scripts/routing_reference/arrival_only.py`. Exact rate 0.979 on the real graph. Next is the user's exact-enough bar and the `US-093` run.
