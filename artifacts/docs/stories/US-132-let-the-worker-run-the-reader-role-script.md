---
date_drafted: 2026-10-13
type: user-story
us_id: "US-132"
title: "Let the worker run the reader role script"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P3
estimate: S
sprint: 14
subsystem: database, airflow-pipeline
source_ideas: []
related: ["[[core-output-contract]]", "[[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]]"]
tags: [user-story]
---

# US-132 Let the worker run the reader role script

As a developer, I want `create_routing_reader_role.py` to run in the Airflow worker, so a deploy needs no manual `GRANT` statements or temporary file copies.

The script imports `core_contract.py` from `floodmap/graphhopper-flood-road/backend` and reads the contract page `artifacts/docs/concepts/core-output-contract.md`.
The worker mounts neither, so on 2026-10-12 the grants were typed by hand ([[US-119-read-the-map-overlay-and-route-fallback-from-the-edge-table|US-119]]), and on 2026-10-13 both files were copied into the worker's `/tmp` for one run.
The story moves the parser and the table lists to a place that the worker mounts, or mounts them, and keeps one copy of each.

Given the worker after a pull, when `python create_routing_reader_role.py routing_reader` runs there, then the role has `SELECT` on each table the contract page lists for it.
Given the script run twice, then the grants are the same.

Dependencies: None.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: it has no open dependency, it fits one sprint, and its acceptance is a check on the server.
- **2026-10-13, Reviewed.** Built and checked on the server. The owner has not accepted it. `compose.yml` mounts `core_contract.py` (standard library only) and `core-output-contract.md` read-only in the shared `x-airflow-common` block, at the paths that `create_routing_reader_role.py` computes from `/opt/airflow`. The test `test/test_worker_reader_role_mounts.py` checks both mounts. After the worker was recreated, `python create_routing_reader_role.py routing_reader` ran in the worker twice with no copied file, and both runs printed the same list of 11 tables.

## Evidence and details

**Evidence:** the output of the script in the worker, run twice (details item 3). No screenshot yet.

**Details:**

1. The two mounts sit next to the existing `scripts` mount of the shared `x-airflow-common` block, so every Airflow service gets them.
2. `test/test_worker_reader_role_mounts.py` (2 tests) reads `compose.yml` as text, because PyYAML is missing, and checks both mounts and the container paths. It passes with the existing compose test (7 tests).
3. On the server on 2026-10-13, `docker compose up -d --no-deps airflow-scheduler airflow-worker` recreated the containers, and the script ran in the worker twice with the same result: "Role routing_reader can read demo_pin, edge_depth, edge_depth_run, flood_depth_raster_tile, flood_extent_polygon, flood_extent_step, flood_road_file, flood_road_values, flood_run_output, forecast_mode, graph_edge."
4. The second test of the mounts asserts source strings of the script (`parents[2]` and the two path expressions), so it does not catch a change to how the script computes its folder in another form.

