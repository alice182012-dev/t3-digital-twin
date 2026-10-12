---
date_drafted: 2026-10-12
type: user-story
us_id: "US-125"
title: "Restore the snapshot into test databases"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Done
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

- **2026-10-12, In progress.** Started on the owner's request, outside the sprint plan, so it has no `sprint`. [[US-124-save-the-storm-replay-results-and-derived-data|US-124]] is `Reviewed` and not `Done`, and the owner agreed to build against it. At most two stories were `In progress` ([[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and this one).
- **2026-10-12, Reviewed.** Built, tested, and run on the server (details item 1 to 6). Open for `Done`: a server screenshot, the acceptance of US-124, and the owner's acceptance.

- **2026-10-12, Done.** The product owner accepted it. The terminal screenshot was not saved before the acceptance, so the evidence is the captured output of the server run (`us-125-server-check-output.txt`). Save `us-125-server-check-output.png` from a run of the script when convenient.

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/us-125-server-check-output.txt`, the output of the restore on the server on 2026-10-12. There is no screenshot yet.

**Details:**

1. `scripts/testdata/restore_snapshot.py` takes the names from `TEST_POSTGRES_DB` and `TEST_TIMESCALE_DB` (defaults `minio_custom_test` and `flood_metrics_test`). It checks the SHA-256 of each file against `snapshot/MANIFEST.json`, creates the two databases when they do not exist, runs the `SQL` of the DDL scripts of `scripts/database/`, and loads the eight CSV files in `RESTORE_ORDER`. It truncates and loads in one transaction, so a second run gives the same rows and a failed run leaves the old rows. It moves each `id` sequence to the largest restored id.
2. It refuses a database whose name does not end in `_test`, and it counts the eight tables in production before and after, so a restore that touched production is reported. `flood_segment_metrics` has no rows in the snapshot, and the table is empty in the test database.
3. The tests are `scripts/testdata/test_restore_snapshot.py`, 10 tests against a throwaway PostGIS (also in CI, `restore-snapshot-test.yml`). They restore a small snapshot written with `COPY ... CSV HEADER` and compare each row as text, with a NULL, a name with quotes and accents, a geometry, and an array. They also cover the second run, the serial columns, a changed file, a failed load that keeps the old rows, and the guard.
4. Criterion 1, on the server: every table has the row count of the manifest (for example `flood_road_values` 1,573,912 and `flood_extent_polygon` 812). Criterion 2: a second run took 2 min 9 s and gave the same counts. Criterion 3: the production counts of the eight tables were the same before and after both runs.
5. The Docker disk: `docker system df` shows Local Volumes growing from 8.103 GB to 11.64 GB, so the restore adds about 3.5 GB (`minio_custom_test` is 2,628 MB, mostly `flood_extent_polygon` and `flood_road_values`). C: had 100.3 GB free before the restore ([[BL-022-docker-data-vhdx-fills-c-drive-again|BL-022]]).
6. `graph_edge` in the test database has no `edge_key`, because the snapshot of `graph_edge` was written before [[US-117-export-a-stable-key-with-each-graph-edge|US-117]] and has no such column. The edge depth tables are empty too, because the snapshot predates them. [[US-126-rebuild-the-raster-tiles-and-road-values-from-the-netcdf|US-126]] or a later story fills them. A pipeline run with `POSTGRES_DB=minio_custom_test` and `TIMESCALE_DB=flood_metrics_test` reads the test databases (`flood_road_values` 1,573,912 and `depth_history` 0 on 2026-10-12).
