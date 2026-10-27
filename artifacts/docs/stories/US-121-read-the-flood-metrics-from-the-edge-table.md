---
date_drafted: 2026-10-12
type: user-story
us_id: "US-121"
title: "Read the flood metrics from the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
kind: story
priority: P2
estimate: M
sprint: 14
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[decision-log|D-038]]", "[[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]"]
tags: [user-story]
---

# US-121 Read the flood metrics from the edge table

As an analyst, I want the flood metrics of each road to be built from the edge table, so they stay valid after a graph re-import.

`extract_run.py` loads each piece's series from `flood_road_values` by `segment_id` and road name, and writes `flood_segment_metrics`.
The story re-keys the metrics on `edge_key` and decides how a road with several edges is reported, because the metrics count pieces today and the engine counts edges.
It keeps the thresholds of `impassable_from_m` and the rule that a dry run gives 0 cm ([[decision-log|D-036]]).

Given a replay run, when `extract_run.py` runs on the new table, then every edge with a wet step has metric rows, and the story records how the totals differ from the piece-based totals.
Given a run with no wet edge, then the script writes no metric rows and exits without error, where it raises today.
Given a graph re-import, then the metrics of the old keys are kept and marked, by the rule of [[US-117-export-a-stable-key-with-each-graph-edge|US-117]].

Dependencies: [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] is `Done`.

## Status history

- **2026-10-12, draft.** Split from [[decision-log|D-038]], which replaces `flood_road_values` with the edge depth table in stages. It stays in the backlog until the owner accepts the decision.
- **2026-10-12, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: its dependencies are `Done` or in the same sprint, and its acceptance check is written.
- **2026-10-12, Reviewed.** Built and tested, not deployed. `extract_run.py` reads `edge_depth` and `edge_depth_run`, fills each dry step of a wet edge with 0 from `valid_times`, and keys each row by `edge_key`. A road with several edges is reported per edge, with no `road_name`, because `graph_edge` has no name. Group by the way id in the key to report a road. Metric times stay in local time (UTC+7), as in the rows already written, while the edge tables hold UTC. A run with no wet edge writes no rows and does not raise. A run that `edge_depth_run` does not list, or an edge that `graph_edge` lacks, is an error. `flood_segment_metrics` keeps the rows of the piece-based extraction, and a check allows exactly one of `segment_key` and `edge_key` per row. A rerun replaces only the edge-keyed rows. 26 tests in `scripts/flood_metrics` pass against a throwaway PostGIS. Still open: the totals compared with the piece-based totals on the storm runs, and a run of `build_history_and_metrics.py`, which still takes its run list from `flood_road_file` and fails until the test databases hold `edge_depth`.
- **2026-10-13, Done.** The product owner accepted it after the server check. The evidence is the screenshot `US-121-server-metrics-totals-2026-10-13.png`.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/US-121-server-metrics-totals-2026-10-13.png`, the number of closed edges per vehicle for run `20261010T223000`.

**Details:**

1. `create_flood_metrics_tables.py` ran in the worker and added `edge_key` and its checks to `flood_segment_metrics`.
2. `extract_run.py 20261010T223000` wrote 11,496 rows, which is 2,874 edges times 4 vehicle types.
3. The screenshot counts the rows of the run that are not `never_impassable`: car 481, foot 324, motorbike 784, and truck 399.
   Each count equals the number of edges whose deepest value is at or above the limit of the vehicle (0.3, 0.4, 0.2, and 0.35 m).
4. The totals agree with the piece-based totals within 2 points.
   The piece-based numbers come from `flood_road_values` (file 532, 2,457 pieces) and the edge numbers from `edge_depth` (2,874 edges).

   | Vehicle | Pieces closed | Edges closed |
   | --- | --- | --- |
   | motorbike | 622 of 2,457 (25.3%) | 784 of 2,874 (27.3%) |
   | car | 370 of 2,457 (15.1%) | 481 of 2,874 (16.7%) |
   | truck | 304 of 2,457 (12.4%) | 399 of 2,874 (13.9%) |
   | foot | 240 of 2,457 (9.8%) | 324 of 2,874 (11.3%) |

5. The counts differ because a wet edge is a part of a piece or a whole one, and the graph has more edges than the pieces.
6. The only piece-based rows in `flood_segment_metrics` are those of run `20260930T020000`, so the old extractor was not run on the storm run.
   `build_history_and_metrics.py` was not run.

