---
date_drafted: 2026-10-12
type: user-story
us_id: "US-120"
title: "Read the rain gate and the soak checks from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Not started
kind: story
priority: P2
estimate: S
sprint: 
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-120 Read the rain gate and the soak checks from the edge table

As the owner of the pipeline, I want the rain gate and the soak checks to read the edge table, so no job reads `flood_road_values` any more except the ones still to be moved.

`standing_flood.py` reads the maximum depth of the newest runs from `flood_road_file` and `flood_road_values`, and `soak_checks.py` picks roads whose depth lies between two vehicle limits.
The story moves both to the table and the registry of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]].

Given the newest 5 runs with a dry run among them, when the gate reads them, then the dry run counts as dry, and the result equals today's result on the same runs.
Given the soak `roads` check, then it picks edges between the two limits from the new table, and each pick routes on the server.

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.

## Evidence and details

Fill this when the story reaches `Done`.
