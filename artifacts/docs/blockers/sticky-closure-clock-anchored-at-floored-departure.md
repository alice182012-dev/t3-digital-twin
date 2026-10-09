---
date_open: 2026-10-09
date_closed: 
type: blocker
status: monitoring
severity: P1
subsystem: time-aware-routing
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, routing, sticky-closure, correctness]
related: ["[[sticky-closure-proof]]", "[[time-aware-routing-engine-stories]]", "[[US-090-093-routing-paper-experiments-stories]]", "[[routing-not-time-aware]]"]
last_updated: 2026-10-09
---

# sticky-closure-clock-anchored-at-floored-departure

## Description

The engine checks each road at the wrong time. `TimeAwareRouter.decide` floors the requested departure to the forecast step that contains it (`TimeAwareRouter.java`, line 86) and builds the `StickyClosure` with that floored time. `TimeAwareDijkstra` then checks each road at `closure.departureEpochMs() + enterMs` (line 94), and `enterMs` counts from the real departure. Every checked time is earlier than the real arrival by `delta`, the gap between the requested departure and the floored step, where `0 <= delta < 900 s`. The effective margin is 600 s minus `delta`, which is negative when `delta` is more than 600 s.

Example, from the Python reference: a road is wet from the step at 1,800 s, the departure is requested at 840 s and floored to 0 s, and the traveller enters the road 1,000 s into the trip. The engine checks the window [0, 1600 s] and admits the road. The real entry is at 1,840 s, after the road is wet, and the window [0, 2440 s] closes it.

Found by the author of `US-090` while writing [[sticky-closure-proof]], Part 6. It was read in the code by the lead on 2026-10-09. It was not reproduced in Java.

## Why this matters

A route can enter a road that is already too deep when the traveller reaches it. That is the failure the engine exists to prevent. The check of the server proof (`check_crossings` in `scripts/routing_proof/routing_proof.py`) walks from the same floored departure, so the proof of 2026-10-07 (0 crossings) cannot detect it. `US-091` expects the engine to report 0 violations, and its re-walk must start at the requested departure, or it hides the same error. The paper claim of an exact search needs the engine and the proof to use one clock.

Rule 11 case: it does not block building the harness of `US-091`. It blocks reading `US-091`'s engine result, so the fix (`US-096`) comes before that result is reported.

## Approaches tried

### Approach 1

Keep two times in `StickyClosure`: the floored step, where the window of wet steps starts, and the requested departure, from which the arrival clock runs. `TimeAwareDijkstra` and `StickyChecker` check at the requested departure plus the elapsed time. A test with the example above fails first.

## Decision and explanation

Approach 1 was built as planned (`US-096`). `StickyClosure` keeps the floored step as the window start and the requested departure as the arrival clock. The blocker resolves after the `graphhopper` image is rebuilt on the server and a route with a departure between two steps is checked there.

## Concerns

`td.departure` in the response reports the floored time today. Whether it should report the requested time changes the frontend's reading, so check its readers.

## Related topics

- [[sticky-closure-proof]]
- [[time-aware-routing-engine]]

## Status history

- **2026-10-09, open.** Found by the subagent that wrote the proof page, confirmed by reading `TimeAwareRouter.java:86-88` and `TimeAwareDijkstra.java:94`. Story `US-096`, Sprint 12.
- **2026-10-09, monitoring.** `US-096` fixed it in code (`66c9883`). 129 Java tests pass on GitHub Actions (run 37880057761) and the Python suites pass. The server still runs the old image until the next rollout. Evidence: `us-096-fix-check-output.png`.
- **2026-10-09, monitoring.** `rollout.ps1` rebuilt the server's `graphhopper` image from `modular` (`11f6373`), meeting the first half of the resolve condition. The server was not separately checked with a departure between two forecast steps, so the blocker stays `monitoring` rather than moving to `resolved`.
