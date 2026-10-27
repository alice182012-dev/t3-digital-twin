---
date_drafted: 2026-09-23
type: user-story
us_id: "US-019"
story_label: "2"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P1
estimate: S
sprint: 1
subsystem: architecture-backend
related: ["[[EP-04-timescaledb-and-flood-metrics]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Stand up the TimescaleDB service"
---

# US-019 Stand up the TimescaleDB service

As an engineer, I want TimescaleDB running as its own Docker service, distinct from `storage-postgres`, so the metric extractor and population job have somewhere to write.
Given the schema design from Story 1, when the service is added to `compose.yml` and deployed on the remote host, then it starts cleanly and accepts the designed schema's tables.
Dependencies: Story 1 (schema informs what the service needs to support, though standing up the service itself has no hard technical blocker).
Evidence: ![[timescaledb-service.png|420]]
Details:
1. What: a `timescaledb` container apart from `storage-postgres`.
2. How: `compose.yml`, image `timescale/timescaledb:2.30.1-pg17`, bound to `127.0.0.1:5434`.
3. Why: the extractor's output needs a time-series store.
4. Effect: `compose.yml` requires `TIMESCALE_PASSWORD`, so every compose command fails without it.
   The image comes from Docker Hub.
