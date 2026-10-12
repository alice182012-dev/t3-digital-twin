---
date_drafted: 2026-10-12
type: user-story
us_id: "US-125"
title: "Restore the snapshot into test databases"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Not started
kind: story
priority: P1
estimate: M
sprint: 
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-125 Restore the snapshot into test databases

As a developer, I want a script that restores the snapshot into two test databases, so tests run on the real storm without touching production data.

The script creates the database `minio_custom_test` in `storage-postgres` and `flood_metrics_test` in `timescaledb`, runs the DDL scripts of `scripts/database/` against them, and loads each CSV of `snapshot/` in the order of the foreign keys.
It takes the database names from the environment, so the pipeline code under test needs only `POSTGRES_DB` and `TIMESCALE_DB`.
It runs again without error and gives the same rows.
The story checks `docker system df` first and reports the size that the restore adds to the Docker disk ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).

Given an empty test database, when the script runs, then every table has the row count of `snapshot/MANIFEST.json`.
Given the script run twice, then the counts do not change.
Given the production databases, then a row count before and after the restore is the same.

Dependencies: [[US-124-save-the-storm-replay-results-and-derived-data|US-124]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]]. It stays in the backlog until the owner accepts the decision.

## Evidence and details

Fill this when the story reaches `Done`.
