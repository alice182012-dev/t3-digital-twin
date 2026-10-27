---
date_drafted: 2026-10-12
type: epic
epic_id: "EP-22"
theme: test dataset
status: active
subsystem: testing, flood-data, airflow-pipeline
tags: [epic]
related: ["[[test-dataset]]", "[[decision-log|D-039]]", "[[US-102-replay-the-storm-with-the-us-101-fix-to|US-102]]"]
---

# EP-22 Keep a real storm as the test dataset

## Goal

The team tests every stage of the pipeline against one real storm, kept in its own folder and its own databases, so a test never depends on a run that the pipeline prunes.
The test dataset is the 58 runs of the storm replay of 2026-10-10.

## Why

The pipeline deletes `results_3di.nc` and the depth rasters after 24 hours, and it prunes `flood_road_values` and the tiles after 24 hours and 8 runs.
Rana keeps a result for one month, and a replay costs 3Di time.
Tests so far ran on small synthetic fixtures or a throwaway PostGIS, so they did not meet a real storm.
The decision is [[decision-log|D-039]], and the layout is in [[test-dataset]].

## Dependencies and assumptions

- The production retention does not change ([[decision-log|D-039]]).
- `results_3di.nc` is the source of truth, and everything else can be rebuilt from it by the pipeline functions.
- The test databases are other databases on the same two servers, `storage-postgres` and `timescaledb`, with the same versions and extensions as production.

## Definition of done

Given an empty test database, when the restore script runs, then each table has the row count of the snapshot manifest.
Given a missing derived table, when the rebuild script runs on the NetCDF files, then its rows equal the snapshot rows where both exist.
Given the test command, when it runs on the Mac, then the suites that need a database use the test database and leave the production databases unchanged.

## Risks and open questions

- The storm dataset is 2.1 GB on disk, and the restored test database adds several GB to the Docker disk on C:, which filled before ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).
  Check `docker system df` before the first restore.
- The results of the storm stay on Rana until about 2026-11-09 as a second copy.

## Stories

```dataview
TABLE title AS "Story", kind AS "Kind", sprint AS "Sprint", priority AS "Priority", estimate AS "Estimate", status AS "Status"
FROM "docs/stories"
WHERE contains(string(epic), "EP-22")
SORT file.name ASC
```

## Status history

- **2026-10-12, active.** Raised after the owner asked for a designated test dataset from the 12-hour storm run. [[US-124-save-the-storm-replay-results-and-derived-data|US-124]] is built, and [[US-125-restore-the-snapshot-into-test-databases|US-125]] to [[US-128-run-the-test-suites-against-the-test-databases|US-128]] are in the backlog.
