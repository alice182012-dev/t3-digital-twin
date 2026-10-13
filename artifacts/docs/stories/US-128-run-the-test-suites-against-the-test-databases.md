---
date_drafted: 2026-10-12
type: user-story
us_id: "US-128"
title: "Run the test suites against the test databases"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Done
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
- **2026-10-13, Reviewed.** Built and run on the server. `python3 scripts/testdata/run_db_tests.py` gave 753 passed, 0 failed, 0 errors, and 8 skipped, and the rows of the restored tables did not change (details items 1 to 4). The owner has not accepted it.
- **2026-10-13, Done.** The product owner accepted it on the written results of details items 1 to 6, with no screenshot.

## Evidence and details

**Evidence:** the output of the command in details item 2. No screenshot.

**Details:**

1. `scripts/testdata/run_db_tests.py` creates one scratch database on `storage-postgres` (with `postgis` and `postgis_raster`) and one on `timescaledb`, named `us128_<token>_pg_test` and `us128_<token>_ts_test`.
   It reaches both servers through an SSH tunnel to ports 5433 and 5434 of the server, and it reads the database user and password from the environment of the worker at run time and never prints them.
   It runs each of 11 folders with `pytest`, prints one table of counts, counts the rows of the restored tables of `minio_custom_test` and `flood_metrics_test` before and after, and drops the scratch databases, also after an error or Control-C.
   It refuses a database name that does not end in `_test`, or that is the admin or a dataset database.
   The suites run against scratch databases and not against the dataset, because about 9 of them create and drop tables in `public` ([[decision-log|D-048]]).
   `--only FOLDER` runs one folder and `--dry-run` prints the plan.
2. Run on 2026-10-13, with the 50-run check of [[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] still running in the worker:

   | Folder | Passed | Failed | Errors | Skipped |
   | --- | --- | --- | --- | --- |
   | `scripts/backend_soak` | 56 | 0 | 0 | 0 |
   | `scripts/database` | 34 | 0 | 0 | 0 |
   | `scripts/edge_depth` | 174 | 0 | 0 | 0 |
   | `scripts/flood_extent` | 50 | 0 | 0 | 0 |
   | `scripts/flood_history` | 16 | 0 | 0 | 0 |
   | `scripts/flood_metrics` | 26 | 0 | 0 | 0 |
   | `scripts/testdata` | 36 | 0 | 0 | 7 |
   | `scripts` (top level) | 93 | 0 | 0 | 0 |
   | `floodmap/graphhopper-flood-road/backend` | 129 | 0 | 0 | 0 |
   | `analysis-service` | 10 | 0 | 0 | 0 |
   | `test` | 129 | 0 | 0 | 1 |
   | Total | 753 | 0 | 0 | 8 |

   The 4 database tests of `backend_soak` skip on the Mac without the command, and they run with it.
   The 7 skips of `scripts/testdata` are `test_restore_snapshot.py`, which needs the snapshot folder that exists only in the worker. The skip of `test` is the version test of [[US-137-make-the-tests-of-test-pass-without-the-pinned-client|US-137]].
3. The rows of the restored tables are equal before and after: `graph_edge_export` 1, `graph_edge` 67,833, `flood_extent_step` 116, `flood_extent_polygon` 812, and `flood_segment_metrics` 786,956 in `minio_custom_test`. `flood_metrics_test` holds none of these tables.
   Both scratch databases were dropped.
4. The first full run found 9 collection errors in `scripts/flood_extent`, `scripts` (7 files), and the backend, because the tests import modules of other folders by bare name. A `pytest.ini` with `pythonpath` fixed them ([[US-137-make-the-tests-of-test-pass-without-the-pinned-client|US-137]], details item 5).
5. The worker sets no `TIMESCALE_USER` and no `TIMESCALE_DB`, because `db_config.py` falls back to `flood_metrics`, so the command applies the same defaults.
6. The command ran after the code of [[US-123-delete-flood-on-roads-and-flood-road-values|US-123]] was on `modular`, so it ran the final suites, and it does not need the server to hold that code.

