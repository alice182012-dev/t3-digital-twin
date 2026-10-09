---
date_drafted: 2026-09-23
type: user-story
us_id: "US-021"
story_label: "4"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Not started
priority: P1
estimate: M
sprint: 
subsystem: architecture-backend
related: ["[[EP-04-timescaledb-and-flood-metrics]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Populate TimescaleDB from the extractor's output"
---

# US-021 Populate TimescaleDB from the extractor's output

As a downstream consumer, I want the metric extractor's output loaded into TimescaleDB's
histogram tables, so a day's worth of `constant_cycle` and `background_cycle` data is queryable
as a time series.
Given TimescaleDB populated with at least one full day of `constant_cycle` and `background_cycle`
output for an institution, when its histogram table is queried directly for that institution's 24
hourly bars, then bars 1 through 6 return `constant_cycle` data and bars 7 through 24 return
`background_cycle` data, per the architecture doc's §4.9 split. No serving endpoint exists yet.
this checks the stored data directly.
Priority: P1. Status: Dropped (2026-10-01, D-009 in [[decision-log]]). Estimate: M. Sprint: 4 (re-cut 2026-09-29). Dependencies: Story 2, Story 3, [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Story 1 (the `segment_id`), and
[[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]].
