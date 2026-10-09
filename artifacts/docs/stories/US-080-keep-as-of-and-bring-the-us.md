---
date_drafted: 2026-10-07
type: user-story
us_id: "US-080"
story_label: "5"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P3
estimate: XS
sprint: 
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Keep \"As of\" and bring the `US-007` record in line"
---

# US-080 Keep "As of" and bring the `US-007` record in line

As a maintainer, I want the written criteria and the screenshot of the legend to match the label, so the record does not say "Updated" when the app says "As of".
Given the legend in flood mode, when it renders, then it reads "As of `time`" for a step at or before now and "Forecast for `time`" for a later step, as `timestepLabel.ts` does.
The criteria of [[EP-02-frontend-polish|frontend-polish]] Story 2 (`US-007`) say the same, and its screenshot is retaken from the live app.
Decided by the user on 2026-10-07: keep "As of" ([[decision-log]] D-010).
This settles the legend part of [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]].
The blocker stays `monitoring` for the pipeline delay.
Dependencies: None.
Covers G5.
Evidence: None yet.
