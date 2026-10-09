---
date_drafted: 2026-09-29
type: user-story
us_id: "US-037"
story_label: "6"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P2
estimate: M
sprint: 4
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Narrow the per-run critical path under the 15-minute cycle (option D)"
---

# US-037 Narrow the per-run critical path under the 15-minute cycle (option D)

As the pipeline owner, I want each run's step-1 tile to publish with real margin before that step
becomes "now" again, so the 1.5 to 3 minute publish delay [[BL-013-flood-mapping-full-worker-concurrency-serializes-runs|flood-mapping-full-worker-concurrency-serializes-runs]]'s
resolution left behind goes away.
Given a run's critical path (trigger ~3.5 min, `3_calculate_depth` ~7 min, raster load ~2.3 min, tile
build ~6 min) sums to about 18.8 minutes against the 15-minute cycle, when the slowest steps are sped up
or given more of the server's headroom, then four consecutive real runs publish step 1 before it becomes
now, with a measured margin, not after.
Dependencies: Story 8 (`US-063`) for the retest. Independent of Sprint 3's
frontend work. Candidate levers, to measure rather than assume: `3_calculate_depth`'s `MAX_WORKERS` is 8,
set when two runs' depth-calc tasks could contend; the `depth_calc` pool now caps that to one at a time,
so there may be headroom to raise it (12 logical cores available per
[[BL-013-flood-mapping-full-worker-concurrency-serializes-runs|flood-mapping-full-worker-concurrency-serializes-runs]]). `9_build_flood_tiles`'s
`FLOOD_EXTENT_WORKERS` is 2 threads, well under the same headroom. Measure CPU and memory use during a
real run before raising either, since depth-calc's subprocess count and tile-build's thread count are
the two knobs, and both share the same box.
Retest: every simulated run of the 48-hour replay of Story 8 publishes step 1 before it becomes now, and the worst margin is recorded. The run count is 192 of 192 at the server's gate of 0.01 mm/h, and 104 at 5 mm/h. The first measurement below used a constant 50 mm/h rain, which the user judged unrealistic.
Evidence of the first measurement: ![[us-037-margins-check-output.png|700]]
Details of the first measurement:
1. What: step 1 of every run is published before it becomes "now". Four consecutive on-time runs (slots 00:45, 01:00, 01:15, and 01:30 +07 on 2026-10-02) had margins of +1.9, +4.1, +2.7, and +2.4 minutes.
2. How: three changes. The 8 depth processes read their inputs from the container's local disk (`depth_inputs.py`, `684262b`, `3e83a7f`), which cut depth from 6.8 to 7.5 to 3.2 to 3.9 minutes. The tile dissolve runs one process per band (`4e793c0`, `1607484`), with identical areas. A run hotstarts only if the previous slot's run is success or running (`eef34aa` to `828446f`), so a restart starts from the initial water level. Each was found by measuring: the depth experiment of 2026-10-01 and a stage profile of the tile build.
3. Why: the map showed a tile 1.5 to 3 minutes after its time ([[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]), and under the growing test storm the tile task reached 15 to 17 minutes, longer than the 15-minute cycle.
4. Effect: the tile task took 4.4 to 6.1 minutes in the four runs, growing about 0.6 minutes per run as the storm grew from a cold start. At that pace the margin reaches zero in about four more runs. The pass holds for the first hour of a storm, not for a storm that has run for hours. The test storm (`FLOOD_TEST_RAIN_MM_HR=50`) is still on. The blocker [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] stays `monitoring`.
Details (re-closed on 137 runs, 2026-10-05):
1. What: closed again on 2026-10-05 at the user's decision, on the 137 runs of the replay, not on `report.py` passing over 192. The earlier evidence covers four runs only.
2. How: an analysis of the 136 completed runs (critical path from trigger start to tile build end) stayed under the 15-minute budget, with a maximum of 14.9 minutes. `scripts/pipeline_margins/report.py` was not run over the window.
3. Why: the user judged 137 runs enough of a pattern, and wanted to start Sprint 6.
4. Effect: `9_build_flood_tiles` grew 4.8 times over the window (90.9 s to 439.4 s). The lead is the unbounded growth of `flood_extent_polygon`, which `US-067` now prunes, and it is not verified. A later run or the replay now running can show whether the growth is gone. The blocker [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] stays `monitoring`. Flagged for the human to confirm.

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed. It also said: status "Done (re-closed 2026-10-05 on 137 runs, evidence waived by the user)".
