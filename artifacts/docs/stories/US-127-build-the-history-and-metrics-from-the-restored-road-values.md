---
date_drafted: 2026-10-12
type: user-story
us_id: "US-127"
title: "Build the history and metrics from the restored road values"
epic: "[[EP-22-keep-a-real-storm-as-the-test-dataset]]"
status: Done
kind: story
priority: P2
estimate: M
sprint: 
subsystem: testing, flood-data
source_ideas: []
related: ["[[test-dataset]]", "[[decision-log|D-039]]"]
tags: [user-story]
---

# US-127 Build the history and metrics from the restored road values

As a developer, I want the depth history and the flood metrics of the storm built into the test databases from the restored road values, so every consumer of the pipeline output has real data.

The edge depth files and the road values are in the snapshot.
The script loads `depth_history` and `history_moment` with `load_run` of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]], and runs `extract_run` for `flood_segment_metrics`.
It then measures the compression ratio of `depth_history` on the full storm, which answers the open item of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]].

Given the 58 runs loaded, then `history_moment` has the moments of the storm and `hypertable_compression_stats` gives a ratio, which the story records.

Dependencies: [[US-125-restore-the-snapshot-into-test-databases|US-125]] is `Done`, because the road values come from the snapshot and no raster tiles are needed, and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] is `Done`.

## Status history

- **2026-10-12, draft.** Raised with [[decision-log|D-039]].

- **2026-10-12, In progress.** Started on the owner's request, outside the sprint plan, so it has no `sprint`. [[US-125-restore-the-snapshot-into-test-databases|US-125]] and [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] are `Reviewed` and not `Done`, and the owner agreed to build against them. At most two stories were `In progress` ([[US-118-write-the-edge-depth-to-a-queryable-table|US-118]] and this one).
- **2026-10-12, Reviewed.** Built, tested, and run on the server (details item 1 to 6). Its `Done` waits for the `Done` of US-125 and US-106, a server screenshot, and the owner's acceptance.

- **2026-10-12, Done.** The product owner accepted it. The terminal screenshot was not saved before the acceptance, so the evidence is the captured output of the two server runs (`us-127-server-check-output.txt`). The screenshot was saved later the same day (`us-127-server-check-output.png`).

## Evidence and details

**Evidence:** `artifacts/docs/stories/evidence/us-127-server-check-output.png`, a screenshot of a read-only check of the server on 2026-10-12 17:35 +07 (the script is `marie-curie/us-125-127/us127.sh`), and `us-127-server-check-output.txt`, the output of the two build runs. The screenshot shows 219,174 rows and 65 moments in `depth_history` and `history_moment`, the compression ratio of 9.7, 786,956 metric rows over 58 runs, and the unchanged production counts.

**Details:**

1. `scripts/testdata/build_history_and_metrics.py` reads the runs of `flood_road_file` in `minio_custom_test`, oldest first. For each run it calls `load_run.write_run` into `flood_metrics_test` and `extract_run.extract_run` into `minio_custom_test`, then compresses every chunk of `depth_history` and prints the ratio. It decompresses first, so a second run gives the same rows. It refuses a database whose name does not end in `_test`.
2. `load_run.read_run` took the moments of a run from `flood_depth_raster_tile`, which the test databases do not hold (the owner decided that no raster tile is restored). It now reads them from `flood_road_file.forecast_times`, which every run has, wet or dry ([[US-116-let-a-run-with-no-wet-road-piece-win-the-winner-query|US-116]]). The production read of run `20261011T001500` is the same as before: 8 moments and 19,792 rows. The change also lets [[US-113-backfill-per-segment-depth-history|US-113]] load runs older than the newest 8, which the tile table no longer holds.
3. The tests: `test_load_run.py` has 10 unit tests and 5 against a real TimescaleDB, and all pass, with `test_create_timescale_tables.py` (18 in all). The unit tests now give `build_slice` the forecast times in Vietnam local time and check the run without forecast times and the row at an uncovered time.
4. Result, 58 runs loaded: `depth_history` holds 219,174 rows and `history_moment` 65 moments (58 runs at 15 minutes plus the 7 later steps of the last run). `flood_segment_metrics` holds 786,956 rows over 58 runs. The first run took 2 min 12 s, the second 1 min 46 s, with the same counts.
5. Compression of `depth_history` on the full storm: one chunk of 36 MB (23 MB table, 13 MB indexes) goes to 3,840 kB, a ratio of 9.7. The first run printed 12.0, because 58 cycles of delete and insert had left dead space in the chunk, and 47.3 MB before compression is the inflated size. The compressed size is the same in both runs, 3,932,160 bytes. The estimate of [[decision-log|D-028]] and [[decision-log|D-032]] is 10, and the sample of [[US-106-keep-per-segment-depth-history-in-timescaledb|US-106]] with one run gave 1.7, which was a sample with too few rows per segment. With 219,174 rows the ratio is 9.7, so D-028's trigger (far below 10) is not met. The data has 8 steps of one storm, so a longer record can still differ.
6. Production did not change: `depth_history` in `flood_metrics` still has 19,792 rows, and `flood_segment_metrics` in `minio_custom` has 23,324 rows (the two runs of the live pipeline).
