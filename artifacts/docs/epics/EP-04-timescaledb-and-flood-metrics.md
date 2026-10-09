---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-018", "US-019", "US-020", "US-021", "US-060"]
status: done
subsystem: architecture-backend
source_ideas: []
related: ["[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[minio-flood-extent-pipeline]]", "[[BL-003-airflow-cannot-import-flood-utils|airflow-cannot-import-flood-utils]]"]
tags: [user-story, epic, backend, sprint-1, sprint-2]
---

# Epic: TimescaleDB and flood metrics

Builds the flood metric extractor and TimescaleDB, the two goals
[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] keeps in scope after descoping the fast-track trigger, Redis,
and the citizen and council dashboard endpoints. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention (see `.claude/CLAUDE.md`, "User stories and sprint
planning").

- [[US-018-design-timescaledb-s-histogram-and-forecast-series|US-018]] Design TimescaleDB's histogram and forecast-series schema. Story 1.
- [[US-019-stand-up-the-timescaledb-service|US-019]] Stand up the TimescaleDB service. Story 2.
- [[US-020-build-the-flood-metric-extractor|US-020]] Build the flood metric extractor. Story 3.
- [[US-021-populate-timescaledb-from-the-extractor-s-output|US-021]] Populate TimescaleDB from the extractor's output. Story 4.
- [[US-060-run-the-flood-metric-extractor-on-a|US-060]] Run the flood metric extractor on a retained run. Story 5.

## Status history

- **2026-09-23, draft.** Drafted from [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]'s Goals and Definition
  of done sections, after the fast-track trigger, Redis, and citizen and dashboard endpoint goals
  were descoped from that PRD.
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
- **2026-09-29, draft.** Stories 3 and 4 moved from Sprint 2 to Sprint 4 in [[SP-01-prd-and-backlog|sprint-plan]]: no frontend story waits on them, so the point-depth work goes first.
- **2026-09-30, draft.** Story 5 (`US-060`) added to Sprint 4: run the extractor on a retained run. Story 3 (`US-020`) had never run on real data, and the sprint goal needs it. Retained runs exist on the server.
- **2026-10-01, draft.** Stories 5 and 3 (`US-060`, `US-020`) are `Done`: the extractor ran on the 2026-09-30 02:00:00 run in the Airflow worker, and all 5,831 segments match `flood_road_values`. Output rendered as `us-060-extractor-check-output.png`. Story 4 (`US-021`) can switch the row key to `segment_id`, which maps 1 to 1 to the geometry for this run.
- **2026-10-01, draft.** Story 4 (`US-021`) is `Blocked`. Its acceptance check needs `background_cycle` output and an institution, and neither exists: no DAG runs a `background_cycle` forecast, and no institutions table or list exists. The extractor's rows are per-segment summaries, not hourly bars. Options and a recommendation (load per-segment `depth_history` from `flood_road_values` first) are in [[BL-020-timescaledb-load-has-no-source-for-histogram-bars|timescaledb-load-has-no-source-for-histogram-bars]]. The user decides the scope.
- **2026-10-01, done.** Story 4 (`US-021`) is `Dropped`: the user said the pipeline no longer runs `background_cycle`, and the story's acceptance check needs it (D-009 in [[decision-log]]). The ID is not reused. Story 1 (`US-018`) stays `Done`, since the schema was built. Its `background_cycle` enum value, `background_forecast_depth` table, and bars 7 to 24 CHECK stay in the database and stay unused. Every other story of this epic is `Done`, so the epic is `done`.
