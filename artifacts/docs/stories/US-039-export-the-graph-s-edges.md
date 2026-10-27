---
date_drafted: 2026-09-29
type: user-story
us_id: "US-039"
story_label: "E1"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: M
sprint: 6
subsystem: airflow-pipeline, floodmap-backend
related: ["[[EP-08-edge-depth-table]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Export the graph's edges"
---

# US-039 Export the graph's edges

As the table builder, I want every GraphHopper edge with its id, geometry, and a graph hash, so depth can be sampled per edge.
Given the built graph on the server, when the export command runs, then it writes one row per edge with the edge id and its geometry in EPSG:4326, plus a hash of the graph build, and the row count equals the graph's edge count.
Dependencies: Story R4 (`US-049`, done).
Evidence: ![[us-039-edge-export-server-output.png|700]]
Details:
1. What: the export command `ExportEdges` in `java/time-aware-routing/`.
   It writes `edges.csv` (the header `edge_id,wkt`, then one row per edge in id order, a LINESTRING in EPSG:4326 with longitude first) and `graph.json` (the graph hash, the edge and node counts, and the GraphHopper commit), plus `export-edges.sh` to run it on the server.
2. How: tests first (11 new, 9 on a hand-made 4-edge OSM file, plus a check that the graph folder is unchanged and a read-only-folder test).
   It opens the graph store directly, read-only, because GraphHopper's own `load()` needs a routing profile.
   The first server run failed: at this GraphHopper commit `BaseGraph` opens the `geometry` file for writing when the default type is a storing one, and `MMAP_RO` is, so a read-only mount broke it.
   I reproduced that as a non-root user on an unwritable folder, and fixed it with a read-only memory-mapped type that is not marked storing.
   The hash is a SHA-256 over the node count, the edge count, and each edge's nodes and points in 1e-7 degrees, with no file timestamps.
3. Why: the table builder (`US-041`) has to sample depth per edge and needs each edge's geometry, and every table must carry the hash of the graph it was built for, so a reader can refuse a table for a different graph (`US-043`, `US-044`).
4. Effect: on the live graph on the server, mounted read-only, the export wrote 67,833 rows for 67,833 edges (51,328 nodes), the count `US-046` recorded.
   Two exports gave identical files and one hash, `8c13d884...c716ce`.
   The live service was not touched.
   `US-041`, `US-043`, and `US-044` can use the format and the hash, which is written into [[edge-depth-table-format]].
   A rebuild of the graph from a changed OSM file changes the hash, and the next export will show it.
5. Limits: the export opens the graph as 2D, which is right for the flood graph (no elevation) and wrong for a 3D graph.
   The comparison of two exports shows the output is stable, not that the geometry is right on the ground.
   The geometry was checked on small graphs only (the hand-made file and Andorra), not against the real map.
