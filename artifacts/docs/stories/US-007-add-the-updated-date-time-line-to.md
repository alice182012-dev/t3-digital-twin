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
title: "Add the \"As of `date` `time`\" line to the flood legend"
---

# US-007 Add the "As of `date` `time`" line to the flood legend

As a user reading the flood legend, I want to know how current the flood-depth data is, so I can judge whether the map reflects the latest simulation cycle.
Given flood mode is on, when the legend renders, then it shows an "As of `time`" line below the color bands for a step at or before now, and "Forecast for `time`" for a later step, with the selected timestep's date and time.
Dependencies: None.
Evidence: ![[live-legend-as-of.jpg|420]]
The first screenshot, `frontend-legend-updated-line.png`, showed the earlier "Updated" wording and is replaced by the screenshot of the live app on 2026-10-14 ([[US-080-keep-as-of-and-bring-the-us|US-080]]).
Details:
1. What: an "As of" line under the legend bands (it read "Updated" until 2026-10-07, when the owner kept "As of", [[decision-log|D-010]]).
2. How: `FloodLegend` formats the selected timestep with `formatTimestepTime`, in the viewer's local time, and `timestepLabel.ts` picks "As of" or "Forecast for".
3. Why: it shows how current the flood data is.
4. Effect: the legend is one line taller.
   The mobile search panel covered it ([[BL-006-mobile-flood-legend-covered-by-search-panel|mobile-flood-legend-covered-by-search-panel]], resolved 2026-09-28 by moving the legend to bottom-right on mobile).
