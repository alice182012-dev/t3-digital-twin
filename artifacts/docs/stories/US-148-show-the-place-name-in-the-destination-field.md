---
date_drafted: 2026-10-13
type: user-story
us_id: "US-148"
title: "Show the place name in the destination field after Route to this place"
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

# US-148 Show the place name in the destination field after Route to this place

As a user who taps a place and chooses "Route to this place", I want the destination box to show the place name, so I can check where the route goes.

Difference `N6` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
`routeToPlace.ts` names the start once the lookup arrives (`namedStart`). The destination box keeps the raw coordinates `20.999043,105.741703` (screenshot `live-2f`). Screen 2f of the mockup shows the name pre-filled.

Given a tapped point whose name has arrived, when the user chooses "Route to this place", then the destination box shows the name, and the URL keeps the coordinates.
Given a tapped point whose name has not arrived, then the box shows the coordinates, and it changes to the name when the name arrives, unless the user has edited the box.
Given a point with no name from the lookup, then the box keeps the coordinates and no error shows.

The slow lookup ([[BL-021-place-name-slow-after-map-tap|BL-021]], [[US-141-host-photon-for-vietnam-next-to-the-backend|US-141]]) is not part of this story.

Dependencies: None. Test points stay inside the model border (`.claude/CLAUDE.md`).
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.

## Evidence and details

Fill this when the story reaches `Done`.
