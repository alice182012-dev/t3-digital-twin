---
date_drafted: 2026-10-12
type: user-story
us_id: "US-128"
title: "Run the test suites against the test databases"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Not started
kind: story
priority: P2
estimate: S
sprint: 
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-128 Run the test suites against the test databases

As a developer, I want one command that runs the database tests against the test databases, so no test needs a throwaway container.

Today each suite takes its own variable (`FLOOD_TEST_DSN`, `FLOOD_ROADS_TEST_DSN`, `FLOOD_TEST_TIMESCALE_DSN`) and a throwaway PostGIS or TimescaleDB.
The story adds a command that sets them to the test databases through an SSH tunnel, runs the suites, and prints the counts.
A suite that creates tables works in its own schema and drops it, as the suites do now, so the dataset stays unchanged.

Given the command on the Mac, when it runs, then the suites that skip without a DSN run, and their counts are printed.
Given the restore row counts before and after the run, then they are equal.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]].

## Evidence and details

Fill this when the story reaches `Done`.
