---
date_drafted: 2026-10-12
type: user-story
us_id: "US-116"
title: "Let a run with no wet road piece win the winner query"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Not started
kind: bug
priority: P1
estimate: S
sprint: 
subsystem: routing, backend
source_ideas: []
related: ["[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]", "[[flood-on-roads]]", "[[decision-log|D-036]]"]
tags: [user-story]
---

# US-116 Let a run with no wet road piece win the winner query

As a driver, I want the map and the route fallback to show no water when the newest run has none, so I am not routed around roads that have dried.

A run in which no road piece is wet writes no rows to `flood_road_values`.
The winner query in `floodmap/graphhopper-flood-road/backend/flood_areas.py` picks the newest run that has rows at a forecast time, so an older run that still has water wins.

Given a newest run with no wet piece and an older run that is wet at the same forecast time, when `/flood/areas` is read for that time, then the response has no features.
Given the same state, when `/route` falls back to the legacy custom model, then it has no flood areas.
Given a newest run that is wet at some time, then the response does not change.

The method is decided in [[decision-log|D-038]].
The run registry `flood_road_file` gets a column for the run's forecast times, written when `flood_on_roads` registers the run, and the winner picks the newest registry run that covers the forecast time.
The fix is needed in both plans: the edge table of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] keeps the same registry, so the work is not thrown away when `flood_road_values` is deleted.
The server had no run with `feature_count` 0 among 75 runs on 2026-10-12, so a test needs a constructed dry run.

Dependencies: the owner accepts [[decision-log|D-038]].

## Status history

- **2026-10-12, draft.** Found at Sprint 13 planning. It stays in the backlog until the spike decides the method, so the fix is not thrown away.

## Evidence and details

Fill this when the story reaches `Done`.
