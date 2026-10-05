---
date: 2026-10-05
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-9, routing, graphhopper, backend, flag, fallback, us-052]
related: ["[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[time-aware-weighting-and-search]]", "[[edge-depth-table-java-reader]]", "[[edge-depth-table-format]]", "[[graphhopper-backend]]", "[[sprint-plan-3]]"]
---

# Plan: integrate the time-aware engine into the backend with a flag and a fallback (US-052)

## Context

Acceptance, from [[time-aware-routing-engine-stories]] Story R7. With the flag on, `_handle_route` uses the table, takes `t0` as the later of `valid_time` and the server clock rounded to the containing step, pins one run for the whole request, and returns `unknown` for a trip that ends after the last step. With the flag off the body equals today's. A missing, stale, or mismatched table falls back to today's model, and the response carries a fallback flag. Tests cover the flag off, a departure between steps, the horizon edge, run pinning, and the hash mismatch.

`US-050` built the engine and `US-043` the reader. Nothing connects them to a request yet: the table supplier is empty and no one sends `td_departure`. This story connects them. The proof on the server is `US-055`.

## Design

Two processes, so the work splits where the data is.

**GraphHopper side (Java).** It holds the graph, so it can compute the graph hash and read the table.

1. `TableProvider` is a small interface (`current()` and `problem()`). `LatestTableSource` implements it, so the router can say why there is no table.
2. `TimeAwareGraphHopper` reads `time_aware.table_dir` from the config. After `importOrLoad()` it hashes the loaded graph with `GraphHash.compute`, starts a `LatestTableSource` on that folder, and closes it on `close()`. With no folder configured the provider reports "no table folder configured".
3. `TimeAwareRouter.route()` decides once per request, because GraphHopper creates a new router for every request. A request without the hint `td_departure` is not time-aware, and its response is unchanged. A request with it is `applied` (a table, and a profile with `td_limit_cm`) or `fallback` (no table, a stale table, or a profile with no limit). One call to `current()` per request pins the run for all legs.
4. The departure is floored to the step that contains it (the latest step at or before it). Without this the step that describes the road now would fall before the departure and be ignored by the closure rule.
5. Response hints: `td.status` (`applied`, `unknown`, or `fallback`), `td.run`, `td.departure` and `td.last_step` (epoch seconds), and `td.reason` for a fallback. A route that ends after the last step is `unknown`: the departure plus the route time is later than the last step. The route is still returned, judged on the steps that exist.
6. `td_limit_cm` is a profile hint in `config.yml`: 20 for `motorbike` and 30 for `car`. `truck` and `foot` have none until `US-051`, so a flagged request for them is a fallback with that reason.

**Backend side (Python, `server.py`).**

7. The flag is the environment variable `TIME_AWARE_ROUTING` (default off). Off: the request goes as today, with no `td_` field.
8. On: `td_departure` is the later of `valid_time` and the server clock, as epoch seconds. The request goes **without** the flood `custom_model`, because the engine judges the roads over time. If the response says `fallback`, or has no `td.status` (a stock GraphHopper that ignores the hint), the backend sends the request again with today's custom_model and the response keeps `td.status: fallback`. So a fallback is today's model, as the story says, and costs one extra call only then.
9. An error response passes through unchanged. A route that is closed by the table gives GraphHopper's "Connection not found" error, which is what `US-054` reacts to.

**Compose.** The `graphhopper` service builds from `java/time-aware-routing`, mounts `edge-depth-tables` read-only at `/tables`, and starts through the image's `run-time-aware.sh`. `floodmap-backend` gets `TIME_AWARE_ROUTING` with the default `false`. The server change is a deploy, and it waits for the end of the 48-hour replay window.

## Steps

Tests first at every step.

1. Java: `TableProvider`, the decision and the hints in `TimeAwareRouter`, with `TimeAwareRouterTest`: not requested (no hints), applied, fallback for no table, stale table, and a profile with no limit, a departure between steps, the horizon edge (arrival equal to the last step is known, later is `unknown`), the pin (one `current()` call for a 3-point request), and the profile hint read from YAML.
2. Java: `TimeAwareGraphHopper` loads the table folder after import, with a test that the hash of the loaded graph equals the export's hash.
3. Python: `time_aware_route.py` (pure functions and the request flow with the GraphHopper call injected), with unit tests: flag off equals today's body, `t0` rules, the fallback resend, the stock-GraphHopper case, errors pass through.
4. `server.py` calls it. `config.yml` gets the hints. `compose.yml` gets the image, the mount, and the flag. `docker compose config` accepts it.
5. Docs: [[graphhopper-backend]], the story files, `TODOS.md`.

## Risks

- **Request body field.** GraphHopper turns unknown body fields into hints, as it does with `ch.disable`. A test with the real router checks the hint arrives as a number.
- **Hash of the live graph.** It must equal the export's hash, or every request falls back. The test on the tiny graph covers the code, and `US-055` shows it on the real graph.
- **Two calls on a fallback.** Only when the engine cannot be used. The response says so.
- **Flag on with an old image.** The hint is ignored, the response has no `td.status`, and the backend treats it as a fallback.

## Status history

- **2026-10-05, active.** Plan written at the start of `US-052`.
- **2026-10-05, active.** Steps 1 to 5 built, tests first. Java: 118 module tests, and four changes make tests fail (no floor to the step, an arrival at the horizon edge counted as unknown, two reads of the table per request, no hints). Python: `time_aware_route.py` with 27 tests, and four changes make tests fail (the departure ignores the clock, the client's `td_` fields kept, no resend on a fallback, the flag ignored). `test_server.py` against a throwaway PostGIS and a stub GraphHopper passes the two existing route checks and a new flag-on check (the engine request, then today's graded request, and the fallback flag in the response); its later point-depth step needs `gdallocationinfo`, which this session does not have. `docker compose config` accepts the compose change. One finding on the way: GraphHopper turns unknown body fields into hints (`GHRequest.putHint`), so `td_departure` arrives as a number, and `Profile.putHint` does the same for `td_limit_cm` in `config.yml`. Left: the deployed run, which is `US-055`.
