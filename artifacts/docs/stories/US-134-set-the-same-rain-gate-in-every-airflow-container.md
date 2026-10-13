---
date_drafted: 2026-10-13
type: user-story
us_id: "US-134"
title: "Set the same rain gate in every Airflow container"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
kind: story
priority: P3
estimate: XS
sprint: 
subsystem: airflow-pipeline, deploy
source_ideas: []
related: ["[[3di-simulation-orchestration]]", "[[decision-log|D-037]]", "[[US-111-show-a-pinned-demo-flood-when-no-rain-is-forecast|US-111]]"]
tags: [user-story]
---

# US-134 Set the same rain gate in every Airflow container

As a developer, I want every Airflow container to hold the same `FLOOD_RAIN_THRESHOLD_MM_HR`, so a task test gives the gate that a real run uses.

On 2026-10-13 the scheduler container had `FLOOD_RAIN_THRESHOLD_MM_HR=0.01` and the worker had 5, although `compose.yml` passes `${FLOOD_RAIN_THRESHOLD_MM_HR:-5}` to all of them.
The scheduler was probably created while the lowered gate was set and was not recreated after [[decision-log|D-037]] withdrew it.
`airflow tasks test` in the scheduler therefore wrote a `forecast_mode` row with a gate of 0.01.
The story recreates the scheduler, and it checks every Airflow container for the value.

Given the server after the change, when the variable is read in each Airflow container, then every value is 5.

Dependencies: None.

## Status history

- **2026-10-13, draft.** Found during the server checks of [[SPR-014-finish-the-remaining-backend|SPR-014]]. The owner asked for a story on the same day.

## Evidence and details

Fill this when the story reaches `Done`.
