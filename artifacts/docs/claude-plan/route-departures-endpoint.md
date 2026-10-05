---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-9, routing, backend, departures, us-053]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[time-aware-backend-integration]]", "[[sticky-routing-reference]]", "[[edge-depth-table-format]]", "[[departure-time-advice-research]]", "[[sprint-plan-3]]"]
---

# Plan: `POST /route/departures`, the earliest clear departure (US-053)

## Context

Acceptance, from [[time-aware-routing-engine-stories]] Story R8. Given a real depth table and a route between two points, the endpoint requests the flood-free route with the `edge_id` and `time` details, reads depth by edge id, applies sticky closure from each candidate departure with a 10-minute margin, and returns each candidate as `clear`, `blocked`, or `unknown`, the earliest clear departure, the run, and the run's age. Candidates start at the step that contains now. The client sends no clock value, margin, or policy.

The alert of `US-054` calls this when `POST /route` fails with no connection, and shows "The usual route is clear from HH:MM" or "No safe route in the next 2 hours".

## Design

1. **The usual route.** The backend asks GraphHopper for the route with no flood model and no time-aware search, with `details: ["edge_id", "time"]` and `points_encoded: false`. It is the route a traveller would take in the dry. The two details must line up one to one (one interval per edge), or the endpoint answers with an error rather than guessing the entry times. The PRD verified that on the server on 2026-09-29.
2. **The table.** The backend mounts the table volume read-only and reads `latest` with a small reader of its own (`edge_depth_reader.py`). The backend image is built from the `floodmap/graphhopper-flood-road` folder, so it cannot import `scripts/edge_depth`. The reader is tested on the same golden fixture as the Python and Java readers.
3. **The stale-table guard.** The table's graph hash must equal the hash of the loaded graph. GraphHopper reports its hash when a request carries the hint `td_info` (a new response hint, `td.graph_hash`, with `td.run`). A missing, damaged, or stale table gives `status: unavailable` and a reason, so the client can show "timing check unavailable". It is not an error.
4. **The rule.** The closure rule is the one of `US-050` and `sticky_reference.py`: a road is closed for an entry time when a step in `[departure, entry + margin]` has a depth at or above the vehicle's limit. The margin is 600 s and the limit comes from `flood_utils.py`. The entry time of an edge is the departure plus the route time up to that edge.
5. **Candidates.** One per forecast step, from the step that contains now to the last step. A candidate is `blocked` when any edge is closed on entry, else `unknown` when the trip ends after the last step, else `clear`. `earliest_clear` is the first `clear` candidate, or null.
6. **The answer.** `status` (`ok` or `unavailable`), `run`, `run_age_s` (now minus the run's first step), `generated_at`, `vehicle`, `limit_cm`, `margin_s`, `route` (distance and time), `candidates` (departure, status, arrival), and `earliest_clear`. The server clock and the margin are the server's. A body that carries them is not trusted.
7. **Errors.** GraphHopper's "Connection not found" for the usual route passes through, since no advice is possible without a route.

## Steps

Tests first at every step.

1. Java: `TableProvider.graphHash()` (default empty), `LatestTableSource` returns the hash it was given, and `TimeAwareRouter` adds `td.graph_hash` and `td.run` for a request with `td_info`, without changing the route.
2. Python: `edge_depth_reader.py`, on the golden fixture and on damaged copies.
3. Python: `departures.py`, pure: the entry times from the details, the closure rule, the candidates, and the answer. A random test against `scripts/routing_reference/sticky_reference.py` on the same inputs (skipped when the repo's `scripts/` is not there).
4. `server.py` serves `POST /route/departures`. Compose mounts the volume into `floodmap-backend` and sets `EDGE_TABLE_DIR`.
5. Docs: [[graphhopper-backend]], the story files, `TODOS.md`.

## Risks

- **Detail alignment.** If GraphHopper merges equal consecutive values in the `time` detail, the two lists stop lining up. The endpoint checks and refuses, and the server proof shows it on a real route.
- **A third reader of the table format.** The golden fixture keeps it in step with the Python and Java readers.
- **Run age.** Defined as now minus the first step of the table. The first step is the run's "now", so it is the age of the forecast.

## Status history

- **2026-10-05, active.** Plan written at the start of `US-053`.
- **2026-10-05, active.** Steps 1 to 4 built, tests first. Java: `td_info` gives `td.graph_hash` and `td.run` (123 module tests). Python: `edge_depth_reader.py` (21 tests, on the golden fixture, with a one-file cache), `departures.py` (30 tests, five changes make tests fail, and a 300-case comparison with `sticky_reference.py`), and `server.py`. `test_server.py` runs the endpoint against a stub GraphHopper with a real table folder: a blocked-blocked-clear answer with the earliest clear departure at step 3, an unavailable answer that names both hashes for a table of another graph, an unavailable answer with no pointer, and a 400 for a body with no points. Compose mounts `edge-depth-tables` read-only into `floodmap-backend` with `EDGE_TABLE_DIR=/tables`. Decision made while building: a candidate's arrival is counted from when the traveller leaves (the later of the step and now), while the closure is judged from the step that contains now. Left: a real route on the server (`US-055`).
