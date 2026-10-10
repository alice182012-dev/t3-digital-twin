---
date_drafted: 2026-10-11
type: user-story
us_id: "US-112"
title: "Keep the edge depth files to the count the contract names"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
kind: story
priority: P3
estimate: S
sprint: 
subsystem: core-output, airflow-pipeline
source_ideas: []
related: ["[[core-output-contract]]", "[[edge-depth-table-format]]", "[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]]"]
tags: [user-story]
---

# US-112 Keep the edge depth files to the count the contract names

As the owner of the core outputs, I want the edge depth volume to hold only the files the contract names, so that the disk use matches the contract.

On 2026-10-11, the `edge-depth-tables` volume held about 35 `.bin` files.
The contract in [[core-output-contract]] says the newest 3 stay (`EDGE_TABLE_KEEP_RUNS`).
The default in `dags/routing_adapter_dag.py` is 3, but `compose.yml` defaults `EDGE_TABLE_KEEP_RUNS` to 60.
[[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] raised it to 100 in the server `.env` for the second replay.
The raised value is the likely cause, but the server's current value is not read, so the cause is unverified.

Given the owner has chosen the kept count, when task `9c_build_edge_depth_table` publishes on the server after the change, then the volume holds that many `.bin` files, the file that `latest` names is one of them, and the contract page states the same count.

Dependencies: None. The count is the owner's decision, so the story waits for it.

## Status history

- **2026-10-11, draft.** Found during the server check of [[US-108-publish-a-run-manifest-for-the-core-outputs|US-108]].
  It is a backlog story with no sprint.

## Evidence and details

Fill this when the story reaches `Done`.
