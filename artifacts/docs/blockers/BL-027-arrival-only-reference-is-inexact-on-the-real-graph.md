---
date_open: 2026-10-09
date_closed: 
type: blocker
status: open
severity: P2
subsystem: time-aware-routing
approaches_tried: 2
approaches_remaining: 3
tags: [blocker, routing, arrival-only, us-093, paper-experiments]
related: ["[[US-093-measure-how-often-the-sticky-rule-gives]]", "[[US-092-test-how-the-vehicle-limits-change-the]]", "[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout]]", "[[BL-024-edge-export-has-no-node-ids]]", "[[sticky-closure-proof]]", "[[sticky-routing-reference]]"]
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

## Options remaining

Each option changes what "arrival-only" means. Option A and option B change the definition. Option C keeps the definition and gives up exactness.

1. **A. Simple paths only.** A label may not visit a node that is already on its own path. This removes the loops, so the number of labels per node stays small. It answers the question "which route that does not repeat a node arrives first?". It is a defensible definition, because the sticky search is a shortest-path search, and a shortest-path search returns routes that do not repeat a node. It is no longer a lower bound that includes deliberate loops to burn time until a road opens. The search can still grow large on a graph this size, so the exact rate has to be measured before you rely on it.
2. **B. A dominance rule.** A label at a node is dropped when another label at the same node is provably at least as good. Closure depends on the arrival time only through the forecast step (the step at or before the arrival), so labels in the same step interval look alike. The rule is valid only if an earlier label can follow every continuation of a later one and never meet a closed road that the later one passes. That holds while the flood only rises. It does not hold when the flood recedes. This option needs a written proof for the recession case before the code is trusted. It keeps the definition of the reference.
3. **C. Report the share of exact comparisons and the bound.** Keep the search as it is, report how many comparisons were exact, and report the sticky result only for those. On the real graph this is currently zero, so this option alone yields no result. It works only together with option A or option B, or with a smaller graph.

## Decision and explanation

Pending. See "What your input needs to include".

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

Option A can still be slow on a graph with 51,328 nodes, because finding the earliest simple path when travel depends on time is a hard problem in the general case. The measure-first run answers this.

The sticky side is not in question. A seeded test of 300 graphs in `scripts/routing_experiments/test_sticky_cost.py` shows that the sticky rule never ends earlier than the arrival-only reference. That property holds only for an exact reference, so the same exactness limit applies to it.

## Related topics

- [[sticky-closure-proof]]
- [[sticky-routing-reference]]
- [[BL-024-edge-export-has-no-node-ids]], which made the real-graph run possible.

## Status history

- **2026-10-09, open.** Found by the first real-graph run of `US-093` (all 2,520 comparisons inexact). Approach 1 (cap 16) and approach 2 (caps 64 and 256) failed. The blocker does not stop build in the next sprint (rule 11), and the fix waits for your decision on the definition of the reference.
- **2026-10-09, open.** Added the "Plain-language explanation" section at the user's request.
