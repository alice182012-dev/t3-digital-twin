---
date: 2026-10-06
type: concept
status: active
tags: [concept, architecture, contract, routing, sprint-11]
related: ["[[EP-10-routing-first-consumer|routing-first-consumer-stories]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[architecture-block-diagram]]", "[[graphhopper-backend]]", "[[edge-depth-table-format]]"]
last_updated: 2026-10-06
---

# Plan: routing as the first consumer of the core output

## Context

The user wants the system ready for other applications (finance analysis, multi-stakeholder decision analysis) if
the opportunity arises, without building them. The 3Di pipeline is the core and does not change. Routing is the
first customer. The scratch note with the cost and benefit of the options is `marie-curie/modular-core-platform-idea.md`
(untracked). Stories: [[EP-10-routing-first-consumer|routing-first-consumer-stories]], Sprint 11 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].

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

1. Move the routing tasks into a separate DAG `routing_adapter`, scheduled on an Airflow asset that `9b_load_depth_raster` emits (changed 2026-10-06 at the user's request). The first draft kept them in one DAG for the 9c timing limit of `US-045`, but 9c depends only on `9b`, so an asset trigger adds seconds. The asset event is the contract's "run published" signal. A TaskGroup in the same DAG is the fallback.
2. No read API and no per-run export now. Both wait for a second consumer that shows which shape it wants.
3. The core's simulation and pipeline code do not change.

## Steps

1. `US-071` the contract page and the contract test. 2. `US-072` the read-only role. 3. `US-073` the separate DAG.
4. `US-074` the thresholds' owner. 5. `US-075` the guard test. Order: US-071 first, then US-072, US-073 and US-075.
US-074 any time.

## Risks

- Moving tasks to a new `dag_id` changes where their logs and task ids live. `scripts/pipeline_margins` and the `US-055` proof tooling may name them. Do it after `US-055`.
- The 9c limit (end within 5 minutes of `3_calculate_depth`) needs one measurement on the server with the asset trigger. A pool keeps routing tasks from taking depth's worker slots.
- The routing DAG needs the run id from the asset event, or must query the newest published run.
- The read-only role needs a server change. It waits for `US-055` and the end of the replay.
- Sprint 11 held `US-033` (M) when this plan was written. It moved to Sprint 12 on 2026-10-07 (see [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] Status history).

## Status history

- **2026-10-06, active.** Plan written with the stories. Nothing built.
- **2026-10-06, active.** Decision 1 changed from one DAG to a separate DAG (`US-073`, now M).
- **2026-10-07, active.** Steps 1 to 5 are built on the branch `modular` (`US-071` to `US-075`, all `Reviewed`). Item 5 under "What routing reads from the core today" describes 2026-10-06: since `77169c3` the three routing tasks `load_road_segments`, `flood_on_roads`, and `9c_build_edge_depth_table` are in the DAG `routing_adapter`, not in the core DAG. The concept page [[3di-simulation-orchestration]] has the current shape. Not deployed.

