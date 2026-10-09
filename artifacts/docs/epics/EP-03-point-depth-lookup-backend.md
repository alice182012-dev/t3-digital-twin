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

- **2026-09-23, draft.** Drafted from [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]'s Goals, Dependencies
  and assumptions, and Definition of done sections.
- **2026-09-23, draft.** Story 1 done: added `backend/test_flood_areas.py` and
  `backend/test_server.py`, both passing against a real PostGIS and a stub GraphHopper. Story 2
  (raster load) is next.
- **2026-09-23, draft.** Story 2 done in commit `118e04a`: the `flood_depth_raster` table and the
  `9b_load_depth_raster` task. Story 3 (`GET /flood/points`) is next.
- **2026-09-23, draft.** Story 3 built and reviewed on branch `worktree-agent-af5d6b004a774583a`
  (commits `80c6843` and `e3a0a95`). `GET /flood/points` returns `wet`, `dry`, or `no_data`. Its
  tests pass against a local PostGIS, and the wet case matches `gdallocationinfo` on a synthetic
  `depth.tif` to float32 precision. Status is `Reviewed`, not `Done`, because the acceptance check
  names a real `depth.tif`, and none has run against the real `storage-postgres`.
- **2026-09-24, draft.** Story 3 done. On the remote host, `GET /flood/points` matched
  `gdallocationinfo` on a real `depth.tif` (`depth_20260924_170639.tif`, run `20260924T153638`) at
  three points: 6.812467575073242 against 6.81246757507324, 0.17372192442417145 against
  0.173721924424171, and 0.0 against 0. A point outside the raster returned `no_data`, an unknown
  `valid_time` returned 404, and a latitude of 95 returned 400. `storage-postgres` runs in
  `Etc/UTC`, so the timestamp handling holds. Story 4 (latency) is next.
- **2026-09-24, draft.** Story 4's baseline changed. `GET /flood/points` now reads tiles
  ([[EP-06-raster-first-pipeline|raster-first-pipeline-stories]] Story 2): 0.2 ms per lookup locally, but about 58 ms per request
  because each new connection loads the raster library. Measure on the server, with and without
  connection reuse.
- **2026-09-24, draft.** The connection cost is tracked as [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]].
- **2026-09-24, draft.** Stories 2 and 3 name `flood_depth_raster`, the table they shipped with.
  Both paths now use `flood_depth_raster_tile` instead, and `create_flood_depth_raster_tables.py`
  no longer creates the old table. The deploy runbook drops it.
- **2026-09-29, draft.** Story 4 moved from Sprint 2 to the start of Sprint 3, after the connection-reuse fix. See
  [[SP-01-prd-and-backlog|sprint-plan]].
- **2026-09-29, draft.** The re-cut of [[SP-01-prd-and-backlog|sprint-plan]] put Story 4 in Sprint 2 after the connection-reuse row, so Sprint 3's per-step
  depth and depth badges start on a measured endpoint.
- **2026-09-29, draft.** Story 4 done. Deployed the pooled `db.py` (built on branch
  `pool-floodmap-backend-connections`) to the live `floodmap-backend` container and measured:
  sequential median 80.7ms to 4.6ms, 5-concurrent median 99.4ms to 39.6ms, 10-concurrent median
  126.8ms to 103.3ms (the pool's own 10-connection ceiling). No errors at any level. See
  [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]], now resolved.
- **2026-09-30, draft.** Added Story 5 (a full connection pool) to Sprint 2 as `Reviewed`. Story 4's numbers stop
  at 10 concurrent requests. A live run at 30 concurrent found HTTP 400 `connection pool exhausted`. The fix waits for a
  free connection and answers 503 after 5 seconds. It is deployed to the server and measured at 30 and 60 concurrent
  requests, all 200.
- **2026-09-30, draft.** Story 5 is `Done`: a fresh run on the server (2026-09-29 17:46 UTC) is saved as
  `pool-wait-and-503-server-check.png`. All requests returned 200 at 30 and 60 concurrent. The live 503 path stays covered by
  the unit test only.
- **2026-09-30, draft.** Story 6 added for [[BL-019-test-server-tile-edge-check-fails|test-server-tile-edge-check-fails]]. It blocks no later build, so a subagent fixes it while the next work continues (rule 11).
- **2026-09-30, draft.** Story 6 is `Done`. A subagent built it, I reviewed the diff and reran the script, and it landed as `03f7aa6`.
- **2026-09-30, draft.** Story 7 (US-056) added to give the Sprint 2 row "Reuse database connections" a story. It is `Done`: the work shipped on 2026-09-29.

