---
date_open: 2026-10-09
date_closed: 
type: blocker
status: open
severity: P2
subsystem: time-aware-routing
approaches_tried: 4
approaches_remaining: 1
tags: [blocker, routing, arrival-only, us-093, paper-experiments]
related: ["[[US-100-decide-between-option-a-and-sticky-closure]]", "[[US-093-measure-how-often-the-sticky-rule-gives]]", "[[US-092-test-how-the-vehicle-limits-change-the]]", "[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout]]", "[[BL-024-edge-export-has-no-node-ids]]", "[[sticky-closure-proof]]", "[[sticky-routing-reference]]"]
last_updated: 2026-10-09
---

# arrival-only-reference-is-inexact-on-the-real-graph

## Description

`scripts/routing_experiments/real_run.py` runs the arrival-only reference (`earliest_arrival_arrival_only` in `scripts/routing_reference/arrival_only.py`) on the real Hanoi graph. Every result is `INEXACT`. On 2026-10-09 the run covered 30 node pairs, 21 (table, step) settings, and four vehicles. All 2,520 comparisons came back inexact, so the run reports no share of "sticky gives no route" and no share of "sticky gives a longer route".

The cause is in the search, not in the data. The arrival-only closure is not monotone in time. A road that is closed at one arrival time can be open at a later one, because the flood recedes, so an earlier arrival at a node is not always better. The search therefore keeps several arrival-time labels per node, up to `max_labels_per_node` (16). A result is exact only when no label earlier than the answer was dropped at that cap.

The real graph breaks this condition. `real_graph.py` treats every road as open in both directions (the export has no one-way flag). A route can walk from node A to node B and back to A. That walk reaches A again at a later, different time and counts as a new label. A few such loops near the origin fill the 16 labels of the nearby nodes, and the search then drops labels that are earlier than the destination arrival. The search has no way to tell that those labels do not matter, so it reports the result as inexact.

## Plain-language explanation

**The game.** We want to know the fastest way to walk to school. Some streets flood, and the water goes up and down as time passes. A street is closed when it has too much water at the moment you reach it.

**Two kinds of walkers.** The sticky walker looks at a street before leaving home and again on arrival, and avoids a street that might close. The arrival-only walker looks at a street only at the moment they reach it. We want to count how often the sticky walker does worse than the arrival-only walker. That count is the `US-093` result.

**The trouble.** To be fair, the arrival-only walker must try every possible way to walk. On our map every street can be walked in both directions, so the walker can also go to the next corner and back, again and again. Each trip back and forth makes a new "walking story", and there are millions of them. The program keeps only 16 stories per corner, and the silly back-and-forth stories fill the space. The program then cannot be sure it found the best way, so it says "inexact", meaning "I am not sure". It said that every time. Keeping 64 or 256 stories did not help.

**Why a decision is needed.** There are two ways to fix the program, and they give different answers. The paper has to say which one we used, so the choice is yours.

- **Rule A, never visit the same corner twice.** No back and forth. This is the easiest to explain. The paper would say "earliest arrival over routes that visit no node twice".
- **Rule B, ignore stories that are clearly worse.** The walker keeps the old rules, but the program needs a careful written proof that ignoring those stories is safe when the water goes down.
- **Waiting by walking back and forth.** Under the old rules, the walker can pass time on purpose until a flooded street opens. Rule A forbids this. Rule B and the current search allow it.

**How to answer.** Say which rule (A or B), or say "measure first" so that both are tried on 10 trips and the numbers are shown to you. Say whether waiting by walking back and forth is allowed. Give a number for "sure enough", for example "95 answers out of 100 must be certain". Give the longest run time, for example "2 hours". Give the sprint for the fix. The shortest useful answer is "measure first, Sprint 12".

## Why this matters

`US-093` measures how often the sticky rule gives no route or a longer route than an arrival-only reference. Without an exact reference, the story has no result. `US-093` is part of the routing paper experiments in [[EP-14-routing-paper-experiments]], and the paper handoff needs its numbers.

The blocker does not stop build work in the next sprint. Sprint 13 in [[SP-04-frontend-recheck]] is the frontend recheck and reads none of this code. Under the blocker rules in `.claude/CLAUDE.md` (rule 11), this is the case where a subagent can fix the code while the next sprint continues. The fix still waits for a decision from you on the definition of the reference, because the definition changes what the paper claims.

## Approaches tried

### Approach 1

Ran the reference with the default cap of 16 labels per node on the real graph. Result: 2,520 of 2,520 comparisons inexact. The run took about 1.7 s per comparison.

