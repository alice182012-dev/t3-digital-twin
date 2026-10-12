---
date_drafted: 2026-10-10
type: user-story
us_id: "US-111"
title: "Write the forecast mode status row (part one of the pinned demo flood)"
epic: "[[EP-17-flood-data-pipeline-and-core-output|EP-17]]"
status: Ready
kind: story
priority: P2
estimate: S
sprint: 14
subsystem: flood-extent
source_ideas: []
related: ["[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[minio-flood-extent-pipeline]]", "[[core-output-contract]]", "[[edge-depth-table-format]]", "[[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]", "[[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]"]
tags: [user-story]
---

# US-111 Write the forecast mode status row (part one of the pinned demo flood)

As a visitor who opens the flood map on a day with no forecast rain, I want the map, the routing, and the depth popup to use a pinned demo flood with a warning, so the map has a flood to show when the simulation has none.

The flood map has three modes, set by the rain forecast from Tomorrow.io ([[decision-log|D-013]]) and the steps the simulation has published ([[decision-log|D-030]]).

- **LIVE:** rain is forecast above the threshold, or a standing flood exists, and real simulation steps are published. The map shows the real result, as today.
- **PENDING:** rain is forecast, but the simulation has published no step yet. The map shows a dry map with a warning that the simulation is running.
- **DEMO:** no rain is forecast past the threshold and no flood stands. The map shows the demo flood with the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.

The demo is one static frame, the peak step of the 12-hour replay of the 2026-09-16 storm ([[US-088-cut-the-hanoi-storm-of-2026-09|US-088]]).
It has no slider and no animation.

Given no rain is forecast past the threshold and no flood stands, when a visitor opens the flood map, then the map shows the pinned demo flood and the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026".

Dependencies: [[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]] ran the replay that supplies the peak step.
The DAG was not changed while that replay ran.

## Split

The story was an L, so it was split on 2026-10-12, as [[scrum-framework]] requires.
This story is part one, the status row, and its estimate is S.
The other parts have their own IDs:

- [[US-129-pin-the-peak-step-of-the-demo-flood|US-129]] pins the peak step so that no prune removes it (M).
- [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] serves the mode and reads the pinned step in the backend (M).
- [[US-131-show-the-demo-flood-banner-and-the-pinned-frame|US-131]] shows the banner and the pinned frame in the frontend (M, backlog, not backend).

## Part one: the status row

Task `0_check_forecast_rain` already decides the rain gate for each run.
This part writes that decision to a table, so the backend can read it.
The table holds one row per decision: the time, the forecast peak in mm/h, the gate in mm/h, whether a flood stands, and the mode (`LIVE`, `PENDING`, or `DEMO`).
The mode follows the definitions at the top of this story.
The table is a contract table: it goes on [[core-output-contract]] and in the `routing_reader` list, or the backend gets `permission denied`.
The signal is a proposal of the first draft, and this part confirms it or changes it.

Given a run of `flood_mapping_full` with rain above the gate, when `0_check_forecast_rain` ends, then the status table has a row for that decision with mode `PENDING` until the first step is published, and `LIVE` after.
Given a decision with no rain above the gate and no standing flood, then the row has mode `DEMO`.
Given the role `routing_reader`, then it can read the table, and a write fails with a permission error.

## Acceptance check

On the server, after the change is pulled.
Read the newest status row with `psql`, and take a screenshot of the query result and of the contract page entry.

1. Given the table, when a gate decision runs, then one row holds the mode, the forecast peak, the gate, and the standing-flood flag.
2. Given `routing_reader`, then `SELECT` works and an `INSERT` fails.

## Status history

- **2026-10-10, draft.**
  Written from decision [[decision-log|D-030]].
  No code is written, and no branch holds the feature.

- **2026-10-12, Ready.** Split into four stories at the product owner's request, and this part is picked for [[SPR-014-finish-the-remaining-backend|SPR-014]]. The plan of the original story moved to the parts.

## Evidence and details

Fill this when the story reaches `Done`.
