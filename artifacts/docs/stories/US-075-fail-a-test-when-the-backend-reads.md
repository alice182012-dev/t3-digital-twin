---
date_drafted: 2026-10-06
type: user-story
us_id: "US-075"
story_label: "C5"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P2
estimate: S
sprint: 11
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-10-routing-first-consumer]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Fail a test when the backend reads a table outside the contract"
---

# US-075 Fail a test when the backend reads a table outside the contract

As a maintainer, I want a guard so routing cannot grow a new hidden dependency on the core.
Given the backend source, when the guard test scans its SQL for table names, then it passes only for tables
listed in the contract, and a query on any other table fails it.
Dependencies: Story C1.
Evidence: ![[us-075-contract-table-guard-2026-10-07.png]]
Details:
1. `test_backend_reads_contract_tables.py` reads the backend's SQL with `ast` and lists every table name it
   queries.
2. The guard passes only when every table is one of the 5 the contract (Story C1) lists, and fails when a query
   targets a table outside it.
3. Run on the server (host ADMIN) on 2026-10-07: "backend reads only contract tables (5 listed) ... backend
   reads ['flood_depth_raster_tile', 'flood_extent_polygon', 'flood_extent_step', 'flood_road_values'] ... ok".
