---
date_open: 2026-10-09
date_closed: 2026-10-09
type: blocker
status: resolved
severity: P2
subsystem: time-aware-routing
approaches_tried: 2
approaches_remaining: 0
tags: [blocker, routing, graph-export, us-092, us-093]
related: ["[[US-090-093-routing-paper-experiments-stories]]", "[[sprint-plan-3]]", "[[time-aware-routing-engine-stories]]"]
last_updated: 2026-10-09
---

# edge-export-has-no-node-ids

## Description

The offline reference (`scripts/routing_reference/sticky_reference.py`) needs a `Graph` of edges with a tail node, a head node, and a travel time. The export of the GraphHopper graph gives only `edge_id` and `wkt` per edge (`java/time-aware-routing/README.md`, `scripts/edge_depth/graph_edges.py`), so a real graph cannot be built from it.

- `ExportEdges.java` already reads the base node and the adjacent node of each edge to compute the graph hash, and then does not write them.
- The NetCDF `results_3di.nc` is not a source. It holds the 3Di computational grid (flood-model nodes, cells, water levels). The node ids of the road graph belong to GraphHopper.
- Deriving nodes from the endpoints of the WKT lines is possible, but it guesses at shared coordinates and gives no travel time or direction per vehicle.

## Why this matters

`US-092` and `US-093` run on the offline reference. Without node ids, both can run only on synthetic graphs, so neither can report a number for Hanoi. Both also wait for the depth tables of the second replay (D-020), so no row loses time yet. The blocker does not stop Sprint 13.

## Approaches tried

### Approach 1

Read `ExportEdges.java`, `graph_edges.py`, and the README on 2026-10-09. Found the node ids are available in the exporter and not written. No code changed.

## Decision and explanation

Approved by the user on 2026-10-09 and built (`a4a1372`, `c654962`, `307b872`). Fix: add `base_node` and `adj_node` columns to `edges.csv` in `ExportEdges`, keep the graph hash unchanged, and add a `travel_seconds` per vehicle only if the reference needs it (otherwise derive it from length and the profile speed). The Java suite runs on GitHub Actions, and the export itself runs on the server. Waits for the user's go.

## Related topics

- [[US-090-093-routing-paper-experiments-stories]] Stories 3 and 4

## Status history

- **2026-10-09, open.** Found while reviewing the offline sweep. Rule 11 case: it does not block build in the next sprint, so a subagent can fix it in its own worktree while Sprint 12 continues. Its diff is reviewed before it lands. The user's go is pending.
- **2026-10-09, monitoring.** The user approved the fix. `ExportEdges` writes `base_node` and `adj_node` (format version 2, hash unchanged), and `graph_edges.py` reads versions 1 and 2. Java suite: 130 tests passed on GitHub Actions (run 37885465511). It resolves after the next export on the server and one `Graph` built from it.
- **2026-10-09, resolved.** `export-edges.sh` ran on the server against the rolled-out `graphhopper-time-aware:local` image (`SKIP_BUILD=1`): format version 2, 67,833 edges, 51,328 nodes, two exports identical, files in `D:\airflow-data\mapping\graph_export`. `scripts/routing_experiments/real_graph.py` built a `Graph` from the copy in `marie-curie/graph_export_2026-10-09/` (0.5 s), the graph hash equals the hash of the replay table `20261009T031500`, and `sweep_fraction` routed 20 random node pairs for the car in 4.5 s. Two limits stay and any result must name them: the export has no one-way flag, so one-way roads are open both ways, and the travel time is length at one free-flow speed (30 km/h by default).
