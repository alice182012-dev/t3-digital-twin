---
date_drafted: 2026-10-09
type: user-story
us_id: "US-100"
story_label: "6"
epic: "[[EP-20-routing-paper-experiments]]"
status: Done
kind: spike
priority: P2
estimate: XS
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]", "[[US-099-run-the-simple-path-arrival-only-search-on-the-real]]", "[[sticky-closure-proof]]", "[[sticky-routing-reference]]"]
title: "Decide between option A closure and sticky closure for a vehicle already on the route"
---

# US-100 Decide between option A closure and sticky closure for a vehicle already on the route

As the owner of the routing product, I want a decision on whether the engine keeps sticky closure or moves to the arrival-only rule of option A, so the paper and the engine describe the same closure rule.
Given the grid evidence and the result of `US-099`, when the closure rule of each option is read against a vehicle that is already on the route, then Status history records the chosen rule, the reason, and what the choice costs.
This is a product question and not a correctness question. On the four-node grid (654 cases), sticky closure has no route in 128 cases where option A has one, and it arrives later in 64 cases. If option A can send a vehicle into a segment that floods while the vehicle is still in it, sticky closure is the safer default, even at the cost of 64 later arrivals and 128 lost routes. The work is to check what each closure rule means for a vehicle already on the route: for each rule, read the depth at which instant of the traversal, and say whether a vehicle can be inside a segment when its depth reaches the limit. The reading uses `scripts/routing_reference/arrival_only.py`, `scripts/routing_reference/sticky_reference.py`, and [[sticky-closure-proof]]. The decision belongs to the user. Claude prepares the reading and a recommendation.
The grid counts come from a four-node model. Cite them as grid evidence, and cite the real-graph rate from `US-099` next to them once it exists.
Priority: P2. Status: Done (2026-10-10). Estimate: XS. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]).
Dependencies: the reading of the two closure rules can start now. The decision waits for `US-099`, because a rate that does not scale changes the cost side.
Evidence: None yet. A decision story reaches `Done` with the decision and its reason written in Status history, a numbered details list, and a screenshot of the output that shows the closure reading (rule 8).
Blocker tracking: [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], question 1 and question 2.

## Status history

- **2026-10-09, not started.** The user decided the definition of the arrival-only reference in [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]: option A, "the earliest arrival over routes that visit no node twice", with no loop-and-wait and a fixed departure time. The reason is that no vehicle loops to wait out a flood, and waiting at the origin is a choice of departure time, not of route. This fixes the reference only. The question of this story, whether the engine keeps sticky closure or moves to arrival-only closure, is still open, so the story stays `Not started` and `Done` needs the closure reading and the engine decision. The cost side of option A is 0.475 exact on the real graph ([[US-099-run-the-simple-path-arrival-only-search-on-the-real]]).
- **2026-10-09, not started.** Written from the user's list of next steps for `BL-027`. This is separate from `US-099`: the run measures option A, and this story decides which rule the engine and the paper use.
- **2026-10-10, done.** The user decided to keep sticky closure ([[decision-log|D-023]]): conservative protection of the asset and the person, with no chance of a vehicle being flooded halfway along a road. The reading is in the evidence below. The real-graph cost from `US-093` comes with that story's final run and does not change the decision.

## Evidence and details

**Evidence:** rendered output of `evidence/us-100-closure-reading.py`, which runs `ArrivalOnlyClosure` and `StickyClosure` from `scripts/routing_reference/` on the two cases.

![[us-100-closure-reading-output.png|800]]

**Details:**

1. Built: the closure reading of the two rules for a vehicle already on the route, with a script that reproduces it, and the decision to keep sticky closure.
2. How: arrival-only reads the depth at the forecast step at or before the moment of entry (`StepRule.AT_OR_BEFORE`). Sticky reads every step from the start of the window to 10 minutes after entry, and a step at or over the limit closes the road for good. In case 1 (a 2 km road, 4 minutes, depth 10 cm at 08:00 and 40 cm at 08:15, car limit 30 cm, entry 08:12) arrival-only calls the road open and the limit is reached at 08:15 while the car is on it. Sticky closes it. In case 2 (40 cm at 08:00 and 5 cm at 08:30, entry 08:45) arrival-only calls the road open and sticky keeps it closed.
3. Why: a vehicle that leaves on a road that floods halfway has no way out, so the user chose safety over a shorter route. The cost is routes lost or later (128 and 64 of 654 on the grid), which `US-093` measures on the real graph.
4. What it changes: nothing in the code, because the engine already uses sticky closure. For dependent work, `US-093` keeps option A as its reference and reports the sticky-longer rate as the price of safety, and the paper states sticky closure as the engine's rule. [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph|BL-027]] still needs your answer on the exact-enough bar.

