---
date_drafted: 2026-10-12
type: user-story
us_id: "US-122"
title: "Point depth_history at the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-122 Point depth_history at the edge table

As an analyst, I want `depth_history` to be fed from the edge table, so the history has the same keys and the same water as the engine.

[[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] builds `depth_history` from `flood_road_values` and keys it by `segment_id`.
This story changes the loader `flood_history` to read the edge table and to write `edge_key`, and it re-keys the rows already loaded by [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] and [[US-113-backfill-per-segment-depth-history|US-113]] with the rule of [[US-117-export-a-stable-key-with-each-graph-edge|US-117]].

Given a replay run, when `flood_history` finishes, then `depth_history` has one row per wet edge and step, keyed by `edge_key`.
Given rows loaded before the move, then each has an `edge_key`, or the story lists the rows that could not be mapped and why.
Given the same run loaded twice, then the row count does not change.

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]], [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], and [[US-113-backfill-per-segment-depth-history|US-113]] are `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependencies are `Done` or in the same sprint, and its acceptance check is written.

## Evidence and details

Fill this when the story reaches `Done`.
