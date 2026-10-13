---
date_drafted: 2026-10-12
type: user-story
us_id: "US-130"
title: "Serve the forecast mode and read the pinned step"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
kind: story
priority: P2
estimate: M
sprint: 14
subsystem: floodmap-backend, routing
source_ideas: []
related: ["[[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]", "[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[test-dataset]]"]
tags: [user-story]
---

# US-130 Serve the forecast mode and read the pinned step

As a visitor, I want the depth popup and the route to use the pinned demo flood when the map is in `DEMO` mode, so the demo is the same flood in every part of the app.

Part three of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]].
The backend gets an endpoint that returns `LIVE`, `PENDING`, or `DEMO` from the status row of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]].
In `DEMO` mode, `GET /flood/points`, `GET /flood/areas`, and `POST /route` read the pinned step of [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]] and not the newest run.

Open question for the first step of the story: how the router reads a pinned step after the newest edge depth table has moved on.
The story answers it with the edge depth table of the pinned run (`<run_ts>.bin`) and the rows of `edge_depth`, and records the answer in a decision if it changes a rule.

Given the status row `DEMO`, when the endpoint is read, then it answers `DEMO`, and with `LIVE` or `PENDING` it answers those.
Given mode `DEMO`, when a point inside the flooded area is read, then the depth is the depth of the pinned step.
Given mode `DEMO`, when a route is requested across the pinned flood, then the route is judged on the pinned flood.
Given mode `LIVE`, then the three calls read the newest run as before.

Dependencies: [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] and [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]] are in the same sprint.

## Acceptance check

On the server, with a test point and a test pair inside the model border.
Take a screenshot of the endpoint answer and of a depth read and a route in each mode.

1. Given each of the three modes in the status table, then the endpoint answers it.
2. Given `DEMO`, then the point read and the route use the pinned step, and the answers differ from `LIVE`.

## Status history

- **2026-10-12, Ready.** Split from [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]] at the product owner's request. It is picked for [[SPR-014-finish-the-remaining-backend|SPR-014]], and it has no code yet.
- **2026-10-12, Reviewed.** Built and tested, not deployed. `GET /flood/mode` answers `LIVE`, `PENDING`, or `DEMO` from the newest `forecast_mode` row, with the pinned run and step in `DEMO`. A database with no decision answers `LIVE`. In `DEMO` with a pinned step, `GET /flood/points`, `GET /flood/areas`, and `POST /route` replace the `run` and `valid_time` of the request with the pinned ones. `POST /route` skips the time-aware engine in `DEMO` ([[decision-log|D-043]]). `POST /flood/forecast` and `POST /flood/profile` do not change with the mode. `test_server.py` passes against a throwaway PostGIS. It covers `LIVE` with no decision, `DEMO` reading the pinned older run for a point, the areas, and the route, `DEMO` with no pin, and `PENDING`. The unit tests of `flood_mode.py`, the contract reads guard, and the contract parse test pass. Still open: the grants of `routing_reader` on `forecast_mode` and `demo_pin` (rerun `create_routing_reader_role.py`), the pinned step's raster tiles ([[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]]), the server screenshots of each mode, and the point read and route in `DEMO`.
- **2026-10-13, Reviewed.** The owner rebuilt `floodmap-backend`, and it was checked on the server (screenshot `US-130-server-mode-and-point-2026-10-13.png`). `GET /flood/mode` answers `LIVE`, `PENDING`, and `DEMO` when a temporary row of slot `2030-01-01` sets each mode, and the row was deleted afterwards. In `DEMO` it returns the pinned run and step. At 21.01320, 105.76418 the depth read is 0.80 m in `DEMO` (19:00 UTC) and 0.10 m in `LIVE` and `PENDING` at the first step (17:15 UTC). Of 10 route pairs between wet edges, 1 routed in `DEMO` (2,837 m) and none routed in `LIVE`, where the time-aware engine is on. Why the `LIVE` routes find no connection was not investigated. Still open: screenshots of the `LIVE` and `PENDING` answers and of the route comparison, and the owner's acceptance.
- **2026-10-13, Reviewed.** The `LIVE` and `DEMO` route result is explained by [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]] and [[decision-log|D-044]]. With dry endpoints 150 to 400 m from the flood, `LIVE` routed 12 of 12 pairs and `DEMO` routed 10 of 12, with equal distances on 3. Still open: the screenshots of the `LIVE` and `PENDING` answers, and the owner's acceptance.
- **2026-10-13, Done.** The product owner accepted it on the written results of details items 1 to 5, with no server screenshot. The screenshot that the owner sent showed a table of the results and not the terminal, so it is not filed.

## Evidence and details

**Evidence:** the output of `marie-curie/us130/check_modes.sh`, run by the development team on 2026-10-13 at 04:22 UTC and written in details items 2 to 4. The script is scratch and git does not track it. There is no server screenshot.

**Details:**

1. The owner rebuilt `floodmap-backend` on the server on 2026-10-13, and the checks ran against it.
2. `GET /flood/mode` answers `PENDING`, `LIVE`, and `DEMO` when a temporary `forecast_mode` row (slot `2030-01-01`, deleted after each run) sets each mode.
   In `PENDING` and `LIVE` the answer has `"demo": null`.
   In `DEMO` it names the pinned run `20261011T001500` and the step 2026-10-10 19:00 UTC.
3. The depth at 21.01320, 105.76418 is 0.10 m in `PENDING` and `LIVE` (the request names run `20261011T001500` and 17:15 UTC, its first step) and 0.80 m in `DEMO` (the pinned step).
4. The motorbike route from 105.73674, 21.00219 to 105.72957, 20.99898 is 1,886 m in `PENDING` and `LIVE`, and 4,249 m in `DEMO`.
   The answers of `DEMO` differ from `LIVE`, which meets the second acceptance check.
5. `PENDING` and `LIVE` read the same data on the backend.
   The dry map with a warning in `PENDING` is a behaviour of the frontend ([[US-131-show-the-demo-flood-banner-and-the-pinned-frame|US-131]]).
6. In `DEMO` the route skips the time-aware engine ([[decision-log|D-043]]), and `LIVE` judges the newest table at its last step.
   A comparison of the modes uses points that are dry and away from the flood ([[decision-log|D-044]], [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]]).
7. Earlier on the same day, 10 pairs between wet edges routed in `DEMO` once and in `LIVE` never.
   That result was a flaw of the pairs, which started on closed edges, as [[US-135-find-why-live-routes-find-no-connection-between-wet-edges|US-135]] shows.

