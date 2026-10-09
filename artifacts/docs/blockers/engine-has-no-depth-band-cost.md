---
date_open: 2026-10-09
date_closed: 2026-10-09
type: blocker
status: resolved
severity: P2
subsystem: time-aware-routing
approaches_tried: 1
approaches_remaining: 2
tags: [blocker, routing, cost-band, us-092]
related: ["[[US-090-093-routing-paper-experiments-stories]]", "[[time-aware-routing-engine-stories]]", "[[sprint-plan-3]]", "[[sticky-closure-proof]]"]
last_updated: 2026-10-09
---

# engine-has-no-depth-band-cost

## Description

Story 3 (`US-092`) asks for a sweep of the start of the cost band at 25, 50, and 75 percent of the vehicle limit. No code or PRD defines that band.

- `TimeAwareWeightingFactory.createWeighting` returns what the stock factory returns. Its comment says "For now it returns what the stock factory returns", and "The time-aware wrapper (`US-050`) is added here."
- The engine only closes roads. `StickyClosure` and `TimeAwareDijkstra` have no cost term for depth.
- `artifacts/docs/prds/time-aware-routing-engine.md` has no cost band. The only mentions of one are the docstring of `scripts/routing_reference/sticky_reference.py` ("The engine's depth-band cost factors are left out on purpose") and the text of Story 3.
- The 5 cm bands of `flood_extent_polygon` and the `depth_bands_m` of `flood_utils.py` are display and scoring bands of the backend. Neither is a routing cost.

The sweep of the vehicle limits and the regret table are built (`limit_sweep.py`, `bb00594`). Only the band sweep has nothing to vary.

## Why this matters

`US-092` cannot reach `Done` as written, because one of its three sweeps has no model. The paper answer to "why 20 and 35 cm" does not need the band, so the limit sweep can still report. The blocker does not stop Sprint 13 (the frontend recheck), and it does not stop the build of `US-091` or `US-093`.

## Approaches tried

### Approach 1

Searched the Java module, the PRD, and the concept pages for a cost band on 2026-10-09. Found none (see Description).

## Decision and explanation

The user chose neither option on 2026-10-09 and set a third (D-021): a precaution depth at 50 percent of the limit, with the hard-limit route kept as a second option. It is two plain closure rules and needs no cost term. The two options considered were:

1. Define the band as a new cost term in the engine (a story of its own, with a PRD change), then sweep it.
2. Drop the band sweep from `US-092` and state in the result file that the engine closes roads and adds no depth cost.

Option 2 matches the engine as shipped. Option 1 changes routing behavior and needs its own proof.

## Related topics

- [[US-090-093-routing-paper-experiments-stories]] Story 3
- [[time-aware-routing-engine-stories]]

## Status history

- **2026-10-09, open.** Found while reviewing the offline sweep. Rule 11 case: it does not block build in the next sprint, so no fix comes first. It blocks only the band part of `US-092`. The user is asked to pick option 1 or 2.
- **2026-10-09, resolved.** D-021 replaces the cost band with a precaution depth. The band sweep of `US-092` becomes a sweep of the precaution fraction (25, 50, and 75 percent). Engine work is `US-097`.