### Approach 2

Raised the cap on one pair set (4 pairs, one vehicle limit of 30 cm, the first table, step 0). Results are in the following table.

| Cap | Exact | Time per pair |
| --- | ----- | ------------- |
| 16 | no | 0.2 to 1.6 s |
| 64 | no | 0.6 to 7.6 s |
| 256 | no | 2.9 to 39 s |

A bigger cap does not make the result exact, and the cost grows faster than the cap. This approach is closed.
### Approach 3

Ran option A (`marie-curie/arrival_only_simple_path.py`) on the real graph through `marie-curie/run_option_a_real.py`. The run used 15 node pairs (5 per length class), the 4 vehicles, 2 tables (`20261009T024500` and `20261009T031500`) at steps 0 and 4, and a budget of 3,000,000 label expansions per search. One-way roads are open both ways and travel time is length at 30 km/h. It ran on the Mac for 618 s of wall time on 4 workers. The result file is `marie-curie/us-099/option_a_real_seed1.json`, and the evidence image is `us-099-option-a-real-graph-output.png` ([[US-099-run-the-simple-path-arrival-only-search-on-the-real]]).

| Vehicle | Searches | Exact | Exact rate | Mean time | Maximum time |
| ------- | -------- | ----- | ---------- | --------- | ------------ |
| motorbike | 60 | 30 | 0.50 | 10.0 s | 26.6 s |
| car | 60 | 28 | 0.47 | 10.3 s | 26.9 s |
| truck | 60 | 28 | 0.47 | 10.1 s | 27.4 s |
| foot | 60 | 28 | 0.47 | 10.1 s | 27.6 s |

In all, 114 of 240 searches were exact (0.475). The result splits in two. Every exact search took 0.08 s or less, and every inexact search used the whole budget (about 19 s). By length class, 80 of 80 searches under 2 km were exact, 19 of 80 between 2 and 5 km, and 15 of 80 over 5 km. A pilot with a budget of 1,000,000 had an exact rate of 0.43 on 12 pairs, and one hard pair (7992 to 49964) became exact only at 3,303,174 expansions (21 s). So the exact rate rises with the budget, and the cost per hard pair grows with it. A first run with 30 pairs and a budget of 10,000,000 was stopped after 2 hours 26 minutes with no result, because it wrote output only at the end. Option A with the cap-free search is exact where it finishes, and it finishes only for pairs whose route is not blocked.

Every exact comparison with a route was `same` (112 of 112, plus 2 `neither`). No exact comparison showed a sticky route that was later or missing, and none broke the nesting check. This does not show that sticky closure costs nothing. The exact set holds the unobstructed pairs, so it leaves out the pairs where a closure forces a detour, which are the pairs `US-093` is about.

Evidence from the four-node grid (`marie-curie/flood_scenario_grid.py`, 654 scenarios after removing duplicates), which shows only that the rules differ and cannot show scale:

- The capped, loop-allowed arrival-only search arrives earlier than the simple-path search in 94 scenarios.
- The capped search is inexact in 72 scenarios.
- Sticky closure arrives later in 64 scenarios, and has no route where arrival-only has one in 128. The two rules give the same arrival in 242 scenarios, and neither finds a route in 220.

### Approach 4

Pruned the option A search with two bounds from a relaxation in which the traveller may wait and loop (2026-10-09). The relaxation never rules out a real route, because every route of option A is also a route of the relaxation.

1. `latest[v]` is the latest time a traveller can be at node `v` and still reach the destination in the relaxation. A label that arrives at `v` later than `latest[v]` is dropped. A reverse search from the destination computes it, and it stops once the latest time falls below the departure.
2. The time left to the destination is the shortest travel time over the roads that are open at some step from the departure on. A road closed at every such step is left out.

Before the change, a destination that every closed road shut off made the search enumerate every simple path, and that was the cause of the 27 s searches. The code is `scripts/routing_reference/arrival_only.py` (`SimplePathSearch`), and the capped loop search it replaces is kept in `marie-curie/arrival_only_loops.py` for the grid evidence.

The run used the same setting as approach 3 (15 pairs, 4 vehicles, 2 tables, steps 0 and 4, budget 3,000,000, seed 1). Results are in `marie-curie/us-099/option_a_pruned_seed1.json`.

| Vehicle | Searches | Exact | Exact rate | Mean time | Maximum time |
| ------- | -------- | ----- | ---------- | --------- | ------------ |
| motorbike | 60 | 57 | 0.95 | 1.5 s | 27.5 s |
| car | 60 | 59 | 0.98 | 0.7 s | 32.6 s |
| truck | 60 | 60 | 1.00 | 0.2 s | 0.2 s |
| foot | 60 | 59 | 0.98 | 0.8 s | 35.4 s |

