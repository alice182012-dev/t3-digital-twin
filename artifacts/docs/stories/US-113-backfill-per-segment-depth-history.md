---
date_drafted: 2026-10-12
type: user-story
us_id: "US-113"
title: "Backfill per-segment depth history from flood_road_values"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P1
estimate: S
sprint: 13
subsystem: airflow-pipeline, timescaledb
source_ideas: []
related: ["[[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]]", "[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]]", "[[decision-log|D-032]]", "[[decision-log|D-017]]", "[[core-output-contract]]", "[[timescaledb-schema]]"]
tags: [user-story]
---

# US-113 Backfill per-segment depth history from flood_road_values

As an analyst, I want the runs that are still in `flood_road_values` loaded into `depth_history`, so the history does not start on the day the loader is deployed.

This is part (b) of the split of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].
The loader of part (a) writes each new run.
This story loads the runs that already exist.

The backfill reads only what `flood_road_values` still holds.
Rows older than `FLOOD_ROAD_VALUES_KEEP_HOURS` (default 24) before the newest run are pruned ([[decision-log|D-017]], [[core-output-contract]]), so the backfill covers the runs that remain on the day it runs.

Given the loader of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] on the server, when the backfill runs once, then `depth_history` holds the same rows that the `flood_history` load writes for each run still in `flood_road_values`.
Given the same backfill, when it runs a second time, then the row count does not change.
Given the runs in `flood_road_values` at the time of the backfill, then the story records each `run_ts` it loaded and each one it skipped, with the reason.

Open question for the owner and the team: a run that wets no road piece writes no rows to `flood_road_values` ([[US-105-decide-what-flood-history-the-industry-apps-need|US-105]], Evidence item 5).
Its moments cannot be read from that table, so `history_moment` has no source for such a run.
Which source gives the moments of those runs, or does the backfill skip them?

Dependencies: [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] part (a) is in the same sprint and must be `Done` first.
[[US-105-decide-what-flood-history-the-industry-apps-need|US-105]] is `Done`.

Estimate: S.

## Status history

- **2026-10-12, Ready.** Split from US-106 at Sprint 13 planning. Sized S (2 points). It passes the INVEST check: its dependency is named and in the same sprint, and the acceptance check runs on the server.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the row counts of the backfilled runs, set against the counts of `flood_road_values` for the same runs, is the evidence.
