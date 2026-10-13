---
date_drafted: 2026-10-13
type: user-story
us_id: "US-135"
title: "Find why LIVE routes find no connection between wet edges"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Not started
kind: spike
priority: P2
estimate: S
sprint: 
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

## Evidence and details

Fill this when the story reaches `Done`.
