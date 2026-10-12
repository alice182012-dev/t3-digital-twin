---
date_drafted: 2026-10-12
type: user-story
us_id: "US-117"
title: "Export a stable key with each graph edge"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: In progress
kind: story
priority: P1
estimate: M
sprint: 
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-117 Export a stable key with each graph edge

As the owner of the flood data, I want each graph edge to carry a key that survives a graph re-import, so the depth history and the metrics keep their meaning after the graph changes.

`ExportEdges` (`java/time-aware-routing`) writes `edge_id`, `wkt`, `base_node`, and `adj_node`, and GraphHopper renumbers all four on every import.
The story adds the OSM way id and the position of the edge along its way to `edges.csv`, and loads them into `graph_edge` as one `edge_key`.
It also decides how a way split in a different place by a new import maps its old keys to new ones, and records the rule.

Given a graph imported twice from the same OSM file, when `ExportEdges` runs on both, then every `edge_key` of the first export appears in the second.
Given a graph re-imported from a changed OSM file, when the keys are compared, then the story lists which keys appear, vanish, or change, and the rule for history is written in [[graph-reimport-procedure]].
Given `graph_edge` after the load, then no two rows share an `edge_key`.

Dependencies: None.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, In progress.** Started on the owner's request, outside the sprint plan, so it has no `sprint`. The first read found that the export cannot carry the way id yet. `graph.encoded_values` in `floodmap/graphhopper-flood-road/graphhopper/config.yml` does not list `osm_way_id`, and the pinned GraphHopper build rejected it as a path detail on 2026-09-29 (archived PRD-003 and PRD-004, not rechecked). Enabling it needs a graph re-import ([[graph-reimport-procedure]]): routing is down for minutes, every `edge_id` is renumbered, and task `9c` rebuilds the edge depth table. Whether the pinned build has the `OSMWayID` encoded value is unverified. The owner decides between that re-import and a key built from the edge geometry.
- **2026-10-12, In progress.** Throwaway test of the re-import route, on the server. A separate container of the live image `graphhopper-time-aware:local` imported `hanoi-model-area.osm.pbf` into a scratch volume with `osm_way_id` added to `graph.encoded_values`, on port 18989, and was healthy after 16 s. `/info` listed `osm_way_id`. A truck route from 21.0250, 105.7550 to 21.0255, 105.7620 with `details: [osm_way_id, edge_id]` returned both, with 6 way segments over 21 edge segments (for example way 601455783 on points 0 to 1 and way 685040575 on points 1 to 28). The 6 way ids of the route all exist in `road_segment.way_id`. The largest `road_segment` way id is 1,475,686,339, which is 69 percent of 2^31, so check the bit width of the encoded value before the ids pass 2,147,483,647. The container, the volume, and the config copy are removed, and the live `graphhopper` was not touched. So the pinned build can carry the way id, and the 2026-09-29 rejection was only the missing `osm_way_id` entry in the config. Not yet tested: reading the value in `ExportEdges` (the Java build runs in Docker, not on the Mac), the position of an edge along its way, and the re-import window.

## Evidence and details

Fill this when the story reaches `Done`.
