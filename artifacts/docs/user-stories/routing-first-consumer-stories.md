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
  Priority: P1. Status: Done. Estimate: M. Sprint: 11. Dependencies: None.
  Evidence: ![[us-071-live-schema-contract-2026-10-07.png]]
  Details:
  1. Built `core_contract.py` (the parser) and `test_core_contract.py` (the offline parser tests plus the live-schema
     test), reading `artifacts/docs/concepts/core-output-contract.md`.
  2. The live test connects to `storage-postgres` and compares every contract table's columns, types, nullability
     and keys against `pg_attribute`/`pg_constraint`.
  3. On 2026-10-07, run on the server (host ADMIN) in a one-off container with the repo mounted read-only: "live
     schema matches the contract for 5 tables, ok". A deliberately wrong page was checked earlier and failed as
     expected.
  4. US-072, US-073 and US-075 read this contract's table list, so it unblocks them.

- **Story C2 (US-072): Run the routing backend on a read-only database role.**
  As the operator, I want the backend to connect with a role that can only read the contract tables, so a
  consumer cannot write into the core.
  Given the role, when the backend runs on it, then every endpoint works and an `INSERT` into any core table
  fails with a permission error.
  Priority: P1. Status: Done. Estimate: S. Sprint: 11. Dependencies: Story C1 (the table list), and
  `US-055` for the server run.
  Evidence: ![[us-072-reader-role-2026-10-07.png]]
  Details:
  1. On 2026-10-07, host ADMIN: `ROUTING_READER_PASSWORD` added to `.env`, `scripts/database/create_routing_reader_role.py` run, confirmed the role reads the 5 contract tables.
  2. `floodmap-backend` recreated as `routing_reader` (confirmed via `printenv` and a clean startup log).
  3. `test_reader_role.py` run live: every contract table's `SELECT` works, every table's `INSERT` is refused, and a table outside the contract is refused too. Print line: "ok: routing_reader reads 5 contract tables and writes nothing".
  4. A 116-check soak run against real traffic produced 0 `permission denied` lines in the backend log, and all 5 contract-table endpoints (`/flood/runs`, `/flood/timesteps`, `/flood/areas`, `/flood/points`, `/flood/forecast`) answered correctly under the reader role.

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
  Priority: P2. Status: Done (45 of 45 runs triggered on the server, 9c within the limit). Estimate: M. Sprint: 11. Dependencies: Story C1 (the contract names the
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
  Priority: P2. Status: Done. Estimate: S. Sprint: 11. Dependencies: None.
  Evidence: ![[us-074-vehicle-limit-owner-2026-10-07.png]]
  Details:
  1. `VEHICLE_PROFILES` in `flood_utils.py` is the one owner of the vehicle depth thresholds.
  2. `scripts/test_vehicle_limit_owner.py` scans the repo's source files and fails if a second file defines the
     same limits, and the existing test comparing `td_limit_cm` (GraphHopper `config.yml`) with `flood_utils`
     still passes (confirmed earlier re-running `test_time_aware_route.py`'s
     `test_the_limits_equal_the_thresholds_of_flood_utils`).
  3. Run on the server (host ADMIN) on 2026-10-07: `test_no_source_file_defines_the_limits_again ... ok`.
  4. The Airflow container's import of `flood_utils` ([[airflow-cannot-import-flood-utils]]) was checked
     unchanged on 2026-10-07.

- **Story C5 (US-075): Fail a test when the backend reads a table outside the contract.**
  As a maintainer, I want a guard so routing cannot grow a new hidden dependency on the core.
  Given the backend source, when the guard test scans its SQL for table names, then it passes only for tables
  listed in the contract, and a query on any other table fails it.
  Priority: P2. Status: Done. Estimate: S. Sprint: 11. Dependencies: Story C1.
  Evidence: ![[us-075-contract-table-guard-2026-10-07.png]]
  Details:
  1. `test_backend_reads_contract_tables.py` reads the backend's SQL with `ast` and lists every table name it
     queries.
  2. The guard passes only when every table is one of the 5 the contract (Story C1) lists, and fails when a query
     targets a table outside it.
  3. Run on the server (host ADMIN) on 2026-10-07: "backend reads only contract tables (5 listed) ... backend
     reads ['flood_depth_raster_tile', 'flood_extent_polygon', 'flood_extent_step', 'flood_road_values'] ... ok".

## Status history

- **2026-10-06, draft.** Written at the user's request after the discussion of making the system ready for other
  applications, with routing as the first customer. Placed in Sprint 11 of [[sprint-plan-3]].
- **2026-10-06, draft.** Story C3 changed from a TaskGroup (S) to a separate DAG triggered by an asset event (M), at the user's request. The earlier reason for one DAG, the 9c timing limit, does not need it: 9c depends only on `9b_load_depth_raster`, so an asset trigger adds seconds. The TaskGroup stays as the fallback.
- **2026-10-09, draft.** Story C3 (`US-073`) is `Done`. 45 of 45 simulating runs of the replay triggered `routing_adapter`, and 9c ended within 3.91 minutes of `3_calculate_depth`. A routing failure leaving the core run green was not observed. The user accepted the DAG structure and its tests as proof.
