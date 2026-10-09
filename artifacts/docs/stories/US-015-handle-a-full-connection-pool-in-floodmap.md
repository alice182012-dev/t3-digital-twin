---
date_drafted: 2026-09-23
type: user-story
us_id: "US-015"
story_label: "5"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: S
sprint: 2
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Handle a full connection pool in `floodmap-backend`"
---

# US-015 Handle a full connection pool in `floodmap-backend`

As a person checking flood depth while many others use the app, I want a burst of simultaneous
requests to slow down instead of fail, so the depth popup still answers.
Given the pool is at its ceiling of 10 connections (`FLOOD_DB_POOL_MAX`), when 30 concurrent
`GET /flood/points` requests arrive, then each request returns 200, or returns 503 with a
`Retry-After` header after the wait limit passes. None returns 400.
Given a pooled connection whose database session has died, when its request ends, then the pool
discards that connection and the slot is free for the next request.
Priority: P0. Status: Done. Estimate: S. Sprint: 2. Dependencies: Story 4, and the pooling
change from [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]].
Evidence: ![[pool-wait-and-503-server-check.png|420]]
Details:
1. What: a full pool makes a request wait for a free connection for up to 5 seconds
   (`FLOOD_DB_POOL_WAIT`), then answer 503 with `Retry-After: 1`. A connection whose rollback fails
   is closed and its slot returned.
2. How: `db.connection()` takes a semaphore sized to `FLOOD_DB_POOL_MAX` before it calls
   `getconn()`, and raises `db.PoolTimeout` when the wait runs out. `server.py` maps `PoolTimeout`
   to 503. Tests are in `backend/test_db.py`, committed before the fix.
3. Why: on 2026-09-29, 30 concurrent requests against the live backend returned HTTP 400
   `connection pool exhausted` on about half of the requests, in three runs. Story 4's measurement
   stopped at 10 concurrent requests, so it did not reach the pool ceiling.
4. Effect: deployed to the server by copying the branch's `backend` folder and rebuilding
   `floodmap-backend`. Measured there at 2026-09-30 00:36 (+07:00). At 30 concurrent, three runs of 90
   requests all returned 200, with medians of 152, 215, and 158 ms and p95 of 296, 364, and 270 ms.
   At 60 concurrent, 180 requests returned 200 (median 345 ms). A warm sequential request takes 2.3 ms.
   The 503 path and the dead-connection case have only unit tests, because no live run reached the
   5 second wait. The screenshot is a fresh run at 2026-09-29 17:46 UTC on host ADMIN, with the same
   result: no 400 at 30 or 60 concurrent requests.
