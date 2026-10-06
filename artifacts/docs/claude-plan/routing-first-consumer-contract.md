---
date: 2026-10-06
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, architecture, contract, routing, sprint-11]
related: ["[[routing-first-consumer-stories]]", "[[sprint-plan-3]]", "[[architecture-block-diagram]]", "[[graphhopper-backend]]", "[[edge-depth-table-format]]"]
---

# Plan: routing as the first consumer of the core output

## Context

The user wants the system ready for other applications (finance analysis, multi-stakeholder decision analysis) if
the opportunity arises, without building them. The 3Di pipeline is the core and does not change. Routing is the
first customer. The scratch note with the cost and benefit of the options is `marie-curie/modular-core-platform-idea.md`
(untracked). Stories: [[routing-first-consumer-stories]], Sprint 11 of [[sprint-plan-3]].

## What routing reads from the core today (read on 2026-10-06)

1. `flood_depth_raster_tile` (6 queries), `flood_extent_polygon` (2), `flood_extent_step` (2), `flood_road_values` (3), in
   `floodmap/graphhopper-flood-road/backend/`.
2. The edge depth `.bin` in the `edge-depth-tables` volume, tied to the loaded graph by `graph_hash`
   (`edge_depth_reader.py:107`).
3. Vehicle thresholds in `floodmap/graphhopper-flood-road/scripts/flood_utils.py`, copied in by the backend's Dockerfile and
   duplicated as `td_limit_cm` in GraphHopper's `config.yml` (a test keeps the two equal).
4. The backend connects as the pipeline's own user (`db.py:9-14`, default `minio_custom`), so it can write.
5. Routing-owned tasks and tables sit in the core DAG: `load_road_segments`, `flood_on_roads`, `9c_build_edge_depth_table`;
   `road_segment`, `graph_edge`, `graph_edge_export`.

## Decisions

1. Keep the routing tasks in the same DAG. A separate DAG risks the 9c timing limit of `US-045`.
2. No read API and no per-run export now. Both wait for a second consumer that shows which shape it wants.
3. The core's simulation and pipeline code do not change.

## Steps

1. `US-071` the contract page and the contract test. 2. `US-072` the read-only role. 3. `US-073` the TaskGroup.
4. `US-074` the thresholds' owner. 5. `US-075` the guard test. Order: US-071 first, US-072 and US-075 after it,
US-073 and US-074 any time.

## Risks

- The TaskGroup prefix changes task ids. Logs, `scripts/pipeline_margins` and the proof tooling may name them.
- The read-only role needs a server change. It waits for `US-055` and the end of the replay.
- Sprint 11 also holds `US-033` (M), so the sprint is fuller than the others (see [[sprint-plan-3]] Status history).

## Status history

- **2026-10-06, active.** Plan written with the stories. Nothing built.