In all, 235 of 240 searches were exact (0.979), against 114 of 240 in approach 3. The run took 76 s of wall time on 4 workers, against 618 s. Every exact search took 0.43 s or less. The 5 inexact searches are 3 pairs, all over 5 km, and each spent the whole budget. By length class, 80 of 80 searches under 2 km, 80 of 80 between 2 and 5 km, and 75 of 80 over 5 km were exact.

The exact set now holds pairs where a closure matters. Of the 233 exact searches with a route, 231 were `same` and 2 were `sticky_longer`. None broke the nesting check. This sample is 15 pairs, so these counts show that the comparison now produces results, and they are not the `US-093` shares.

Tests: the search matches a brute-force enumeration of every simple path on 1,900 seeded random graphs (the new 1,500-case set has roads that close and reopen). A destination shut off by a closed road ends with 0 expansions on a 6 by 6 grid. A separate run of 6,000 cases found 0 mismatches.

## Options remaining

Each option changes what "arrival-only" means. Option A and option B change the definition. Option C keeps the definition and gives up exactness.

1. **A. Simple paths only.** A label may not visit a node that is already on its own path. This removes the loops, so the number of labels per node stays small. It answers the question "which route that does not repeat a node arrives first?". It is a defensible definition, because the sticky search is a shortest-path search, and a shortest-path search returns routes that do not repeat a node. It is no longer a lower bound that includes deliberate loops to burn time until a road opens. Measured on 2026-10-09 (approach 3): the exact rate is 0.475 at a budget of 3,000,000 expansions, with a cost of up to 27 s per search, so option A does not give an exact reference for every pair on the real graph.
2. **B. A dominance rule.** A label at a node is dropped when another label at the same node is provably at least as good. Closure depends on the arrival time only through the forecast step (the step at or before the arrival), so labels in the same step interval look alike. The rule is valid only if an earlier label can follow every continuation of a later one and never meet a closed road that the later one passes. That holds while the flood only rises. It does not hold when the flood recedes. This option needs a written proof for the recession case before the code is trusted. It keeps the definition of the reference.
3. **C. Report the share of exact comparisons and the bound.** Keep the search as it is, report how many comparisons were exact, and report the sticky result only for those. On the real graph this is currently zero, so this option alone yields no result. It works only together with option A or option B, or with a smaller graph.

## Decision and explanation

Decided on 2026-10-09 by the user (definition only; questions 3 to 5 are still open).

**Decision.** The arrival-only reference is option A. Its paper sentence is "the earliest arrival over routes that visit no node twice". Option B is not pursued. The departure time of each trip is fixed, and the walker cannot delay it.

**Answers to the questions under "What your input needs to include".**

1. Definition: option A.
2. Loop-and-wait: not allowed.
3. Exact enough: not yet given.
4. Cost limit and pair count: not yet given.
5. Sprint: not yet given. `US-100` already sits in Sprint 12.
6. Measure first: not needed for the definition, because approach 3 already measured option A.

**Why.**

1. A walker who finds a road flooded is routed another way. No one walks to a flooded road, turns back, and tries again, so a reference that allows loops measures a route that no vehicle drives.
2. Waiting out a flood at the origin is a choice of departure time, not a choice of route. `US-093` compares two closure rules for the same trip at a fixed departure. If the walker may delay the departure, both rules eventually find a route, and the share of "sticky gives no route" loses its meaning.
3. A loop can beat the best alternative only when no good alternative exists. In that case the real answer is "no route now", not "walk in circles".
4. The flood does not start to recede before about minute 30. Each loop on a short road costs a few minutes, so a loop does not reach a reopened road sooner than a sensible detour does.
5. Option B existed to keep loop-and-wait in the reference. With loop-and-wait out, B has no remaining purpose, and its recession proof would be work for a definition no one wants.

**What stays open.** The definition is settled, and the cost is not. Option A is exact for 0.475 of the searches on the real graph at a budget of 3,000,000 expansions (approach 3). Every inexact search used the whole budget. The remaining ways to close the gap are a faster implementation, a stronger bound that prunes the search, or a smaller sample or graph. The blocker stays `open` until one of them reaches the exact-enough bar, which the user has not set.

**Assumption to confirm.** The departure time is fixed per trip and per forecast step. This follows from why 2 above, and the paper's method section has to say it.

## What your input needs to include

A decision on this blocker lets me act when it answers the following questions. A short answer to each is enough.

