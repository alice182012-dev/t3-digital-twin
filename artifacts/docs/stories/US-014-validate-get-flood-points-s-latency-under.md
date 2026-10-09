---
date_drafted: 2026-09-23
type: user-story
us_id: "US-014"
story_label: "4"
epic: "[[EP-03-point-depth-lookup-backend]]"
status: Done
priority: P0
estimate: S
sprint: 2
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Validate `GET /flood/points`'s latency under concurrent taps"
---

# US-014 Validate `GET /flood/points`'s latency under concurrent taps

As an engineer, I want to know whether a live `ST_Value` query holds up under concurrent popup
taps, so I can decide before Sprint 3 whether the frontend can call this endpoint directly or
needs a pre-computed lookup grid instead.
Given the raster table loaded, when concurrent `ST_Value` queries run at a rate matching expected
popup-tap traffic, then response times land within the same interactive latency budget the
existing `GET /flood/areas` call already meets.
Priority: P0. Status: Done. Estimate: S. Sprint: 2 (re-cut 2026-09-29). Dependencies: Story 3,
and the connection-reuse item in [[BL-007-flood-points-connection-per-request|flood-points-connection-per-request]], which lands first.
Evidence: ![[connection-pooling-and-forecast-verification.png|420]]
Details:
1. What: measured `GET /flood/points` latency on the live server, sequential and concurrent, with
   the pooled-connection `db.py` deployed.
2. How: 30 sequential requests, then 20 requests at 5 concurrent and 40 at 10 concurrent, against
   a real wet point on run `20260929T163000`, matching the original blocker measurement's shape.
3. Why: this is the acceptance check the connection-reuse fix needed before it could close.
4. Effect: sequential median dropped from 80.7 ms to 4.6 ms (about 17x). At 5 concurrent, median
   dropped from 99.4 ms to 39.6 ms. At 10 concurrent (the pool's own `FLOOD_DB_POOL_MAX` ceiling),
   median dropped more modestly, from 126.8 ms to 103.3 ms, since all 10 pooled connections are in
   use at once; raising `FLOOD_DB_POOL_MAX` would widen that ceiling if production sees sustained
   10-way concurrency. No errors at any level tested. `GET /flood/areas`'s own interactive budget
   (not separately re-measured here) is the comparison target the acceptance criteria name; the
   new sequential number is well inside any plausible interactive budget.
