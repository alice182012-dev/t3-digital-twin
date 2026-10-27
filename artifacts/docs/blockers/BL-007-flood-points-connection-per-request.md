---
date_open: 2026-09-24
date_closed: 2026-09-29
type: blocker
status: resolved
severity: P2
subsystem: floodmap-backend
approaches_tried: 1
approaches_remaining: 1
tags: [blocker, postgis, latency, floodmap-backend]
related: ["[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]", "[[EP-06-raster-first-pipeline|raster-first-pipeline-stories]]", "[[graphhopper-backend]]", "[[minio-flood-extent-pipeline]]"]
last_updated: 2026-09-29
---

# GET /flood/points spends most of its time opening a connection

## Description

The tiled raster lookup itself takes 0.2 ms warm, but a full `GET /flood/points` request still takes
about 58 ms. The rest is connection setup.

`floodmap/graphhopper-flood-road/backend/server.py` calls `get_connection()` in every handler.
`db.py` implements that as `psycopg2.connect(**DB_CONFIG)`, so each request opens a new connection.
The first raster call in a new PostgreSQL session loads the PostGIS raster library. The tiled-raster
delegate measured this on a laptop with PostGIS 3.6.4 on PostgreSQL 18:

| | Warm lookup | Full request, new connection |
| --- | --- | --- |
| Old whole raster | 69.3 ms | 149.5 ms |
| New tiles | 0.20 ms | 58.2 ms |

Loading the raster library took 57.3 ms in a new session, against 1.4 ms for a plain connect.

The server shows the same shape (measured 2026-09-24 from inside the `floodmap-backend` container, run
`20260924T153638`, four timesteps loaded):

| | Median | Slowest |
| --- | --- | --- |
| Tile lookup in the database | 0.56 ms | 84.5 ms (the first call in a session) |
| Full request, 30 sequential | 80.7 ms | 96.2 ms |
| Full request, 5 at once (20 requests) | 99.4 ms | 111.5 ms |
| Full request, 10 at once (40 requests) | 126.8 ms | 145.1 ms |

The lookup is about 0.5 ms and the request is about 80 ms, so nearly all of the time is connection
setup and the first-call library load.

## Why this matters

[[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]]'s Story 4 asks whether the endpoint meets the same interactive latency
budget as `GET /flood/areas`. The frontend's place-depth popup, per-step depth, and per-point badges
in Sprint 3 all call this endpoint, and a route with many points calls it many times. At 58 ms per
request, the tile work is already fast, and the connection is now almost the whole cost.

## Approaches tried

1. Pool the connections (2026-09-29). `db.py`'s `get_connection()` replaced with a
   `psycopg2.pool.ThreadedConnectionPool` (`FLOOD_DB_POOL_MIN`/`FLOOD_DB_POOL_MAX`, default 1/10)
   behind a `db.connection()` context manager, rolled back on release. Built, deployed to the live
   `floodmap-backend` container, and measured on the server: worked, see Status history.

## Decision and explanation

Done: pooling (candidate 1). Candidate 2 (thread-local) wasn't needed; pooling resolved the
blocker on the first measurement.

1. ~~Pool the connections.~~ Built and deployed 2026-09-29, resolved.
2. Keep one connection per handler thread (thread-local). Not needed.

## Concerns

A pooled connection must be reset between requests (roll back any open transaction), or a failed
request can leave the next one in an aborted transaction. The pool size must stay under
`storage-postgres`'s connection limit, shared with Airflow and the storage backend.

## Related topics

- [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]], Story 4
- [[EP-06-raster-first-pipeline|raster-first-pipeline-stories]], Story 2
- [[graphhopper-backend]], `GET /flood/points`

## Status history

- **2026-09-24, open.** Logged at the user's request from the tiled-raster delegate's report. The
  per-request connection is confirmed in `server.py` and `db.py`. The 57 ms cost is a laptop
  measurement.
- **2026-09-24, open.** Measured on the server after the Stage A deploy: the 0.56 ms lookup sits inside an
  81 ms request. The fix (a pool in `db.py`) is still untried.
- **2026-09-29, open.** Scheduled as the first row of Sprint 3 in [[SP-01-prd-and-backlog|sprint-plan]], ahead of the `GET /flood/points`
  latency check. Per-step depth and depth badges call the endpoint once per point, so each new connection
  (about 58 ms) adds up. Still untried.
- **2026-09-29, open.** The re-cut of [[SP-01-prd-and-backlog|sprint-plan]] moved this to Sprint 2, ahead of the latency check and Sprint 3's per-step depth.
- **2026-09-29, resolved.** Built the pooling fix, rebuilt and redeployed `floodmap-backend` on the
  server, and measured with the same methodology as the original numbers above (30 sequential, 5 at
  once/20 requests, 10 at once/40 requests), against the same endpoint. Sequential median 80.7ms to
  4.6ms (about 17x). 5-concurrent median 99.4ms to 39.6ms. 10-concurrent median 126.8ms to 103.3ms,
  a smaller gain because 10 concurrent requests hits `FLOOD_DB_POOL_MAX`'s default ceiling of 10, not
  a regression; raise the env var if sustained 10-way concurrency shows up in production. No errors
  at any level. Closes this blocker and [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 4.