1. **Which definition of arrival-only do you want?** Choose A (simple paths only), B (dominance rule, with a proof), or "measure first". If you choose A or B, say in one sentence how the paper should describe the reference, for example "the earliest arrival over routes that visit no node twice". The sentence is what ends up in the method section, so it has to be one you can defend to a reviewer.
2. **Is loop-and-wait allowed in the reference?** In plain words: may the reference "waste time" on purpose by walking back and forth so that a road opens? If yes, only option B (or the current search) fits. If no, option A fits.
3. **What counts as exact enough?** Give a number, for example "at least 95 percent of comparisons exact per vehicle and setting". If the exact rate is lower, say whether I should report the partial result with the share of exact comparisons, or stop and come back to you.
4. **What is the cost limit?** Give the longest run time you accept for the full run, for example "under 2 hours on the Mac with 8 processes", and the pair count you want (the first run used 30 pairs). I use these to size the search and the sample.
5. **Which sprint?** Give the sprint number for the fix. The current plan covers Sprints 9 to 12. `US-093` is in Sprint 12, and Sprint 13 is in [[SP-04-frontend-recheck]]. A new fix must exist as a story with a sprint before it appears in `TODOS.md`. If you do not name a sprint, I will propose Sprint 12 and ask again.
6. **May I measure first?** If you are not sure about options A and B, answer "measure first". I then build both variants behind a switch, run them on 10 pairs of the first table, and report the exact rate and the time per pair for each. You choose after you see the numbers. This takes little work and changes no result file.

A good input looks like this:

> Use option A. Describe it as "earliest arrival over routes that visit no node twice". Loops to wait are not allowed. Exact enough means 95 percent per vehicle. Allow 2 hours on the Mac with 8 processes and 30 pairs. Put the fix in Sprint 12.

An input that only says "make it exact" is not enough, because "exact" is not defined without the choices above.

## Concerns

Before approach 4, option A was exact for 0.475 of the searches on the real graph (51,328 nodes) at a budget of 3,000,000 expansions, and the exact set held only unobstructed pairs. After approach 4 the rate is 0.979, and the exact set includes pairs where a closure forces a detour. The 5 remaining inexact searches (3 pairs over 5 km) spend the whole budget. Choices that remain: a stronger bound for those pairs (a time-dependent lower bound for the time left), a larger budget, or a report of the exact share next to the result, which option C describes. Whether 0.979 is exact enough is the open question 3.

The sticky side is not in question. A seeded test of 300 graphs in `scripts/routing_experiments/test_sticky_cost.py` shows that the sticky rule never ends earlier than the arrival-only reference. That property holds only for an exact reference, so the same exactness limit applies to it.

## Related topics

- [[sticky-closure-proof]]
- [[sticky-routing-reference]]
- [[BL-024-edge-export-has-no-node-ids]], which made the real-graph run possible.

## Status history

- **2026-10-09, open.** Found by the first real-graph run of `US-093` (all 2,520 comparisons inexact). Approach 1 (cap 16) and approach 2 (caps 64 and 256) failed. The blocker does not stop build in the next sprint (rule 11), and the fix waits for your decision on the definition of the reference.
- **2026-10-09, open.** Added the "Plain-language explanation" section at the user's request.
- **2026-10-09, open.** Approach 3 ran option A on the real graph (`US-099`): exact rate 0.475 (114 of 240 searches) at a budget of 3,000,000 expansions, mean 10 s and maximum 27.6 s per search. The blocker stays open. The measured rate does not meet an exact-enough bar such as 95 percent, and the decision between option A, option B, and sticky closure is in `US-100`.
- **2026-10-09, open.** The user chose option A as the definition of the reference: the earliest arrival over routes that visit no node twice. Loop-and-wait is not allowed, and the departure time is fixed per trip. Option B is dropped. The exact-enough bar, the cost limit, and the sprint are still open, so the blocker stays `open`. The cost of option A (0.475 exact) is the remaining problem. `approaches_remaining` goes from 2 to 1.
- **2026-10-09, open.** Approach 4 (pruned option A, now in `scripts/routing_reference/arrival_only.py`) raised the exact rate from 0.475 to 0.979 (235 of 240) and cut the wall time from 618 s to 76 s. Option B is not needed. The blocker stays `open` until the user sets the exact-enough bar (question 3). If the bar is 95 percent per vehicle, every vehicle meets it (motorbike 0.95, car 0.98, truck 1.00, foot 0.98). `approaches_remaining` stays 1: a stronger bound for the 3 pairs left.
