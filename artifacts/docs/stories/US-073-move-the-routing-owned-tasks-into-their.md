---
date_drafted: 2026-10-06
type: user-story
us_id: "US-073"
story_label: "C3"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P2
estimate: M
sprint: 11
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-10-routing-first-consumer]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"]
title: "Move the routing-owned tasks into their own DAG, triggered by the core's published output"
---

# US-073 Move the routing-owned tasks into their own DAG, triggered by the core's published output

As a maintainer, I want the tasks that only routing needs to run in a separate DAG, so a routing failure or
redeploy never touches the core run, and the next application can plug in the same way.
Given the core DAG, when `9b_load_depth_raster` finishes, then it emits an Airflow asset event carrying the run
id, and a DAG `routing_adapter` scheduled on that asset runs `load_road_segments`, `flood_on_roads` and
`9c_build_edge_depth_table` for that run. The core DAG no longer contains those tasks and its graph tests are
updated. A routing failure leaves the core run green. 9c still ends within 5 minutes of `3_calculate_depth`
(the limit of `US-045`), measured once on the server, and runs in a pool so it does not compete with depth for
worker slots. The asset event is the "run X published" signal in the contract of Story C1.
Fallback if the asset trigger gives trouble: a TaskGroup `routing_adapter` inside the same DAG.
Dependencies: Story C1 (the contract names the
signal), and `US-055` for the server timing, since the proof and the replay rely on today's DAG shape. Task ids
move to a new `dag_id`, so `scripts/pipeline_margins`, the proof tooling and anything keyed on
`flood_mapping_full` task ids must be checked first.
Evidence: None yet.

## Evidence and details

**Evidence:** Story C1, and `US-055` for the server timing

**Details:**

![[us-073-routing-adapter-check-output.png|120]]

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed. It also said: status "Done (45 of 45 runs triggered on the server, 9c within the limit)".
