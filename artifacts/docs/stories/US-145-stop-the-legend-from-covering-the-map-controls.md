---
date_drafted: 2026-10-13
type: user-story
us_id: "US-145"
title: "Stop the legend from covering the map controls"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
kind: story
priority: P2
estimate: S
sprint: 
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-145 Stop the legend from covering the map controls

As a user on a laptop, I want the zoom, locate, and layer buttons to stay in reach when the legend shows, so I can still zoom the map.

Difference `N2` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
With flood on, the legend (`FloodLegend.module.css`, `right: 30px; top: 30px`) sits on top of the top-right map controls. The zoom `+` and `-`, the locate button, and the layer switcher are half hidden behind it in the screenshot `live-2b`. The mockup puts the legend at the bottom right and has no such controls.

Given flood mode at 1366x768, when the page loads, then the legend and the map buttons do not overlap, and every button is fully visible and clickable.
Given a viewport of 390x844, then the same holds with the search panel open.
Given the mockup screens 2b and 2c, then the legend sits where the mockup puts it, or the story records why it moves.

Dependencies: None. Decide with the owner whether the stock map buttons stay (US-147 decides the panel).
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.

## Evidence and details

Fill this when the story reaches `Done`.
