---
date_drafted: 2026-10-12
type: user-story
us_id: "US-128"
title: "Run the test suites against the test databases"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-128 Run the test suites against the test databases

As a developer, I want one command that runs the database tests against the test databases, so no test needs a throwaway container.

Today each suite takes its own variable (`FLOOD_TEST_DSN`, `EDGE_DEPTH_TEST_DSN`, `FLOOD_TEST_TIMESCALE_DSN`) and a throwaway PostGIS or TimescaleDB.
The story adds a command that creates a scratch database on each existing server, points the variables at it through an SSH tunnel, runs the suites, prints the counts, and drops the scratch databases ([[decision-log|D-048]]).
The suites do not run against `minio_custom_test` and `flood_metrics_test`, because about 9 of them create and drop tables in `public`, which would delete the restored dataset.

Given the command on the Mac, when it runs, then the suites that skip without a DSN run against the scratch databases, and their counts are printed per folder.
Given the command stopped by an error or by Control-C, then the scratch databases are dropped.
Given the row counts of the restored tables of `minio_custom_test` and `flood_metrics_test` before and after the run, then they are equal.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]].

- **2026-10-12, Ready.** Picked for the sprint at the product owner's request. [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`. Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]].
- **2026-10-13, Ready.** The design changed after a check of the suites: scratch databases instead of the dataset databases ([[decision-log|D-048]]). The code is being written. The run on the server waits for the end of the 50-run check of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and for [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]], so it runs the final suites.

## Evidence and details

Fill this when the story reaches `Done`.
