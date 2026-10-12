---
date_drafted: 2026-10-12
type: user-story
us_id: "US-130"
title: "Serve the forecast mode and read the pinned step"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
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

## Evidence and details

Fill this when the story reaches `Done`.
