---
date_drafted: 2026-10-13
type: user-story
us_id: "US-148"
title: "Show the place name in the destination field after Route to this place"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
kind: story
priority: P2
estimate: S
sprint: 15
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-148 Show the place name in the destination field after Route to this place

As a user who taps a place and chooses "Route to this place", I want the destination box to show the place name, so I can check where the route goes.

Difference `N6` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
`routeToPlace.ts` names the start once the lookup arrives (`namedStart`). The destination box keeps the raw coordinates `20.999043,105.741703` (screenshot `live-2f`). Screen 2f of the mockup shows the name pre-filled.

Given a tapped point whose name has arrived, when the user chooses "Route to this place", then the destination box shows the name, and the URL keeps the coordinates.
Given a tapped point whose name has not arrived, then the box shows the coordinates, and it changes to the name when the name arrives, unless the user has edited the box.
Given a point with no name from the lookup, then the box keeps the coordinates and no error shows.

The slow lookup ([[BL-021-place-name-slow-after-map-tap|BL-021]], [[US-141-host-photon-for-vietnam-next-to-the-backend|US-141]]) is not part of this story.

Dependencies: None. Test points stay inside the model border (`.claude/CLAUDE.md`).
Evidence: see below.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.
- **2026-10-13, Ready.** Passes the INVEST check and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]] at the product owner's request.

## Evidence and details

Fill this when the story reaches `Done`.
- **2026-10-14, In progress.** Started in parallel with one other story, within the limit of two.
- **2026-10-14, Reviewed.** Built and checked in a local dev build against the server backend. It waits for the one frontend rebuild on the server and the owner's acceptance.

## Evidence and details

Name not yet arrived (the lookup was delayed 6 s in the page): ![[live-coordinates-first.jpg|420]]
Name arrived: ![[live-name-arrived.jpg|420]]

1. What: after "Route to this place" the destination box shows the place name, and the URL keeps the coordinates. When the name has not arrived at the click, the box shows the coordinates and changes to the name when it arrives, unless the user edited the box. A point with no name keeps its coordinates and no error shows.
2. How: `namedDestination` in `floodmap/graphhopper-maps/src/floodmap/routeToPlace.ts` shares a private helper with `namedStart`. The route button closed the popup and with it the place lookup, so `App.tsx` keeps a `namingCoordinate` and `PlaceDepthPopup.tsx` gets a `nameCoordinate` prop that keeps only the lookup alive. Five new tests in `test/floodmap/routeToPlace.test.ts` cover a rename, a rename with via points, a moved destination, a user-typed text, and an empty destination. The whole jest suite (318 tests) and `tsc --noEmit` pass in a throwaway Node container.
3. Checked end to end in Aside against the server backend, with the page's `fetch` delayed 6 s for `places/reverse` to force the slow case. The pin label of [[US-078-show-the-place-names-on-the-start|US-078]] shows the same name.
4. Not covered: a point with no name from the lookup, and a 390x844 viewport. Both are only covered by the unit tests.
5. Left for `Done`: the server rebuild, a server screenshot, and the update of [[floodmap-frontend]].
