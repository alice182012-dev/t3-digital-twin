---
date_drafted: 2026-10-13
type: user-story
us_id: "US-134"
title: "Set the same rain gate in every Airflow container"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Reviewed
kind: story
priority: P3
estimate: XS
sprint: 14
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
- **2026-10-13, Ready.** Picked for [[SPR-014-finish-the-remaining-backend|SPR-014]] at the product owner's request, and `Ready` after the INVEST check: it has no open dependency, it fits one sprint, and its acceptance is a check on the server.
- **2026-10-13, Reviewed.** Done on the server. The owner has not accepted it. The scheduler, the API server, and the DAG processor held `FLOOD_RAIN_THRESHOLD_MM_HR=0.01`, and the worker held 5. The owner paused `flood_mapping_full`, and the four containers were recreated with `docker compose up -d --no-deps` over SSH. All four now read 5.

## Evidence and details

**Evidence:** the value read in each Airflow container after the recreation (details item 2). No screenshot yet.

**Details:**

1. `compose.yml` passes `${FLOOD_RAIN_THRESHOLD_MM_HR:-5}` to every Airflow service, and the server `.env` has no value, so the old 0.01 came from containers created while a lowered gate was set. No file changed.
2. After the recreation, `printenv FLOOD_RAIN_THRESHOLD_MM_HR` gives 5 in `airflow-scheduler-1`, `airflow-worker-1`, `airflow-apiserver-1`, and `airflow-dag-processor-1`. `airflow dags list-import-errors` reports none.
3. Recreating the worker would have stopped a running task, so it waited until `3_calculate_depth` of the 03:45 UTC run had finished. A paused DAG does not schedule the next tasks of a run, so that run stays in the state `running` with `3b_publish_depth_files` and `9b_load_depth_raster` not started, until the owner unpauses the DAG.

