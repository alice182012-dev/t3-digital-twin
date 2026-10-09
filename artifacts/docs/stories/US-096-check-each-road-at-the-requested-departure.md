---
date_drafted: 2026-09-29
type: user-story
us_id: "US-096"
story_label: "R11"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: S
sprint: 12
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Check each road at the requested departure, not the floored one"
---

# US-096 Check each road at the requested departure, not the floored one

As a traveller, I want the engine to close a road that is too deep when I reach it, so a departure between two forecast steps does not shorten the margin of the rule (blocker [[BL-026-sticky-closure-clock-anchored-at-floored-departure|sticky-closure-clock-anchored-at-floored-departure]]).
Given a road that is wet from the step at 1,800 s, a departure requested at 840 s, and a trip that enters the road 1,000 s in, when the engine plans the route, then the road is closed.
Today the engine admits it.
The first test reproduces the example in Java and fails, then the fix makes it pass.
`StickyClosure` keeps the floored step as the start of its window and the requested departure as the arrival clock, and `TimeAwareDijkstra` and `StickyChecker` check at the requested departure plus the elapsed time.
`check_crossings` in `scripts/routing_proof/routing_proof.py` and the harness of `US-091` (`scripts/routing_experiments/experiment.py`, line 90, which reads `td.departure`) walk from the requested departure.
The Java suite and the Python suite pass, and a case with a departure exactly on a step gives the same result as before.
Dependencies: none to build.
The server check waits for a rollout of the `graphhopper` image, which needs no replay running.
`US-091` reports its engine result after this.

## Evidence and details

**Evidence:** None to build.
`US-091` reports its engine result after it

**Details:**

![[us-096-fix-check-output.png|120]]
