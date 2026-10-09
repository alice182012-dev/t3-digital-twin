---
date_drafted: 2026-09-23
type: user-story
us_id: "US-003"
story_label: "2"
epic: "[[EP-01-frontend-depth-features]]"
status: Done
priority: P0
estimate: S
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-01-frontend-depth-features]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Per-step depth in turn-by-turn instructions"
---

# US-003 Per-step depth in turn-by-turn instructions

As a user following a route, I want to see the depth at each turn alongside its distance, so I
know what to expect before I reach it.
Given a route exists, when each turn-by-turn step in the expanded instructions list renders, then
it shows its depth next to its distance on the same line ("320 m · 8 cm"), matching mockup screen
2e.
Priority: P0. Status: Done. Estimate: S. Sprint: 3. Dependencies: [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 3, Story 4.
Evidence: ![[frontend-per-step-depth-live-check.png|420]] ![[frontend-per-step-depth-preview-check.png|420]]
Details:
1. What: each step in the expanded instructions list shows the water depth at its start point after its distance, for example "134 m · 16 cm", in Flood mode. Map mode shows the distance only.
2. How: `useStepDepths` requests `GET /flood/points` for every step at the selected timestep, and `stepDepthText` prints the reading. `depthQuery` builds the query and is shared with the place-depth popup. The step's depth is the depth at its start point, not the deepest point along it.
3. Why: a user can see what to expect before reaching each turn.
4. Effect: checked on a preview build on the server (port 8083) against the real backend, with the browser clock set to 2026-09-29 17:00 +07:00 because the pipeline is paused. A 5-step route from a start point that is 16 cm deep at the 16:45 step showed 16, 0, 0, 0, and 0 cm, the same as `GET /flood/points` for each start point. A 17-step route showed 0 cm on every step, also matching. A step with no reading prints nothing, so no step claims a depth it lacks. Each route costs one request per step. Deployed 2026-09-30 (`ac1ab84`). On the live frontend at 8082, with the real clock, all 17 steps of the car route from `21.0000,105.7450` to `21.0060,105.7520` show "N m · 0 cm" (`frontend-per-step-depth-live-check.png`). Tap-a-step (Story 4) can start.
