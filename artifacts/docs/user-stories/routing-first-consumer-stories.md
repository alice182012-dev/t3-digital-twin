---
date_drafted: 2026-10-06
type: user-story
us_ids: ["US-071", "US-072", "US-073", "US-074", "US-075"]
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: []
related: ["[[sprint-plan-3]]", "[[routing-first-consumer-contract]]", "[[architecture-block-diagram]]", "[[graphhopper-backend]]", "[[edge-depth-table-format]]", "[[flood-on-roads]]"]
tags: [user-story, epic, architecture, contract, routing, sprint-11]
---

# Epic: routing as the first consumer of the core output

The 3Di simulation pipeline stays the core and does not change. Routing is its first customer. This epic makes
the boundary between them explicit and enforced, so a later application (finance analysis, decision analysis)
reads the same contract. No application besides routing is built. The reasoning and the inventory of what routing
reads today are in [[routing-first-consumer-contract]]. The order of work is in [[sprint-plan-3]], Sprint 11.

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`sprint-plan-3.md`. Server evidence waits for `US-055` (no builds on the server until the replay ends and the
engine proof runs).

- **Story C1 (US-071): Write the output contract and a test that checks it against the live schema.**
  As an engineer of any consuming application, I want one page that states what the core publishes, so I can
  read it without reading the pipeline's SQL.
  Given the contract page, when the contract test runs against the database, then it fails if a column, type or
  key of a contract table differs from the page. The page covers `flood_depth_raster_tile`,
  `flood_extent_polygon`, `flood_extent_step`, `flood_road_values`, `graph_edge`, the edge depth `.bin` (by link to
  [[edge-depth-table-format]]) and the tiles in MinIO: schema, units, CRS, the time convention (UTC in the
  database, +07 in filenames), keys, retention (8 runs, 48 h for `netcdf_values`), and `flood_extent_step.published_at`
  as the readiness flag.
  Priority: P1. Status: Reviewed (built on `modular`, live check passed on the server's backend container on 2026-10-07; screenshot pending).. Estimate: M. Sprint: 11. Dependencies: None.
  Evidence: None yet.

- **Story C2 (US-072): Run the routing backend on a read-only database role.**
  As the operator, I want the backend to connect with a role that can only read the contract tables, so a
  consumer cannot write into the core.
  Given the role, when the backend runs on it, then every endpoint works and an `INSERT` into any core table
  fails with a permission error.
  Priority: P1. Status: Reviewed (built on `modular`, offline tests pass; role script and live test not yet run, they wait for the end of the replay).. Estimate: S. Sprint: 11. Dependencies: Story C1 (the table list), and
  `US-055` for the server run.
  Evidence: None yet.

- **Story C3 (US-073): Move the routing-owned tasks into their own DAG, triggered by the core's published output.**
  As a maintainer, I want the tasks that only routing needs to run in a separate DAG, so a routing failure or
  redeploy never touches the core run, and the next application can plug in the same way.
  Given the core DAG, when `9b_load_depth_raster` finishes, then it emits an Airflow asset event carrying the run
  id, and a DAG `routing_adapter` scheduled on that asset runs `load_road_segments`, `flood_on_roads` and
  `9c_build_edge_depth_table` for that run. The core DAG no longer contains those tasks and its graph tests are
  updated. A routing failure leaves the core run green. 9c still ends within 5 minutes of `3_calculate_depth`
  (the limit of `US-045`), measured once on the server, and runs in a pool so it does not compete with depth for
  worker slots. The asset event is the "run X published" signal in the contract of Story C1.
  Fallback if the asset trigger gives trouble: a TaskGroup `routing_adapter` inside the same DAG.
  Priority: P2. Status: Reviewed (built on `modular`, serialized by Airflow 3.1.7 on the server; trigger and the 9c limit not yet observed).. Estimate: M. Sprint: 11. Dependencies: Story C1 (the contract names the
  signal), and `US-055` for the server timing, since the proof and the replay rely on today's DAG shape. Task ids
  move to a new `dag_id`, so `scripts/pipeline_margins`, the proof tooling and anything keyed on
  `flood_mapping_full` task ids must be checked first.
  Evidence: None yet.

- **Story C4 (US-074): Give the vehicle thresholds one owner.**
  As a maintainer, I want `flood_utils.py` owned by routing, with the core importing it by an explicit path, so the
  dependency points one way.
  Given the thresholds, when the backend, `scripts/flood_metrics/extract_run.py` and the GraphHopper
  `td_limit_cm` all read them, then there is one source, the existing test that compares `td_limit_cm` with
  `flood_utils` still passes, and the extractor's import works inside the Airflow container (the problem of
  [[airflow-cannot-import-flood-utils]] must not return).
  Priority: P2. Status: Reviewed (built on `modular`, tests pass; the Airflow container import is unchanged and was checked on 2026-10-07).. Estimate: S. Sprint: 11. Dependencies: None.
  Evidence: None yet.

- **Story C5 (US-075): Fail a test when the backend reads a table outside the contract.**
  As a maintainer, I want a guard so routing cannot grow a new hidden dependency on the core.
  Given the backend source, when the guard test scans its SQL for table names, then it passes only for tables
  listed in the contract, and a query on any other table fails it.
  Priority: P2. Status: Reviewed (built on `modular`, tests pass and a fault check fails as it should).. Estimate: S. Sprint: 11. Dependencies: Story C1.
  Evidence: None yet.

## Status history

- **2026-10-06, draft.** Written at the user's request after the discussion of making the system ready for other
  applications, with routing as the first customer. Placed in Sprint 11 of [[sprint-plan-3]].
- **2026-10-06, draft.** Story C3 changed from a TaskGroup (S) to a separate DAG triggered by an asset event (M), at the user's request. The earlier reason for one DAG, the 9c timing limit, does not need it: 9c depends only on `9b_load_depth_raster`, so an asset trigger adds seconds. The TaskGroup stays as the fallback.
