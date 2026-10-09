---
date_drafted: 2026-09-23
type: user-story
us_id: "US-011"
story_label: "1"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P0
estimate: M
sprint: 1
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Regression-harden `floodmap-backend` before adding new load"
---

# US-011 Regression-harden `floodmap-backend` before adding new load

As an engineer, I want `server.py` and `flood_areas.py` covered by a regression or test pass, so
I can add a new endpoint without debugging two unknowns (new code, an unproven backend) at once.
Given the architecture doc's §11 flags `floodmap-backend` as untested since the
Valhalla-to-GraphHopper rewrite, when a regression or test pass runs against its existing routing
and flood-grading behavior, then a real request and response confirms both still work before any
new endpoint work starts.
`backend/test_flood_areas.py` and `backend/test_server.py` cover `derive_areas()`,
`build_custom_model()`, and `server.py`'s full HTTP surface (`/health`, `/flood/areas`,
`POST /route` graded and ungraded) against a real PostGIS and a stub GraphHopper. Both ran clean
against `postgis/postgis:15-3.4`. `artifacts/TODOS.md`'s broader hardening item (a soak period, a
side-by-side comparison against the old Valhalla backend) is still open; this story covered only
the regression-test half of that item.
Dependencies: None.
Evidence: ![[harden-floodmap-backend-tests.png|420]]
Details:
1. What: regression tests for `server.py` and `flood_areas.py`.
2. How: `test_flood_areas.py` and `test_server.py` run against a real PostGIS and a stub GraphHopper.
3. Why: `GET /flood/points` would otherwise land on an unproven backend.
4. Effect: unblocks the point-depth stories. The soak period and the Valhalla comparison stay open in `TODOS.md`.
