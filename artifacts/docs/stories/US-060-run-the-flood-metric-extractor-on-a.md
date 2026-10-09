---
date_drafted: 2026-09-23
type: user-story
us_id: "US-060"
story_label: "5"
epic: "[[EP-04-timescaledb-and-flood-metrics]]"
status: Done
priority: P1
estimate: XS
sprint: 4
subsystem: architecture-backend
related: ["[[EP-04-timescaledb-and-flood-metrics]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
---

# US-060 Run the flood metric extractor on a retained run

As the owner of Sprint 4's goal, I want the extractor (Story 3, `US-020`) run against a real run, so the
metrics are proven on real depth series before Story 4 loads them on a schedule.
Given a retained run in `flood_road_values` on the server, for example `timestamp` 2026-09-30 02:00:00 (46,648
rows, forecast times 02:00 to 03:45), when `scripts/flood_metrics/extract_run.py` runs with that run's
timestamp, then `flood_segment_metrics` holds one row per segment and vehicle type for that run, the segment
count equals the number of distinct `geom_4326` values of the run, and for three segments chosen by hand the
stored `peak_depth_m` equals the largest `depth` of the segment in `flood_road_values`.
On 2026-09-30 the server held retained runs from 2026-09-29 15:00 to 16:30 and 2026-09-30 01:30 to 02:00, so the
data exists today. `flood_mapping_full` is paused, so no new run arrives until it is unpaused. This story needs
none. Story 4's scheduled load does need the DAG unpaused, and that stays with Story 4.
Priority: P1. Status: Done. Estimate: XS. Sprint: 4 (added 2026-09-30). Dependencies: Story 3 (built, `Reviewed`),
Story 2 (`US-019`, the TimescaleDB service). Story 3 moves to `Done` with this story's evidence.
Test points: no coordinate is involved.
Evidence: ![[us-060-extractor-check-output.png|700]]
Details:
1. What: the extractor ran on the retained run 2026-09-30 02:00:00 (46,648 rows).
2. How: `extract_run.py 20260930T020000` inside `airflow_new-airflow-worker-1`, then `evidence/us-060-extractor-check.sh` compared the stored rows with `flood_road_values`.
3. Why: to prove the metrics on a real depth series before Story 4 loads them on a schedule.
4. Effect: 5,831 segments stored, equal to the run's 5,831 distinct `geom_4326` values, with 4 vehicle types and 23,324 rows. `peak_depth_m` equals the largest `depth` for three hand-picked segments (7.147252 m on `way/952973245`, 0.199990 m on Ngõ 153 Phố Phú Đô, 0.000016 m on Đại lộ Thăng Long) and for all 5,831. Story 3 is `Done` with this evidence. Story 4's scheduled load still needs `flood_mapping_full` unpaused. The output was captured from the Mac (`gods-macbook.local`) against the server's containers at 100.67.84.55.
