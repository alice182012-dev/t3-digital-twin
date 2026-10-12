---
date_drafted: 2026-10-12
type: user-story
us_id: "US-117"
title: "Export a stable key with each graph edge"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
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
- **2026-10-12, In progress.** The export side is written and tested, not deployed. `ExportEdges` writes `edge_key` (`<osm_way_id>:<position>`) as a fifth column and `format_version` 3, and fails with the fix named when the graph has no `osm_way_id`. `graph_edges.py` reads format 3 and ignores the column. The `java-module` workflow ran on a throwaway branch (since deleted): `ExportEdgesTest` 19 tests and the whole module 144 tests passed, and the Python tests of the reader pass. The GitHub Actions run 38223799828 holds the log. Still open: load `edge_key` into `graph_edge` with a unique index, the re-import window, and the rule for keys when the OSM file changes ([[graph-reimport-procedure]]). `osm_way_id` is a 31-bit int, and the largest way id in `road_segment` is 69 percent of that limit.
- **2026-10-12, In progress.** The load side is written and tested, not deployed. `create_graph_edge_table.py` adds `graph_edge.edge_key` (`ADD COLUMN IF NOT EXISTS`, so `0b_ensure_schema` migrates the live table) with a unique index. `graph_edges.py` reads the key of a format 3 export (a `GraphEdge` row with `edge_key`, `None` before format 3), refuses a missing column, a malformed key, or a repeated key before the database is touched, and `load_graph_edges` stores it. 57 tests (`test_graph_edges`, `test_build_edge_depth`, `test_check_tables`) passed with none skipped, run in the worker against the real PostGIS in their own schemas, which they dropped. [[core-output-contract]] lists the column. Still open: the re-import window, the rule for keys when the OSM file changes ([[graph-reimport-procedure]]), the live check, and the owner's acceptance.
- **2026-10-12, In progress.** `modular` was pushed and pulled on the server (`--ff-only` from the `alice` remote). Only the scripts are live. The `ExportEdges` change needs an image rebuild, and the live graph still has no `osm_way_id`, so the live export stays format 2 and `graph_edge.edge_key` stays NULL. Pulled with no import errors, and `check_tables.py` reports `FRESH`. If a re-import runs before `create_graph_edge_table.py` has added the column, the load of the new export fails, so run that script first (see the order trap in the re-import procedure).
- **2026-10-12, In progress.** The code that fills the key when the graph hash stays the same was added before the re-import (`load_graph_edges` reloads while an export has keys and a row has none), and `config.yml` got `osm_way_id`.
- **2026-10-12, Reviewed.** Re-imported on the server with the owner's go (details items 1 to 6). It waits for the server screenshot and the owner's acceptance.
- **2026-10-12, Done.** The product owner accepted it. The terminal screenshot was not saved before the acceptance, so the evidence is the script and its captured output (`us-117-server-check-output.txt`, 2026-10-12 15:57 +07). Save `us-117-server-check-output.png` from a run of the script when convenient.

## Evidence and details

**Evidence:** the server check of 2026-10-12, read only, from `artifacts/docs/stories/evidence/us-117-server-check.sh`. Its captured output is `us-117-server-check-output.txt`. The screenshot `us-117-server-check-output.png` is not saved yet (owner waived it at acceptance).

**Details:**

1. The live graph was imported again from the same OSM file with `osm_way_id` in `graph.encoded_values`.
   The image was rebuilt first from the server's desktop, and a read-only export against the old graph then refused with the message about `osm_way_id`, which showed the new jar was in the image.
   `graphhopper` was recreated alone with `--no-deps` at 15:52:39 +07 and was healthy 40 seconds later.
   `/info` lists the four profiles and `osm_way_id`, the log shows `TimeAwareGraphHopper active`, and a truck route returns 1,905.742 m, as before.
2. The graph hash did not change, `8c13d884...`, with 67,833 edges and 51,328 nodes.
   The same OSM file gives the same edges, so every edge depth table stays valid and task `9c` builds nothing new.
3. `export-edges.sh` wrote format 3 to `data/mapping/graph_export`. Two exports were identical, and the rows matched `edge_count`.
   The old export is in `graph_export.bak-2026-10-12-us117`.
4. The live `graph_edge` got `edge_key` and its unique index from `create_graph_edge_table.py` before the import.
   The loader then filled it in 2.1 seconds: 67,833 edges, 67,833 keys, 67,833 distinct keys, over 30,185 ways. A second load changed nothing.
   The largest position is 48.
5. Only 27,860 of the 67,833 edges lie on a way that `road_segment` holds, because the graph has more road classes than the 12,431 ways of `road_segment`.
   The key joins to `road_segment` only for those edges, so a story that moves a reader from pieces to edges does not use that join.
6. `check_tables.py` reports `FRESH`, `POST /route` of the backend returns the same route, and `POST /route/departures` answers `status: ok` from the table of run `20261011T001500`.
7. The criteria and what covers them:
   - The keys of a graph imported twice from one file are equal: `ExportEdgesTest` (CI run 38223799828) and the keys of the throwaway import and the live import.
   - No two rows share a key: the unique index, and the loader refuses a repeated key before it writes.
   - A graph imported from a changed OSM file: the rule is in [[graph-reimport-procedure]], and the tests prove it only on a small graph. No real changed extract was compared, so the rule for a way whose number of edges changed is not measured.
8. The largest way id is 1,556,752,106, which is 72.5 percent of the 31-bit limit of `osm_way_id`.
