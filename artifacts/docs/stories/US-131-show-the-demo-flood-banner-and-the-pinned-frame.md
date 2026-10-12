---
date_drafted: 2026-10-12
type: user-story
us_id: "US-131"
title: "Show the demo flood banner and the pinned frame"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
kind: story
priority: P2
estimate: M
sprint: 
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]", "[[decision-log|D-030]]", "[[decision-log|D-013]]", "[[test-dataset]]"]
tags: [user-story]
---

# US-131 Show the demo flood banner and the pinned frame

As a visitor, I want a warning and a still frame of the demo flood when no flood is forecast, so I know the map shows a past storm.

Part four of [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]], and the only part that is frontend work, so it is not in the backend sprint.
The map reads the mode from [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]].
In `DEMO` mode it shows the pinned frame with no slider and no animation, and the warning "No flood forecasted, displaying the demo flood of Sep 16, 2026", in English only.
In `PENDING` mode it shows a dry map and a warning that the simulation is running.

Given mode `DEMO`, when a visitor opens the flood map, then the pinned frame and the exact warning show.
Given mode `PENDING`, then the map is dry and the warning says the simulation is running.
Given mode `LIVE`, then the map shows the real result as today.

Dependencies: [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]] is `Done`.

## Acceptance check

On the server, with a screenshot of each mode.

## Status history

- **2026-10-12, draft.** Split from [[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]. It stays in the backlog because it is frontend work and the sprint covers the backend.

## Evidence and details

Fill this when the story reaches `Done`.
