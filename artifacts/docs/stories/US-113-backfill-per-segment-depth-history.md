---
date_drafted: 2026-10-12
type: user-story
us_id: "US-113"
title: "Backfill the depth history from the runs of the edge depth table"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Reviewed
kind: story
priority: P1
estimate: S
sprint: 14
subsystem: airflow-pipeline, timescaledb
source_ideas: []
related: ["[[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]]", "[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]]", "[[decision-log|D-032]]", "[[decision-log|D-017]]", "[[core-output-contract]]", "[[timescaledb-schema]]"]
tags: [user-story]
---

# US-113 Backfill the depth history from the runs of the edge depth table

As an analyst, I want the runs that are still in `edge_depth` loaded into `depth_history`, so the history does not start on the day the loader is deployed.

This is part (b) of the split of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].
The loader of part (a) writes each new run.
This story loads the runs that already exist.

The owner rescoped it on 2026-10-13 ([[decision-log|D-047]]).
The backfill reads only the runs that `edge_depth_run` lists, because the loader reads `edge_depth` since [[US-122-point-depth-history-at-the-edge-table|US-122]], and the rows of `flood_road_values` are keyed by piece and cannot be mapped to edges ([[decision-log|D-042]]).
A run that left `edge_depth` is not covered, so the backfill covers the runs that remain on the day it runs.

Given the loader on the server, when the backfill runs once, then `depth_history` holds the same rows that the `flood_history` load writes for each run of `edge_depth_run`.
Given the same backfill, when it runs a second time, then the row count does not change.
Given a run that wets no edge, then each of its moments is recorded as dry at depth 0 cm, and the story records the source it read those moments from.
Given the runs of `edge_depth_run` at the time of the backfill, then the story records each `run_ts` it loaded and each one it skipped, with the reason.

A run that wets no edge writes no rows to `edge_depth`, and `edge_depth_run.valid_times` lists its moments ([[decision-log|D-036]]).
The loader records those moments as dry, at depth 0 cm.

Dependencies: [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] and [[US-122-point-depth-history-at-the-edge-table|US-122]] are `Done`.
[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] is `Done`.

Estimate: S.

## Status history

- **2026-10-12, Ready.** Split from US-106 at Sprint 13 planning. Sized S (2 points). It passes the INVEST check: its dependency is named and in the same sprint, and the acceptance check runs on the server.
- **2026-10-12, Ready.** The product owner decided the rule for a run that wets no road piece ([[decision-log|D-036]]), and the open question is removed from the story.
- **2026-10-12, Ready.** Left Sprint 13 to make room for [[US-115-decide-whether-the-edge-depth-table-replaces-flood-road-values|US-115]]. Its parent, [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], may change with the answer of that spike. `sprint` is cleared and the story returns to the backlog.
- **2026-10-12, sprint 14.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request.
- **2026-10-13, Reviewed.** The owner rescoped it ([[decision-log|D-047]]), and the backfill ran on the server for the 2 runs of `edge_depth_run` (details items 1 to 3). The owner has not accepted it.

## Evidence and details

**Evidence:** the output of `load_run.py` and the row counts in details item 2. No screenshot.

**Details:**

1. `edge_depth_run` lists 2 runs on 2026-10-13: `20261011T001500` (the pinned run) and `20261013T104500`.
   `edge_depth` keeps the pinned run and the newest ones, so no other run is left to load.
   The runs of the 50-run check are in `minio_custom_test` and not in production.
2. `load_run.py` ran for each run, oldest first.
   Before it, `depth_history` held 41,410 rows over 3,025 edges and 24 moments.
   Run `20261011T001500` wrote 1 moment (135 rows) and skipped 7 moments for a later run.
   Run `20261013T104500` wrote 8 moments (1,219 rows).
   After it, `depth_history` held 39,031 rows over 3,021 edges and 24 moments, from 2026-10-10 15:30 to 2026-10-13 05:30 UTC.
   The count fell by 2,379 rows.
   The loader gives a moment to the run with the later `issued_at`, so the moment 17:15 UTC most likely changed from run `20261010T223000` to run `20261011T001500`, which wets fewer edges at that moment.
   The rows of `20261010T223000` are no longer in `edge_depth`, so this cause was not checked.
   A second pass gave the same counts.
3. Loaded: `20261011T001500` and `20261013T104500`. Skipped: none.
   Before the backfill, `depth_history` already held the 8 moments of `20261013T104500` (up to 05:30 UTC), so the `flood_history` DAG had loaded it, and the count did not change when the backfill loaded it again.
4. Not exercised on the server: a run that wets no edge, because both runs wet edges.
   The tests of `test_load_run.py` cover it ([[US-122-point-depth-history-at-the-edge-table|US-122]]).

A server screenshot of the row counts of the backfilled runs, set against the counts of `flood_road_values` for the same runs, is the evidence.
