---
date_drafted: 2026-09-29
type: user-story
us_id: "US-046"
story_label: "R1"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: S
sprint: 5
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Record the routing baselines on the server"
---

# US-046 Record the routing baselines on the server

As the team, I want the server's latency, edge count, image revision, and step length written down, so
every later story has a real baseline instead of a guess.
Given the running stack on the server, when the measurements run, then the blocker page lists the p50 and
p95 of `POST /route` (flexible mode with LM) for a short, a medium, and a long Hanoi trip, the edge count of
`hanoi-model-area.osm.pbf`, the source revision of the pinned GraphHopper image, and the step length and
count of one real run.
Priority: P0. Status: Done. Estimate: S. Sprint: 5. Dependencies: None. The latency numbers waited for the `US-037` knob, which settled on 2026-10-02.
Evidence: ![[us-046-baselines-check-output.png|700]]
Details:
1. What: the server's baselines are written in "Baselines on the server" of [[BL-011-routing-not-time-aware|routing-not-time-aware]]. The graph has 67,833 edges, the image's source is GraphHopper commit `d7dc1b06`, a run has 8 steps 15 minutes apart, and the p50 and p95 of `POST /route` are recorded for a short, a medium, and a long trip in four setups.
2. How: `scripts/backend_soak/soak_checks.py latency` ran inside `airflow_new-floodmap-backend-1` on 2026-10-02 from 02:39 to 02:49 +07, with 30 requests per cell in flexible mode with LM, for the motorbike and the car. The setups are GraphHopper alone, GraphHopper with the run's flood model, the backend with its area cache, and the backend without it. The edge count, image, and step facts come from read-only commands on the server. Tests came first (29 in `scripts/backend_soak/`).
3. Why: the PRD leaves the latency factor open until a baseline exists, and two PRD assumptions were wrong (2,000,000 edges and 9 steps).
4. Effect: GraphHopper alone answers in 8 to 21 ms at the p50, and the flood model raises that to 153 to 1,857 ms. The app's own path takes 126 to 2,759 ms, and a miss of the 30-second area cache adds 0.6 to 1.0 s. The user can now set the latency factor. `US-049` can pin commit `d7dc1b06`. The numbers were taken under pipeline load (load average about 10 on 12 CPUs), so a quiet host can be faster.
