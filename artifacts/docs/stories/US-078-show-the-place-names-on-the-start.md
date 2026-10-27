---
date_drafted: 2026-10-07
type: user-story
us_id: "US-078"
story_label: "3"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the place names on the start and destination pins"
---

# US-078 Show the place names on the start and destination pins

As a user looking at a route, I want the pins to carry their names, so I know which end is which without reading the panel.
Given a route whose start and destination have names, when the map renders, then each pin shows its name next to it, as in screen 2e ("GO Thăng Long", "FPT Shop").
A point with only coordinates shows no label.
Dependencies: Story 1.
Covers G2.
Evidence: see below.

## Status history

- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, In progress.** Started after the owner accepted [[US-077-match-the-depth-chart-columns-and-the|US-077]].
- **2026-10-14, Reviewed.** Built and checked in a local build against the server backend. It waits for a rebuild of the frontend on the server and the owner's acceptance.
- **2026-10-14, Done.** The owner accepted it after the frontend rebuild on the server and the server check in the last details item.

## Evidence and details

![[live-pin-labels.jpg|420]]

1. What: the start and destination pins show their place name in a white rounded label with a soft shadow, to the right of the pin head, as in screen 2e. A point with an empty text or only coordinates shows no label, and a via point never shows one.
2. How: `pinLabel` in `floodmap/graphhopper-maps/src/Converters.ts` returns the name or `undefined`. `UseQueryPointsLayer.tsx` adds a second style with the label, which `createLabelCanvas.ts` draws on a canvas at the device pixel ratio. The tests are in `test/Converters.test.ts`. The `test/Converters.test.ts`, `test/floodmap`, and `test/sidebar` suites pass (75 tests), and `tsc --noEmit` and `prettier --check` are clean, in a throwaway Node container.
3. Why a canvas and not an OpenLayers text style: a text style has square corners, and the mockup has a rounded label.
4. The screenshot comes from a local dev build served on `127.0.0.1:3000` against the backend at `100.67.84.55:8010`, for `21.0250,105.7550` (GO Thang Long) to `21.0255,105.7620` (FPT Shop) with the truck profile. The page shows the map only, because the viewport was narrow, so the panel and the Elevation widget ([[US-147-remove-the-elevation-widget-from-the-route-view|US-147]]) are outside this story.
5. Server check on 2026-10-14: the `flood-routing-frontend` container was recreated at 14:40 +07 and serves `bundle.59973ebe0d06b74d3b7c.js`. Aside at `100.67.84.55:8082` (window 1440x900) shows the name "Phố Tân Mỹ, 12600 Hanoi, Vietnam" in a rounded label on the destination pin, for `21.0250,105.7550` to a place picked from the autofill. Screenshot: `evidence/server-check-2026-10-14/server-named-destination.jpg`. The owner accepted the story on 2026-10-14.
