---
date_drafted: 2026-10-06
type: user-story
us_ids: ["US-071", "US-072", "US-073", "US-074", "US-075"]
status: draft
subsystem: airflow-pipeline, floodmap-backend
source_ideas: []
related: ["[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[routing-first-consumer-contract]]", "[[architecture-block-diagram]]", "[[graphhopper-backend]]", "[[edge-depth-table-format]]", "[[flood-on-roads]]"]
tags: [user-story, epic, architecture, contract, routing, sprint-11]
---

# Epic: routing as the first consumer of the core output

The 3Di simulation pipeline stays the core and does not change. Routing is its first customer. This epic makes
the boundary between them explicit and enforced, so a later application (finance analysis, decision analysis)
reads the same contract. No application besides routing is built. The reasoning and the inventory of what routing
reads today are in [[routing-first-consumer-contract]]. The order of work is in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], Sprint 11.

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`sprint-plan-3.md`. Server evidence waits for `US-055` (no builds on the server until the replay ends and the
engine proof runs).

- [[US-071-write-the-output-contract-and-a-test|US-071]] Write the output contract and a test that checks it against the live schema. Story C1.
- [[US-072-run-the-routing-backend-on-a-read|US-072]] Run the routing backend on a read-only database role. Story C2.
- [[US-073-move-the-routing-owned-tasks-into-their|US-073]] Move the routing-owned tasks into their own DAG, triggered by the core's published output. Story C3.
- [[US-074-give-the-vehicle-thresholds-one-owner|US-074]] Give the vehicle thresholds one owner. Story C4.
- [[US-075-fail-a-test-when-the-backend-reads|US-075]] Fail a test when the backend reads a table outside the contract. Story C5.

## Status history

- **2026-10-06, draft.** Written at the user's request after the discussion of making the system ready for other
  applications, with routing as the first customer. Placed in Sprint 11 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]].
- **2026-10-06, draft.** Story C3 changed from a TaskGroup (S) to a separate DAG triggered by an asset event (M), at the user's request. The earlier reason for one DAG, the 9c timing limit, does not need it: 9c depends only on `9b_load_depth_raster`, so an asset trigger adds seconds. The TaskGroup stays as the fallback.
- **2026-10-09, draft.** Story C3 (`US-073`) is `Done`. 45 of 45 simulating runs of the replay triggered `routing_adapter`, and 9c ended within 3.91 minutes of `3_calculate_depth`. A routing failure leaving the core run green was not observed. The user accepted the DAG structure and its tests as proof.
