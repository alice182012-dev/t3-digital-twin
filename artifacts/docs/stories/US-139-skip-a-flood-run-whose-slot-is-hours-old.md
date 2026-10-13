---
date_drafted: 2026-10-13
type: user-story
us_id: "US-139"
title: "Skip a flood_mapping_full run whose slot is hours old"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 
subsystem: airflow-pipeline, 3di-orchestration
source_ideas: []
related: ["[[3di-simulation-orchestration]]", "[[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]", "[[decision-log|D-040]]"]
tags: [user-story]
---

# US-139 Skip a flood_mapping_full run whose slot is hours old

As the owner of the pipeline, I want a run of `flood_mapping_full` to do nothing when its slot is hours old, so an unpause or a long queue cannot revive old work.

On 2026-10-13 the owner unpaused the DAG, and a run from 2026-10-10 resumed at `3_calculate_depth`.
It published a run, the standing-flood rule saw that fresh publish, and the slots of 03:30 and 03:45 UTC started two real 3Di simulations with a forecast of 0 mm/h.
Each simulation costs 3Di compute, and the published run was three days old.
The story adds a guard to the tasks `0_check_forecast_rain`, `1_trigger_simulation`, `3_calculate_depth`, `3b_publish_depth_files`, and `9b_load_depth_raster`.
When the slot of the run (`run_slot`) is older than `FLOOD_STALE_RUN_MINUTES` (default 120, passed by `compose.yml`), the task raises `AirflowSkipException` with the slot, its age, and the limit, and the run ends as skipped.
The value 0 turns the guard off.
A run takes about 25 minutes from its slot to `9b`, so 120 minutes leaves room for a queue and a retry.

Given a run whose slot is 3 hours old, when one of the five tasks starts, then it is skipped with a message that names the slot, the age, and the limit, no simulation starts, and no depth file or tile is published.
Given a run whose slot is 20 minutes old, then the tasks run as before.
Given `FLOOD_STALE_RUN_MINUTES=0`, then no run is skipped.
Given a value that is not a whole number of minutes, then the DAG fails to parse with a message that names the variable.

Dependencies: None. Deploy it after the server steps of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], because the guard would skip the frozen run of 03:45 UTC that the check of US-123 needs.

## Status history

- **2026-10-13, Ready.** Raised by the unpause of 2026-10-13 ([[US-123-delete-flood-on-roads-and-flood-road-values|US-123]]). It is in the backlog and has no `sprint`, as the product owner asked. The code is built on the branch `us-139-stale-run-guard`, which is not merged into `modular` until the server steps of US-123 end.

## Evidence and details

Fill this when the story reaches `Done`.
