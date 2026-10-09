---
date_drafted: 2026-09-23
type: user-story
us_id: "US-007"
story_label: "2"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 1
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Add the \"Updated `date` `time`\" line to the flood legend"
---

# US-007 Add the "Updated `date` `time`" line to the flood legend

As a user reading the flood legend, I want to know how current the flood-depth data is, so I can
judge whether the map reflects the latest simulation cycle.
Given flood mode is on, when the legend renders, then it shows an "Updated" line below the color
bands with the selected timestep's date and time.
Priority: P2. Status: Done. Estimate: S. Sprint: 1. Dependencies: None.
Evidence: ![[frontend-legend-updated-line.png|420]]
Details:
1. What: an "Updated" line under the legend bands.
2. How: `FloodLegend` formats the selected timestep with `formatTimestepTime`, in the viewer's local time.
3. Why: it shows how current the flood data is.
4. Effect: the legend is one line taller. The mobile search panel covered it
   ([[BL-006-mobile-flood-legend-covered-by-search-panel|mobile-flood-legend-covered-by-search-panel]], resolved 2026-09-28 by moving the legend to
   bottom-right on mobile).
