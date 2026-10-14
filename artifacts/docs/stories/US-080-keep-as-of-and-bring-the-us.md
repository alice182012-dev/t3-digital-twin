---
date_drafted: 2026-10-07
type: user-story
us_id: "US-080"
story_label: "5"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P3
estimate: XS
sprint: 15
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
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, Reviewed.** The live app already reads "As of", so no code changed. The record of [[US-007-add-the-updated-date-time-line-to|US-007]] is brought in line and its screenshot is retaken. The owner's acceptance is left.

## Evidence and details

![[live-legend-as-of.jpg|420]]

1. What: the legend of the live app reads "As of 13/10/2026 18:00". The title, the Given, and the details of `US-007` now say "As of" and "Forecast for", and its screenshot is the one above.
2. How: the screenshot comes from the live app at `100.67.84.55:8082` in Aside, for `21.0250,105.7550` to `21.0255,105.7620` with the truck profile, taken on 2026-10-14. `timestepLabel.ts` picks the wording, as the story says.
3. Why: the record said "Updated" while the app said "As of", which is a decision of the owner ([[decision-log|D-010]]).
4. The pipeline delay part of [[BL-010-map-shows-forecast-not-now|BL-010]] is not touched, and that blocker is unchanged.
