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

Story-level progress lines up to 2026-10-10 are in [[EP-04-timescaledb-and-flood-metrics-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-23, draft.** Drafted from [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]'s Goals and Definition
  of done sections, after the fast-track trigger, Redis, and citizen and dashboard endpoint goals
  were descoped from that PRD.
- **2026-09-29, draft.** Stories 3 and 4 moved from Sprint 2 to Sprint 4 in [[SP-01-prd-and-backlog|sprint-plan]]: no frontend story waits on them, so the point-depth work goes first.
- **2026-09-30, draft.** Story 5 (`US-060`) added to Sprint 4: run the extractor on a retained run. Story 3 (`US-020`) had never run on real data, and the sprint goal needs it. Retained runs exist on the server.
- **2026-10-01, done.** Story 4 (`US-021`) is `Dropped`: the user said the pipeline no longer runs `background_cycle`, and the story's acceptance check needs it (D-009 in [[decision-log]]). The ID is not reused. Story 1 (`US-018`) stays `Done`, since the schema was built. Its `background_cycle` enum value, `background_forecast_depth` table, and bars 7 to 24 CHECK stay in the database and stay unused. Every other story of this epic is `Done`, so the epic is `done`.
