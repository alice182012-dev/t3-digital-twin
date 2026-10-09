---
date_drafted: 2026-09-23
type: user-story
us_id: "US-013"
story_label: "3"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: M
sprint: 2
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Build `GET /flood/points`"
---

# US-013 Build `GET /flood/points`

As a frontend developer, I want an endpoint that returns the exact depth at an arbitrary lat/lon
and timestep, so I can source the place-depth popup and per-point depth figures from a single
source of truth instead of a road-segment or banded-polygon approximation.
Given a completed run with `depth.tif` loaded for at least one `valid_time`, when
`GET /flood/points?lat=&lon=&valid_time=` is called for a point inside the flooded extent, then
the response's depth value matches the value read directly from `depth.tif` at that pixel with
`gdallocationinfo`, for one spot-checked point.
Dependencies: Story 1, Story 2.
Evidence: ![[flood-points-endpoint.png|420]]
Details:
1. What: `GET /flood/points` returns the depth at a lat/lon and timestep.
2. How: `flood_points.py` reads `flood_depth_raster` with `ST_Value`. A pixel of 0 reads `dry`, and a point outside the raster reads `no_data`.
3. Why: the popup and badges need the exact pixel, not a band.
4. Effect: unblocks the latency check and the three Sprint 3 point stories. Without `run=`, it returns 404 when the newest run has no raster. On a real `depth.tif`, it matched `gdallocationinfo` at three points.
