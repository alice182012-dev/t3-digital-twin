---
date_drafted: 2026-09-29
type: user-story
us_id: "US-032"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 4
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Make the map toggle, legend, and route tabs usable by keyboard and screen reader"
---

# US-032 Make the map toggle, legend, and route tabs usable by keyboard and screen reader

As a person who uses a keyboard or a screen reader, I want the Map or Flood toggle, the flood legend, and
the route tabs to be operable and announced, so I can read the flood map and pick a route without a mouse.
Given the app is open with a route showing, when the user moves through the page with the Tab key, then the
toggle has `aria-pressed` and responds to Enter and Space, the route tabs have `role="tablist"` and
`role="tab"` with `aria-selected` and move with the arrow keys, every control has a touch target of at
least 44 px, and the legend text has a contrast ratio of at least 4.5:1 against its background.
Priority: P2. Status: Done. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None. The components exist.
`PlainButton` likely covers baseline keyboard use already. The route tabs have no ARIA precedent in the
codebase.
Evidence: ![[frontend-route-tabs-keyboard-live-check.png|420]] ![[frontend-route-tabs-keyboard-preview-check.png|420]]
Details:
1. What: the route tabs move with the arrow keys, are 44 px tall, and show a focus outline. The legend band labels have an explicit color, and a test fails if legend or tab text drops under 4.5:1.
2. How: `routeTabKeyTarget` is a pure function. `RouteTabs.tsx` gives the selected tab `tabindex` 0 and the others -1, and moves focus with the selection. `.routeTab` has a 44 px minimum size, and `.band` has `color: #111827`. `textContrast.test.ts` reads the CSS and checks six pairs. Tests first, 7 commits (`f44f776` to `26034f1`), 279 tests pass.
3. Why: a person who uses a keyboard can pick a route and switch the map mode without a mouse.
4. Effect: on the live site (2026-10-01), a foot route from 20.9850, 105.7100 to 21.0150, 105.7900 showed 3 tabs of 44 px. ArrowRight and ArrowLeft wrapped, Home and End jumped to the ends, and Tab left the strip from the selected tab. Enter on Map and Space on Flood flipped `aria-pressed`. The legend band labels computed to rgb(17, 24, 39). The toggle's `aria-pressed` and the tabs' `role` and `aria-selected` were already in place. A preview build passed first. No screen reader was tried. `US-035` can now measure the final components.
