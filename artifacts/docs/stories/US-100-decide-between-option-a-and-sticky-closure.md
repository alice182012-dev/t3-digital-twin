---
date_drafted: 2026-10-09
type: user-story
us_id: "US-100"
story_label: "6"
epic: "[[EP-14-routing-paper-experiments]]"
status: Not started
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
Priority: P2. Status: Not started. Estimate: XS. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]).
Dependencies: the reading of the two closure rules can start now. The decision waits for `US-099`, because a rate that does not scale changes the cost side.
Evidence: None yet. A decision story reaches `Done` with the decision and its reason written in Status history, a numbered details list, and a screenshot of the output that shows the closure reading (rule 8).
Blocker tracking: [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]], question 1 and question 2.

## Status history

- **2026-10-09, not started.** The user decided the definition of the arrival-only reference in [[BL-027-arrival-only-reference-is-inexact-on-the-real-graph]]: option A, "the earliest arrival over routes that visit no node twice", with no loop-and-wait and a fixed departure time. The reason is that no vehicle loops to wait out a flood, and waiting at the origin is a choice of departure time, not of route. This fixes the reference only. The question of this story, whether the engine keeps sticky closure or moves to arrival-only closure, is still open, so the story stays `Not started` and `Done` needs the closure reading and the engine decision. The cost side of option A is 0.475 exact on the real graph ([[US-099-run-the-simple-path-arrival-only-search-on-the-real]]).
- **2026-10-09, not started.** Written from the user's list of next steps for `BL-027`. This is separate from `US-099`: the run measures option A, and this story decides which rule the engine and the paper use.
