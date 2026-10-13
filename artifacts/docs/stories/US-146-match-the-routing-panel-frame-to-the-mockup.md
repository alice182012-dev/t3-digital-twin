---
date_drafted: 2026-10-13
type: user-story
us_id: "US-146"
title: "Match the routing panel frame to the mockup"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
kind: story
priority: P2
estimate: M
sprint: 
subsystem: floodmap-frontend
source_ideas: []
related: ["[[US-076-compare-the-live-app-with-the-mockup|US-076]]", "[[EP-19-frontend-against-the-mockup|EP-19]]"]
tags: [user-story]
---

# US-146 Match the routing panel frame to the mockup

As a user planning a route, I want the routing panel to look like the approved design, so the app reads as one product and not as the stock GraphHopper card.

Difference `N3` in [[EP-19-frontend-against-the-mockup|EP-19]], found by [[US-076-compare-the-live-app-with-the-mockup|US-076]].
The panel is the stock GraphHopper card: a settings gear, "Add location", "Settings", "GPX", and "Details". The mockup (screens 2c to 2e) has a full-height white panel of about 460 px, a black pill on the selected mode with a white icon, a close X at the right, rounded input boxes joined by a dotted connector, and no gear, "Add location", or "Settings" link.

Given the empty routing panel at 1366x768, when it opens, then it matches screen 2c: the four mode icons with the selected one in a black pill, a close X, two rounded input boxes with the dotted connector, and no other controls.
Given a route result, then the same frame holds around the chart and the steps of screen 2e.
Given the removed controls, then each one either has a replacement the owner approved or is recorded as dropped in this story.
Given the panel, then a keyboard user can still reach every remaining control, and the close X has an accessible name.

The story estimate is M. If the match of the input boxes and the removal of the stock controls grow, split the second part before the sprint holds it.

Dependencies: [[US-079-name-the-page-floodmap-and-remove-the|US-079]] removes the "Powered by" line, so the panel match starts after it. The owner decides which stock controls (settings, GPX, details, custom model) stay.
Evidence: None yet.

## Status history

- **2026-10-13, draft.** Drafted from the comparison of [[US-076-compare-the-live-app-with-the-mockup|US-076]]. It is in the backlog and has no `sprint`.

## Evidence and details

Fill this when the story reaches `Done`.
