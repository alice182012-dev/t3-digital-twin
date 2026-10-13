---
date_drafted: 2026-10-13
type: user-story
us_id: "US-147"
title: "Remove the Elevation widget from the route view"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
kind: story
priority: P3
estimate: XS
sprint: 
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-147 Remove the Elevation widget from the route view

As a user reading a route in a flood app, I want no elevation chart, so the map shows only what the design shows.

Difference `N4` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The stock GraphHopper elevation widget (`src/pathDetails/ElevationInfoBar.tsx`) shows at the bottom left of every route result. Mockup screen 2e has none, and the area is flat, so the chart reads "-" with a 0 m line.

Given a route result at 1366x768, when the panel shows the route, then no elevation widget, path-detail selector, or play button shows, and the map and the legend are unchanged.
Given the path-detail popup code, then the story removes or leaves it by a decision recorded here, and no console error appears.

Dependencies: None. Ask the owner whether any path detail (surface, road class) is wanted before it is removed.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.

## Evidence and details

Fill this when the story reaches `Done`.
