---
date_drafted: 2026-09-29
type: user-story
us_id: "US-033"
story_label: "2"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P3
estimate: S
sprint: 
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]"]
title: "Write a project `DESIGN.md` with real design tokens"
---

# US-033 Write a project `DESIGN.md` with real design tokens

As a developer building the next screen, I want one versioned file of colors, typography, and spacing, so
new screens match the approved mockup without reading its HTML each time.
Given the approved mockup and the shipped components, when `/design-consultation` runs, then a
`DESIGN.md` lists the tokens (colors, type scale, spacing) extracted from the mockup, and each value the
shipped `FloodLegend.module.css` and `PlaceDepthPopup.module.css` use either matches a token or is listed
as a known divergence.
Dependencies: `US-077` to `US-083`, so it extracts from the UI that they finish. Blocks nothing.

## Status history

- **2026-10-10, estimate M to S.** Compared with US-025 and US-026 (S each: match one screen to the mockup). Extracting tokens from one mockup and two CSS modules into one file is the same size, with no unknowns.
