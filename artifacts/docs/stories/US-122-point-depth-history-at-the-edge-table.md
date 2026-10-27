---
date_drafted: 2026-10-12
type: user-story
us_id: "US-122"
title: "Point depth_history at the edge table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Done
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
- **2026-10-12, Reviewed.** Built and tested, not deployed. `load_run.py` reads `edge_depth` and `edge_depth_run` and writes `depth_history` keyed by `edge_key`, with `depth_m` equal to `depth_cm / 100`. Only wet edges have a row, and `history_moment` marks the dry steps. `create_timescale_tables.py` renames `segment_id` to `edge_key` on an older table. A test on a compressed hypertable (TimescaleDB 2.30.2) shows the rename keeps the compression settings. The rows loaded before the move held piece ids that cannot be mapped to edges, so no mapping list exists. The owner decided to delete them ([[decision-log|D-042]]), and the same step deletes `history_moment`. 16 tests of `test_load_run.py` and 4 of the schema tests pass against a throwaway TimescaleDB. Task `9c` has no ordering against `flood_on_roads`, so a load that runs first fails and the DAG retries once. Still open: the migration on the server database, one run loaded twice on the server, and the rebuild of the history from runs ([[US-113-backfill-per-segment-depth-history|US-113]]).
- **2026-10-13, Done.** The product owner accepted it after the server check. The evidence is the screenshot `US-122-server-load-run-2026-10-13.png`.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/US-122-server-load-run-2026-10-13.png`, the output of `load_run.py 20261010T223000` in the worker.

**Details:**

1. `create_timescale_tables.py` ran on the server TimescaleDB.
   `depth_history` has the primary key `(edge_key, valid_time)`, and `history_moment` exists.
   The step deleted the piece-keyed rows ([[decision-log|D-042]]), and both tables held no row afterwards.
2. `load_run.py 20261010T223000` ran twice.
   Each run printed "8 moments written, 0 skipped for a later run, 20989 rows".
   After each run, `depth_history` held 20,989 rows over 2,874 edges, from 2026-10-10 15:30 to 17:15 UTC, and `history_moment` held 8 rows.
   The rows equal the 20,989 rows of the run in `edge_depth`.
3. The screenshot shows one load.
   The second load was checked by the row counts above.
4. The rows of the other stored runs are not loaded.
   [[US-113-backfill-per-segment-depth-history|US-113]] rebuilds the history from the retained runs.

