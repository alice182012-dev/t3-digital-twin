---
date_drafted: 2026-10-08
type: user-story
us_id: "US-090"
story_label: "1"
epic: "[[EP-14-routing-paper-experiments]]"
status: Done
priority: P1
estimate: M
sprint: 12
subsystem: routing, paper
related: ["[[EP-14-routing-paper-experiments]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
---

# US-090 Write the FIFO lemma and the correctness proof of the sticky-closure forward search

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
Priority: P1. Status: Done. Estimate: M. Sprint: 12 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]; 2026-12-07 to 2026-12-13).
Dependencies: None. The user's confirmation of "sticky from departure" is already in place (2026-10-02).
Evidence: None yet.
