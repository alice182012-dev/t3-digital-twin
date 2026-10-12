---
date_drafted: 2026-10-12
type: user-story
us_id: "US-115"
title: "Decide whether the edge depth table replaces flood_road_values"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
kind: spike
priority: P0
estimate: M
sprint: 13
subsystem: routing, flood-data, core-output
source_ideas: []
related: ["[[edge-depth-table-format]]", "[[core-output-contract]]", "[[flood-on-roads]]", "[[decision-log|D-006]]", "[[decision-log|D-032]]", "[[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]]"]
tags: [user-story, spike]
---

# US-115 Decide whether the edge depth table replaces flood_road_values

As the owner of the flood data, I want to know whether one sampler and one table can replace both `flood_road_values` and the edge depth table, so the map, the route fallback, the rain gate, and the depth history all read the same water that the routing engine routes on.

**Why now.**
A run in which no road piece is wet writes no rows to `flood_road_values`.
The winner query of `flood_areas.py` then lets an older, wetter run win for those times, so the map overlay and the route fallback show water that has dried.
The time-aware engine does not have the problem, because its edge depth table is dense (0 for a dry edge).
The `depth_history` of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] reads `flood_road_values`, so the answer decides what that story builds.

**Question.**
Can the edge depth build (task `9c`) feed a queryable table that serves all four readers of `flood_road_values`, and what does the swap cost?

**Timebox.**
Half a sprint, on a copy of the server data in `marie-curie/`, with read-only checks on the server.

The spike answers these points, each with a measured result or the code that proves it:

1. Does a fully dry run reach the readers wrongly today?
   Read the failure path of `extract_run.py` when a run has no rows, and how the DAG that calls it reacts.
   Read how the Java engine picks the table for a time, so the claim "the engine is safe" is checked and not assumed.
2. Does `graph_edge` map to a stable key (`segment_id` or the OSM way) that survives a graph re-import?
   If it does not, say what history keyed on `edge_id` loses at each re-import.
3. What does a sparse table of wet edges per step cost?
   Count rows per run against the 19,656 of `flood_road_values`, and size 24 hours of runs.
4. What does one sampler change in the build time of `9c` against its 5-minute limit ([[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]])?
5. What does each reader need: the overlay and fallback (geometry and a depth band per forecast time), the rain gate (the maximum per run), the metrics (a per-piece series), and the soak checks?

Given the spike on a copy of the server data, when it ends, then the story holds the answers to the five points and a decision `D-nnn` that says replace now, replace later with a trigger, or keep both and fix the winner query with the run registry.
The decision names the stories it creates, and it says what changes for [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].

Dependencies: None.

## Status history

- **2026-10-12, Ready.** Raised at Sprint 13 planning from the question "what does routing do with a run that wets no road piece". The product owner asked for it to be worked first in the sprint. Sized M (3 points) against `US-001`: several code reads, a data query, and a check on the server.
- **2026-10-12, In progress.** Started. The code reads and the server queries ran the same day.
- **2026-10-12, Reviewed.** All five points are answered below, and [[decision-log|D-038]] is proposed: keep both tables and fix the winner query with the run registry. The owner accepts the decision, or chooses another option, before the story is `Done`.

## Evidence and details

**Evidence:** read-only queries on the server on 2026-10-12 (Airflow metadata and `storage-postgres`) and the code paths named below. The spike builds nothing, so it has no screenshot.

**Details:**

1. A fully dry run reaches two readers wrongly and the others correctly.
   `flood_on_roads.py` keeps only pieces with `max(depth) > 0`, so a dry run writes no rows to `flood_road_values`.
   The winner query of `flood_areas.py` (`_WINNER_SEG_SQL`) takes the newest `timestamp` that has rows at a forecast time, so an older, wetter run wins and the overlay and the route fallback show water that has dried.
   The rain gate (`standing_flood.py`) reads `flood_road_file` with a `LEFT JOIN` and `coalesce(max(depth), 0)`, so a dry run counts as dry and the gate is right.
   `extract_run.py` raises `no flood_road_values rows for run`, and no DAG calls it, so only a manual run sees the error.
   The Java engine is safe. `TimeAwareRouter.decide` reads one table, `tables.current()`, which is dense (0 for a dry edge), and `floorToStep` picks the step from that table's own step times.
2. `graph_edge` has no stable key.
   It holds `edge_id`, `length_m`, and `geom`. The export `edges.csv` holds `edge_id`, `wkt`, `base_node`, and `adj_node`, and GraphHopper renumbers all three on every import.
   History keyed on `edge_id` is orphaned at each re-import ([[graph-reimport-procedure]]) unless the export gains an OSM way id.
   `road_segment` has the stable keys: `segment_id` and `way_id`. It holds 35,652 pieces from 12,431 ways, and `graph_edge` holds 67,833 edges. The two sets do not match one to one.
3. A sparse edge table is not smaller than today's table.
   `flood_road_values` holds 75 runs, 1,911,344 rows, and 1,275 MB. A recent run has 18,848 to 20,728 rows.
   The `wet_edges` of the two latest `9c` runs are `[135, 1401, 1953, 2247, 2457, 2599, 2725, 2853]` (16,370 wet edge-steps) and `[127, 135, 1403, 1952, 2246, 2455, 2597, 2735]` (13,650).
   So a sparse edge table has 13,650 to 16,370 rows per run, against about 20,000 today. At 96 runs in 24 hours, that is 1.1 to 1.6 million rows, against 1.9 million.
   Row count and storage are the same order, so a sparse table saves little.
   A sparse table also keeps the dry-run bug: a run with no wet edge has no rows, and the winner query still cannot see it.
4. One sampler would cost less than two, and the saving is small against the limit.
   Over the last 3 days (116 successful runs of `routing_adapter`), `9c_build_edge_depth_table` took 74 s on average and 109 s at most, and `flood_on_roads` took 62 s on average and 80 s at most.
   Both run in one pool slot, so a run spends about 136 s in them.
   One sampler that writes both outputs would take about the `9c` time plus the row insert, so it saves up to 62 s per run.
   The 5-minute limit of [[BL-023-9c-sampling-step-runs-over-770-seconds|BL-023]] is met by `9c` alone today, and `9c` grew from 57 s to 109 s along a chain in the replay of [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]. Merging the samplers puts the `flood_on_roads` work inside that growth.
   The spike did not build the merged sampler, so the figure is an estimate from the two measured times.
5. The four readers need these:
   - Overlay and fallback: the geometry of each wet piece and its depth per forecast time, plus a record that a run exists at that time. `graph_edge.geom` gives the geometry, but not the run record.
   - Rain gate: the maximum depth per run, which also needs the run record. `flood_road_file` already has it.
   - Metrics (`flood_metrics`): the full series of each piece, keyed on `segment_id`, with the road name. The edge table has no `segment_id`, so a swap breaks the metrics at each re-import.
   - Soak checks: roads whose depth lies between two vehicle limits. A dense or sparse table with geometry serves them.
6. The cause of the stale overlay is the missing record of a dry run, not the table. The winner query needs a run registry, and `flood_road_file` already holds a row for every run, including a run with `feature_count` 0 ([[decision-log|D-036]]).
7. The server had no run with `feature_count` 0 among 75 runs, so [[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]] needs a constructed dry run for its test.
