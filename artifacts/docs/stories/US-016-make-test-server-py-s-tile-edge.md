---
date_drafted: 2026-09-23
type: user-story
us_id: "US-016"
story_label: "6"
epic: "[[EP-17-flood-data-pipeline-and-core-output]]"
status: Done
priority: P3
estimate: XS
sprint: 3
subsystem: architecture-backend
related: ["[[EP-03-point-depth-lookup-backend]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Make test_server.py's tile-edge check independent of GDAL's rounding"
---

# US-016 Make test_server.py's tile-edge check independent of GDAL's rounding

As a maintainer of the backend, I want `test_server.py` to end green on any GDAL version, so it stays a
regression pass that people trust.
Given the reference point of the "edge of two tiles" check lies a hair below a pixel boundary, when the
script runs, then it accepts the endpoint's value when it equals one of the four pixels touching that boundary, and
it runs to its end, including the checks after that one.
Dependencies: None.
Blocker tracking: [[BL-019-test-server-tile-edge-check-fails|test-server-tile-edge-check-fails]]
Evidence: ![[test-server-tile-edge-fixed-output.png|420]]
Details:
1. What: `test_server.py` ends green and runs every check to the end.
2. How: `pixels_around_boundary` in `test_server.py` finds the pixel boundary nearest each edge point and reads the four pixels around it. The test requires the endpoint's float32 value to equal one of them, and the four to be distinct, so any other pixel or `no_data` still fails. Both edge points use the one rule.
3. Why: the reference point sits 3e-11 pixels off a boundary, and `gdallocationinfo` and PostGIS break that tie differently. The first attempt, one reference per point, passed only on this GDAL's noise, so it was replaced.
4. Effect: the script exits 0, and the no_data, 404, and validation checks after the tile-edge check run again. The rule is checked on GDAL 3.12.3 and PostGIS 15-3.4 only. It is a test change, so nothing is deployed.

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed. It also said: sprint "3 (found 2026-09-30, fixed by a subagent under rule 11)".
