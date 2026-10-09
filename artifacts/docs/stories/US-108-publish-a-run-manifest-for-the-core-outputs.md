---
date_drafted: 2026-10-10
type: user-story
us_id: "US-108"
title: "Publish a run manifest for the core outputs"
epic: "[[EP-21-industry-analysis-on-the-flood-data]]"
status: Ready
kind: story
priority: P2
estimate: M
sprint: 
subsystem: airflow-pipeline, core-output
source_ideas: []
related: ["[[core-output-contract]]"]
tags: [user-story]
---

# US-108 Publish a run manifest for the core outputs

As a developer of a consumer outside Airflow, I want one table that says which outputs of a run are published, so I do not poll three places to learn that a run is ready.

A new table `flood_run_output` in `storage-postgres` has one row per run and output: `run_ts`, `output`, and `published_at`.
The primary key is (`run_ts`, `output`).
The outputs are `depth_raster` (task `9b_load_depth_raster`), `extent` (task `9_build_flood_tiles`, after its last tile step), `road_values` (task `flood_on_roads`), and `edge_depth` (task `9c_build_edge_depth_table`).
Each writer inserts its row last, in the same transaction as its data where the output is a table, and after the file rename for the edge depth file.
The table gets a column table and a retention line on `core-output-contract.md`, so `test_core_contract.py` covers it, and the same retention as the run tables (newest 8 runs).

Given a replay run on the server, when all four tasks end, then `flood_run_output` has four rows for that `run_ts`, and for each row the data it names is present: a count query on the matching table or the file named by `latest` shows it.
Given a task that fails, then its row does not exist for that run.
Given the same run loaded again, then no row is duplicated.
Given a session as `routing_reader`, then `SELECT` on the table works.

Dependencies: None. `US-107` adds the table to the list of each role.

## Status history

- **2026-10-10, draft.** Ready: it passes the INVEST check.

## Evidence and details

Fill this when the story reaches `Done`.
A server screenshot of the four rows and the four checks is the evidence.
The concept page [[core-output-contract]] changes with it.
