---
date_drafted: 2026-09-29
type: user-story
us_id: "US-045"
story_label: "E7"
epic: "[[EP-08-edge-depth-table]]"
status: Done
priority: P0
estimate: M
sprint: 8
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
---

# US-045 Prove the table on the server

As the team, I want measured build time, size, and spot checks on the server, so the estimates become
numbers.
Given a real run on the server, when the task runs, then the report gives the edge count, the file size, and
the build time for the run, and 20 edges match `ST_Value`. The story records the numbers in
[[PRD-003-edge-depth-table|edge-depth-table]] and replaces the guessed size. If the build time exceeds the limit above, the
story records a blocker.
Priority: P0. Status: Done. Estimate: M. Sprint: 8. Dependencies: Stories E3, E4. Gate cleared: the user
set the build-time limit on 2026-10-02. The table task runs beside the tile task, never delays it, and ends within 5 minutes of the end of `3_calculate_depth`.
