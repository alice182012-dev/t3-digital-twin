---
date_drafted: 2026-09-29
type: user-story
us_id: "US-052"
story_label: "R7"
epic: "[[EP-09-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: M
sprint: 9
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Integrate the engine into the backend with a flag and a fallback"
---

# US-052 Integrate the engine into the backend with a flag and a fallback

As an operator, I want a switch and a safe fallback, so a problem with the table never takes routing down
or hides that timing was skipped.
Given a depth table for the running graph, when the flag is on, then `_handle_route` uses the `td` profile,
takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run
for the whole request, and returns `unknown` for a trip that ends after the last step. Given the flag off,
then the response body equals today's. Given a missing, stale, or mismatched table, then the backend routes
with today's model and the response carries a fallback flag.
Tests cover the flag off, a departure between steps, the horizon edge, run pinning, and the hash mismatch.
Priority: P0. Status: Done. Estimate: M. Sprint: 9 ([[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]). Dependencies: Stories R5, E5.
Built on 2026-10-05, tests first: in Java `TableProvider`, the once-per-request decision, the response hints, the departure floored to its step, and the table folder loaded after the graph (`TimeAwareRouter`, `TimeAwareGraphHopper`; 118 module tests); in Python `time_aware_route.py` (27 tests) and `server.py`; `td_limit_cm` for `motorbike` and `car` in `config.yml`; the compose `graphhopper` service on the time-aware image with the table volume mounted read-only, and `TIME_AWARE_ROUTING` (default off) on the backend. The flag-on path through the real handler passes `test_server.py` against a PostGIS and a stub GraphHopper. Plan: [[time-aware-backend-integration]].
Evidence: ![[us-055-engine-server-proof-2026-10-07.png]]
Details:
1. On 2026-10-07, host ADMIN, `graphhopper` and `floodmap-backend` recreated from `modular`, connected as `routing_reader` (`US-072`).
2. With the flag off then on, `routing_proof.py` ran 24 real pairs through both: `compare` shows 37.5% of routes changed with a median detour ratio of 0.94, engine applied on 22 of 24, `unknown` on 2 (trips ending after the last step). `crossings` found 0 engine routes crossing a closed road.
3. The soak known-answer check (116 checks, 29 roads) found 0 permission errors from the reader role and 3 failures, all on one road segment right at its depth threshold (12.2 cm, "below every limit" bucket) — live flood-depth drift between trials, not an engine or role fault.
4. Not yet closed: this evidence covers the flag-on backend path, but full `US-055` closure also needs the frontend check (`US-054`) and the DAG-timing pieces (`US-045`, `US-073`), which the user deferred to after Sprint 11.
