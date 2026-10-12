---
date_drafted: 2026-10-11
type: user-story
us_id: "US-112"
title: "Keep the edge depth files to the newest 8 runs"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: In progress
kind: story
priority: P3
estimate: S
sprint: 13
subsystem: core-output, airflow-pipeline
source_ideas: []
related: ["[[core-output-contract]]", "[[edge-depth-table-format]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]", "[[decision-log|D-033]]", "[[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]]"]
tags: [user-story]
---

# US-112 Keep the edge depth files to the newest 8 runs

As the owner of the core outputs, I want the edge depth volume to hold the newest 8 runs, the same count as the depth rasters, so that the disk use matches the contract.

The product owner set the count to 8 on 2026-10-12 ([[decision-log|D-033]]).
The count matches `flood_depth_raster_tile`, which keeps the newest 8 runs (`FLOOD_RASTER_KEEP_RUNS`, default 8, in `scripts/flood_extent/raster_load.py`).
The contract page and the edge depth format page still say 3 until this story is `Done`.

On 2026-10-11, the `edge-depth-tables` volume held about 35 `.bin` files.
The contract in [[core-output-contract]] named the newest 3, and the code default in `dags/routing_adapter_dag.py` is 3.
`compose.yml` defaults `EDGE_TABLE_KEEP_RUNS` to 60.
[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] raised it to 100 in the server `.env` for the second replay.
The raised value is the likely cause of the 35 files, but the server's current value is not read, so the cause is unverified.

Work: set the count to 8 in the code default (`dags/routing_adapter_dag.py`), in `compose.yml`, and in the server `.env`.
Set the contract row of the edge depth files to 8 in [[core-output-contract]], and the retention line of [[edge-depth-table-format]] to 8.

Given the count of 8, when task `9c_build_edge_depth_table` publishes on the server after the change, then the volume holds 8 `.bin` files, the file that `latest` names is one of them, and [[core-output-contract]] and [[edge-depth-table-format]] state the same count.

Dependencies: none. The count is the owner's decision ([[decision-log|D-033]]), made on 2026-10-12.

Estimate: S.

## Status history

- **2026-10-11, draft.** Found during the server check of [[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]].
  It was a backlog story with no sprint.
- **2026-10-12, Ready.** The product owner set the count to 8 ([[decision-log|D-033]]). The story named the count the contract named, which was 3, so its title and text now name 8. The contract page changes with this story.
  Sized S (2 points), with no dependency. Picked for Sprint 13.
- **2026-10-12, In progress.** The code default (`dags/routing_adapter_dag.py`) and the `compose.yml` default are 8, with a test for each, and the two pages are updated. The server `.env` change waits for the owner's go.

## Evidence and details

Fill this when the story reaches `Done`.
