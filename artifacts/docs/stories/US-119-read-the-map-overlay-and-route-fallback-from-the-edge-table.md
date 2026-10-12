---
date_drafted: 2026-10-12
type: user-story
us_id: "US-119"
title: "Read the map overlay and the route fallback from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Not started
kind: story
priority: P1
estimate: S
sprint: 
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-119 Read the map overlay and the route fallback from the edge table

As a driver, I want the map overlay and the route fallback to read the same water as the routing engine, so the map never shows a road that the router treats differently.

`flood_areas.py` (`/flood/areas`) and the legacy custom model of `/route` read `flood_road_values` through `_WINNER_SEG_SQL`.
The story moves both to the edge table of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]]. The winner is the newest registry run that covers the forecast time, and the geometry comes from `graph_edge`.

Given a newest run with no wet edge and an older wet run at the same time, when `/flood/areas` is read, then the response has no features.
Given a newest run that is wet, then the response has the same wet roads as the engine's table for that run, and the depth bands match to the centimetre.
Given the same request before and after the move on one replay run, then the story records the difference in the overlay area, which comes from the edge grain.

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.

## Evidence and details

Fill this when the story reaches `Done`.
