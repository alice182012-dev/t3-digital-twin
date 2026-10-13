---
date_drafted: 2026-10-13
type: user-story
us_id: "US-144"
title: "Use the mockup thumbnails for the Map and Flood tiles"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
kind: story
priority: P3
estimate: S
sprint: 
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-144 Use the mockup thumbnails for the Map and Flood tiles

As a user switching layers, I want the Map and Flood tiles to show a picture of each layer, so I can tell what a tap will show before I tap.

Difference `N1` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The tiles are flat colors today. `MapModeToggle.module.css` says the basemap tone "stands in for the mockup's tile-image background". The mockup has two images, `flood_layer.png` and `map_layer.png`, in `artifacts/raw/frontend-mockups/`.

Given the app at 1366x768, when the page loads, then the Map tile shows the map thumbnail and the Flood tile shows the flood thumbnail, each with the white border of the selected tile as in screens 2a and 2b, and the label stays readable on the image.
Given a viewport of 390x844, then the tiles keep their position and size without covering the legend.
Given the built app, then the images are bundled with the frontend and the page makes no request to another origin for them.

Dependencies: None. The images are read from `raw/`, and the story copies them into the frontend source. It never edits `raw/`.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.

## Evidence and details

Fill this when the story reaches `Done`.
