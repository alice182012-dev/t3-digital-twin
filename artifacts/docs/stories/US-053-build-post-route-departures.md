---
date_drafted: 2026-09-29
type: user-story
us_id: "US-053"
story_label: "R8"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P1
estimate: M
sprint: 9
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Build `POST /route/departures`"
---

# US-053 Build `POST /route/departures`

As a traveller with no route now, I want to know the earliest time a route opens, so I can decide whether to
wait.
Given a real depth table and a route between two points, when the endpoint runs, then it requests the
flood-free route with `edge_id` and `time` details, reads depth by edge id, applies sticky closure from each
candidate departure with a 10-minute margin, and returns each candidate as `clear`, `blocked`, or
`unknown`, the earliest clear departure, the run, and the run's age. Candidates start at the step that
contains now. The client sends no clock value, margin, or policy.
Dependencies: Stories E2, E3, E4, R7.
Built on 2026-10-05, tests first. `POST /route/departures` in `departures.py` (30 tests) and `edge_depth_reader.py` (21 tests, on the shared golden fixture), served by `server.py`. The route is requested with no flood model, the `edge_id` and `time` details, and the hint `td_info`, which makes the engine answer with `td.graph_hash` and `td.run` (Java, 123 module tests). Every candidate matches `sticky_reference.py` on 300 random routes and tables, and five changes make tests fail (the window end, the horizon edge, steps before the departure counted, candidates that ignore now, no hash guard). A table that is missing, damaged, or for another graph gives `status: unavailable` and a reason. The client's clock, margin, and limit are dropped. `test_server.py` passes the endpoint end to end against a stub GraphHopper. Compose mounts the table volume into `floodmap-backend`. Plan: [[route-departures-endpoint]].
Evidence: ![[us-055-engine-server-proof-2026-10-07.png]]
Details:
1. On 2026-10-07, host ADMIN, three real trips (short, medium, long) hit `POST /route/departures` on the deployed backend against the live graph and the real `20261007T181500` table (age 513 s).
2. Short and medium each returned 8 real candidates (7 clear, 1 unknown) with an earliest-clear timestamp, in 72 ms and 14 ms. The long trip returned all 8 candidates `blocked` with no earliest-clear time, in 18 ms — the `edge_id`/`time` details lined up correctly against the real table in every case.
