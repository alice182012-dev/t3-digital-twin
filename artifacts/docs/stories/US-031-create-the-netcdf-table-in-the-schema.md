---
date_drafted: 2026-09-24
type: user-story
us_id: "US-031"
story_label: "5"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P2
estimate: S
sprint: 2
subsystem: airflow-pipeline
related: ["[[EP-06-raster-first-pipeline]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Create the netcdf table in the schema task"
---

# US-031 Create the netcdf table in the schema task

As an operator, I want `3b_upload_netcdf_postgres` to stop failing, so a run is not marked
`failed` when every other task succeeded.
Given a database without `netcdf_files`, when `0b_ensure_schema` runs, then the table exists and task 3b succeeds.
Dependencies: None.
Evidence: ![[raster-first-pipeline-sprint2-verification.png|420]]
Details:
1. What: the netcdf tables are created by the schema task.
2. How: `task_ensure_schema` calls `create_netcdf_tables.create_tables()`, which is idempotent.
3. Why: `3b_upload_netcdf_postgres` failed with `relation "netcdf_files" does not exist`, which marked every run `failed`.
4. Effect: on the server the three netcdf tables now exist, created by hand on 2026-09-25 with the same function (run twice).
   Confirmed 2026-09-29: `3b_upload_netcdf_postgres` succeeded in a real cycle (`scheduled__2026-09-29T09:15:00+00:00`), and every other run since has too.
