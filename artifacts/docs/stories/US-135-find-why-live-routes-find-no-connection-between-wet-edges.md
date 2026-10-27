---
date_drafted: 2026-10-13
type: user-story
us_id: "US-135"
title: "Find why LIVE routes find no connection between wet edges"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
kind: spike
priority: P2
estimate: S
sprint: 14
subsystem: routing
source_ideas: []
related: ["[[graphhopper-backend]]", "[[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]]", "[[decision-log|D-043]]"]
tags: [user-story]
---

# US-135 Find why LIVE routes find no connection between wet edges

As a developer, I want to know why `LIVE` mode finds no route where `DEMO` finds one, so I can tell a flood result from an engine limit.

On 2026-10-13, 10 pairs of points on wet edges (700 to 1,500 m apart, motorbike) were routed in both modes.
`DEMO`, which uses the pinned step and skips the time-aware engine ([[decision-log|D-043]]), routed 1 pair (2,837 m).
`LIVE`, with `TIME_AWARE_ROUTING` on, answered "Connection between locations not found" for all 10, including when the request named the pinned step.
The question is whether the engine closes the area for a real reason (water that rises after the departure) or whether it has a fault.
The timebox is one day in `marie-curie/`.
The answer goes into this story with a `D-nnn` decision.

Given the 10 pairs and the pinned run, when the same request is sent in each mode with `td.limit_cm` and the depth along the `DEMO` route read from `edge_depth`, then the story states which edge closes the `LIVE` route and at which step.

Dependencies: [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] is `Reviewed`.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: it has no open dependency, it fits one sprint, and its acceptance is a check on the server.
- **2026-10-13, Reviewed.** Answered on the server in `marie-curie/us135/`. The owner has not accepted it, and [[decision-log|D-044]] holds the decision. `LIVE` finds no connection between points on closed edges by design, and `DEMO` and `LIVE` judge different steps. The engine has no fault in these tests.
- **2026-10-13, Done.** The product owner accepted the answer on the written results of details items 1 to 5 and [[decision-log|D-044]], with no screenshot.

## Evidence and details

**Evidence:** `marie-curie/us135/NOTES.txt`, the three pair files, and the scripts (scratch space, not tracked by git). The numbers are in details items 1 to 3.

**Details:**

1. Pairs between wet edges (10 pairs, motorbike). All 20 endpoints sit on edges of 25 to 56 cm, above the motorbike limit of 20 cm, at the pinned step (19:00 UTC of run `20261011T001500`) and at the step that the engine judged (19:15 UTC of run `20261011T003000`). `LIVE` routed 0 pairs. `DEMO` routed 1 (2,837 m). A route cannot start on a closed edge, so the first result was a flaw of the test.
2. Pairs with dry endpoints within 80 m of an edge of 30 cm or more at the pinned step (12 pairs). `LIVE` routed 12 (1.5 to 10 km). `DEMO` routed 0. `DEMO` judges the pinned peak, and `LIVE` judged run `20261013T104500`, a much smaller flood. The flood areas of `DEMO` are built from edges with a 22 m buffer ([[graphhopper-backend]]), which is the probable reason that endpoints within 80 m of the water are closed. The code was not read for this.
3. Pairs with dry endpoints 150 to 400 m from an edge of 20 cm or more (12 pairs). `LIVE` routed 12. `DEMO` routed 10 and gave the same distance as `LIVE` on 3 pairs (1,749, 1,971, and 1,112 m) and a distance within 2% on 2 more (2,139 and 2,141 m, 2,044 and 2,007 m).
4. The hints of a `LIVE` route name the step: `td.status: unknown`, `td.run`, and `td.departure` equal to `td.last_step`. The engine judges the newest table at its last step, whatever the request names ([[lessons#L-013|L-013]]).
5. Answer for [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]]: the point read and the route differ between the modes because the two modes judge different steps. A comparison of the modes needs the endpoints of [[decision-log|D-044]].

