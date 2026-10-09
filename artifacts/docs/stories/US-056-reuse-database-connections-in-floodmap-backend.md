---
date_drafted: 2026-09-23
type: user-story
us_id: "US-056"
story_label: "7"
epic: "[[EP-03-point-depth-lookup-backend]]"
status: Done
priority: P1
estimate: S
sprint: 2
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
---

# US-056 Reuse database connections in `floodmap-backend`

As a user tapping the map, I want `GET /flood/points` to answer without opening a database connection per request,
so many taps stay fast.
Given the backend pools its PostGIS connections, when requests arrive one after another and at once, then the
median latency falls from the per-request connection cost to the lookup cost, with no error at any level tested.
Priority: P1. Status: Done. Estimate: S. Sprint: 2. Dependencies: None. The tiled raster story it needed is deployed.
Recorded on 2026-09-30 from the Sprint 2 row and the blocker [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]]. It began as a `TODOS.md` item and had no story
in an epic file.
Blocker tracking: [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]]
Evidence: ![[connection-pooling-and-forecast-verification.png|420]]
Details:
1. What: `db.py` pools connections with `psycopg2.pool.ThreadedConnectionPool`, and every `server.py` handler borrows one through a `db.connection()` context manager.
2. How: deployed to the live container and measured on the server with the same method as the original blocker measurement.
3. Why: the raster library load (about 57 ms) now happens once per pooled connection instead of once per request.
4. Effect: sequential median 80.7 ms to 4.6 ms, 5 concurrent 99.4 ms to 39.6 ms, 10 concurrent 126.8 ms to 103.3 ms, with no errors. It fed [[EP-03-point-depth-lookup-backend|point-depth-lookup-backend]] Story 4 (US-014), and Story 5 (US-015) fixed the failure past 10 concurrent requests.
