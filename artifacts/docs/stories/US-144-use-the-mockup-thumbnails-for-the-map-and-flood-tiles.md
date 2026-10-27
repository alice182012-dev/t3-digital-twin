---
date_drafted: 2026-10-13
type: user-story
us_id: "US-144"
title: "Use the mockup thumbnails for the Map and Flood tiles"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
kind: story
priority: P3
estimate: S
sprint: 15
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
Evidence: see below.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.
- **2026-10-14, owner answer.** The unselected tile stays dimmed to 0.65, as in the mockup source. No change to the build.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started in parallel with one other story, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.

## Evidence and details

![[live-tiles.jpg|420]]

1. What: the Map tile shows the mockup's map thumbnail and the Flood tile shows its flood thumbnail, each with the white border, the selected tile with the dark ring, and the label on a dark strip at the bottom.
2. How: `MapModeToggle.tsx` renders an `<img>` in each tile, styled by `.thumbImage` in `MapModeToggle.module.css`. The images are copies of `raw/frontend-mockups/flood_layer.png` and `map_layer.png`, downscaled with `sips` to 2x of the 82 px tile and stored in `src/floodmap/`. The blue tint span is removed. Webpack's existing png rule bundles them, so the page makes no request to another origin. jest (195 tests) and `tsc --noEmit` pass in a throwaway Node container.
3. Not checked: the 390x844 viewport, the page-load state with Map selected (screen 2a), and the emitted asset of a production build. The dev build shows Flood selected, which matches screen 2b.
4. Open: the unselected tile is dimmed to 0.65, as in the mockup source, but in the mockup image of screen 2a the unselected Flood tile looks brighter. Compare it at the review.
5. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows the Map and Flood tiles with the mockup thumbnails, Flood selected. Screenshot: `evidence/server-check-2026-10-14/server-route-collapsed.jpg`. The owner accepted the story on 2026-10-14.
