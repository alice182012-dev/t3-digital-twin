---
date_drafted: 2026-10-13
type: user-story
us_id: "US-145"
title: "Stop the legend from covering the map controls"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
kind: story
priority: P2
estimate: S
sprint: 15
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
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.
- **2026-10-14, owner answer.** The legend moves to the bottom right, exactly like screen 2b (the gradient bar with ticks). The stock map buttons stay at the top right. A worker builds it.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.

![[crop-ours.jpg|420]]

1. What: the legend sits at the bottom right as a 14x168 px gradient bar with ticks at 5, 10, 20, 30, 40, 50, and 60 cm and "> 60 cm", as in screen 2b. The stock map buttons stay at the top right and are not covered.
2. How: `FloodLegend.tsx` and `FloodLegend.module.css`, with `legendTicks()` and `legendGradient()` in `depthScale.ts`, which derive the bar from `DISPLAY_DEPTH_BANDS`, so the legend and the map paint stay one scale. At 390x844 the legend sits above the Map and Flood tiles and the demo banner above it. With a route open, the tiles and the legend sit in a grid cell over the map, so the footer sheet does not cover them. jest (299 tests) and `tsc --noEmit` pass in a throwaway Node container.
3. Evidence: `evidence/US-145/` holds `live-1366.jpg`, `live-390.jpg`, `live-390-route.jpg`, `crop-ours.jpg`, and `crop-mockup.jpg`.
4. Not checked: a pixel-exact match, because the app font is its own stack and not the mockup's Inter. The caption says "As of", the owner's earlier choice, and not "Updated". Also not checked: 390x844 with the search panel expanded, and a phone shorter than 844 px.
5. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows the legend at the bottom right above the OpenStreetMap line, clear of the zoom and layer buttons and of the Map and Flood tiles. The 390x844 layout was not rechecked on the server. Screenshot: `evidence/server-check-2026-10-14/server-route-panel.jpg`. The owner accepted the story on 2026-10-14.
