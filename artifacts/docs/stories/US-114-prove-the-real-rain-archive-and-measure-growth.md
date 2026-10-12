---
date_drafted: 2026-10-12
type: user-story
us_id: "US-114"
story_label: "2"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
kind: story
priority: P1
estimate: S
sprint: 
subsystem: core-output
source_ideas: []
related: ["[[US-094-archive-results-3di-nc-and-a-run|US-094]]", "[[EP-15-archive-and-netcdf-retirement]]", "[[decision-log|D-016]]", "[[decision-log|D-019]]"]
tags: [user-story]
title: "Prove the real-rain archive on the first run above 5 mm/h and measure growth"
---

# US-114 Prove the real-rain archive on the first run above 5 mm/h and measure growth

As the owner of the case-study data, I want the first real-rain run kept on D: and its growth measured, so that a past storm can be analyzed after the 24-hour cleanup deletes `RESULT_DIR`.

Part two of [[US-094-archive-results-3di-nc-and-a-run|US-094]].
Part one deploys the archive mount and shows the test-rain skip.
The archive copy runs only in real-rain mode, so no run has proved it yet.

Given a real-rain run above the rain gate of 5 mm/h (or above the lowered gate that [[decision-log|D-035]] allows if no forecast passes 5 mm/h by 2026-10-23), with `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_MM_HR` unset, when the run finishes, then `results_3di.nc` and `run_record.json` exist under `<sim_id>/` in the archive folder (`D:\airflow_new_data\archive` on the server).
Given that run, when the 24-hour cleanup in `9_build_flood_tiles` has run, then both files are still there.
Given the copy, when it ends, then the task logs the free space of D: and fails loudly when the free space is below `ARCHIVE_MIN_FREE_GB`, which is 50 GB ([[decision-log|D-035]]).
Given the run record, then it holds `sim_id`, `run_timestamp`, `rain_input`, `model_id`, `graph_hash`, `bytes`, and `sha256`.
Given a week of real-rain runs, then the daily growth in GB is measured and recorded in this file.

The proof is a one-off run that reads the real Tomorrow.io forecast, with the test-rain variables unset (the user, 2026-10-08).
The forecast has to pass the rain gate, so the run cannot be scheduled.

The product owner confirmed the 50 GB free-space floor (`ARCHIVE_MIN_FREE_GB`) on 2026-10-12.
The product owner also allowed a lowered rain gate, if no forecast passes 5 mm/h by 2026-10-23 ([[decision-log|D-035]]).
The value of the lowered gate is not set.

Dependencies: [[US-094-archive-results-3di-nc-and-a-run|US-094]] part one is `Done`.
This story blocks [[US-095-retire-the-netcdf-values-ingest|US-095]] and [[US-086-prune-old-rows-of-flood-road-values|US-086]], as the original US-094 did.

Design points already built: a full D: does not stop `9_build_flood_tiles`, because the join task `2c_archive_done` uses trigger rule `all_done`, and the cleanup is age-based at 24 hours, so a failed copy has that long to be retried.
The proof must confirm both points on the real run.

Estimate: S.

## Status history

- **2026-10-12, not started.** Split from US-094 at Sprint 13 planning. It stays in the backlog with no sprint, because its proof waits for a forecast above 5 mm/h ([[decision-log|D-016]], [[decision-log|D-019]]).
- **2026-10-12, not started.** The product owner confirmed the floor of 50 GB and allowed a lowered rain gate after 2026-10-23 ([[decision-log|D-035]]). The story stays in the backlog with no sprint.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the archive folder listing after the real run is the evidence.
