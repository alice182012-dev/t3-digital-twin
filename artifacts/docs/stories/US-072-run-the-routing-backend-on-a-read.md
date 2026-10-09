---
date_drafted: 2026-10-06
type: user-story
us_id: "US-072"
story_label: "C2"
epic: "[[EP-10-routing-first-consumer]]"
status: Done
priority: P1
estimate: S
sprint: 11
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-10-routing-first-consumer]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Run the routing backend on a read-only database role"
---

# US-072 Run the routing backend on a read-only database role

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
