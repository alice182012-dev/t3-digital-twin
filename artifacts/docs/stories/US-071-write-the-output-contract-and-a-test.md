---
date_drafted: 2026-10-06
type: user-story
us_id: "US-071"
story_label: "C1"
epic: "[[EP-10-routing-first-consumer]]"
status: Done
priority: P1
estimate: M
sprint: 11
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-10-routing-first-consumer]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Write the output contract and a test that checks it against the live schema"
---

# US-071 Write the output contract and a test that checks it against the live schema

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
