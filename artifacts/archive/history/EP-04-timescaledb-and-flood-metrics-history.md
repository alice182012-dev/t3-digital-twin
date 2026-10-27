---
date: 2026-10-10
type: archive
status: archived
tags: [archive, history]
related: ["[[EP-04-timescaledb-and-flood-metrics]]"]
---

# EP-04-timescaledb-and-flood-metrics: archived story-level history

Lines moved out of the Status history of [[EP-04-timescaledb-and-flood-metrics]] on 2026-10-10 under the rule "Write each fact once". Each fact is also in its story file. Not read in normal sessions.

- **2026-09-23, draft.** Stories 1 and 2 built and reviewed, pushed in commits `f663dba` and
  `d7a2d78`. Status is `Reviewed`, not `Done`, because the schema has not yet applied against a real
  TimescaleDB container on the remote host. That check is the acceptance criterion for both stories.
- **2026-09-23, draft.** Story 3 built and reviewed on branch `worktree-agent-a77ab581261ff0349`
  (commits `4d81d59`, `cdada59`, `b229926`). The pure extractor passes 19 tests. On the real
  `flood_road` sample, one segment matches a hand computation. Status is `Reviewed`, not `Done`,
  because the loader and writer SQL has never run against Postgres, and the check from raster to
  segment has not run.
- **2026-09-23, draft.** The extractor cannot run inside Airflow until `flood_utils.py` is
  importable there. Tracked as [[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]]. It blocks Story 4's DAG
  wiring, not Story 3's own status.
- **2026-09-24, draft.** Stories 1 and 2 done. On the remote host, the `timescaledb` container is
  healthy on TimescaleDB 2.30.1, the schema script's SQL ran twice with no errors and left three
  hypertables and three tables, and `bar_index_matches_cycle` rejected bar 7 for `constant_cycle`.
  Story 3 stays `Reviewed`: the extractor's loader and writer have not run against a real run, and
  [[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]] blocks running it in Airflow.
- **2026-09-24, draft.** The extractor's row key will change from `md5(ST_AsEWKB(geom_4326))` to the
  `segment_id` of the `road_segment` table ([[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Story 1). Story 3 is
  `Reviewed` with the old key, and its `flood_segment_metrics` rows on the server must be rebuilt after
  the change. Story 4 waits for the new key and for [[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]].
- **2026-10-01, draft.** Stories 5 and 3 (`US-060`, `US-020`) are `Done`: the extractor ran on the 2026-09-30 02:00:00 run in the Airflow worker, and all 5,831 segments match `flood_road_values`. Output rendered as `us-060-extractor-check-output.png`. Story 4 (`US-021`) can switch the row key to `segment_id`, which maps 1 to 1 to the geometry for this run.
- **2026-10-01, draft.** Story 4 (`US-021`) is `Blocked`. Its acceptance check needs `background_cycle` output and an institution, and neither exists: no DAG runs a `background_cycle` forecast, and no institutions table or list exists. The extractor's rows are per-segment summaries, not hourly bars. Options and a recommendation (load per-segment `depth_history` from `flood_road_values` first) are in [[BL-020-timescaledb-load-has-no-source-for-histogram-bars|timescaledb-load-has-no-source-for-histogram-bars]]. The user decides the scope.
