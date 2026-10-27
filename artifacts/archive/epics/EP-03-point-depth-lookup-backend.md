---
date_drafted: 2026-09-23
type: user-story
us_ids: ["US-011", "US-012", "US-013", "US-014", "US-015", "US-016", "US-056"]
status: draft
subsystem: architecture-backend
source_ideas: []
related: ["[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[graphhopper-backend]]"]
tags: [user-story, epic, backend, sprint-1, sprint-2]
---

# Epic: point-depth lookup backend

Builds `GET /flood/points`, the endpoint [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] scopes narrowly for
raster-backed point-depth lookup. Rows carry Priority, Estimate, and Sprint in addition to the
standard Epic fields, per this vault's user-story sprint-delegation convention (see
`.claude/CLAUDE.md`, "User stories and sprint planning").

- [[US-011-regression-harden-floodmap-backend-before-adding-new|US-011]] Regression-harden `floodmap-backend` before adding new load. Story 1.
- [[US-012-load-depth-tif-into-postgis-as-a|US-012]] Load `depth.tif` into PostGIS as a raster. Story 2.
- [[US-013-build-get-flood-points|US-013]] Build `GET /flood/points`. Story 3.
- [[US-014-validate-get-flood-points-s-latency-under|US-014]] Validate `GET /flood/points`'s latency under concurrent taps. Story 4.
- [[US-015-handle-a-full-connection-pool-in-floodmap|US-015]] Handle a full connection pool in `floodmap-backend`. Story 5.
- [[US-016-make-test-server-py-s-tile-edge|US-016]] Make test_server.py's tile-edge check independent of GDAL's rounding. Story 6.
- [[US-056-reuse-database-connections-in-floodmap-backend|US-056]] Reuse database connections in `floodmap-backend`. Story 7.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-03-point-depth-lookup-backend-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-23, draft.** Drafted from [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]'s Goals, Dependencies
  and assumptions, and Definition of done sections.
- **2026-09-23, draft.** Story 1 done: added `backend/test_flood_areas.py` and
  `backend/test_server.py`, both passing against a real PostGIS and a stub GraphHopper. Story 2
  (raster load) is next.
- **2026-09-29, draft.** Story 4 moved from Sprint 2 to the start of Sprint 3, after the connection-reuse fix. See
  [[SP-01-prd-and-backlog|sprint-plan]].
- **2026-09-30, draft.** Added Story 5 (a full connection pool) to Sprint 2 as `Reviewed`. Story 4's numbers stop
  at 10 concurrent requests. A live run at 30 concurrent found HTTP 400 `connection pool exhausted`. The fix waits for a
  free connection and answers 503 after 5 seconds. It is deployed to the server and measured at 30 and 60 concurrent
  requests, all 200.
- **2026-09-30, draft.** Story 6 added for [[BL-019-test-server-tile-edge-check-fails|test-server-tile-edge-check-fails]]. It blocks no later build, so a subagent fixes it while the next work continues (rule 11).
- **2026-09-30, draft.** Story 7 (US-056) added to give the Sprint 2 row "Reuse database connections" a story. It is `Done`: the work shipped on 2026-09-29.

