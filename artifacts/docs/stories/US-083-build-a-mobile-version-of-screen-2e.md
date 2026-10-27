---
date_drafted: 2026-10-07
type: user-story
us_id: "US-083"
story_label: "8"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Ready
priority: P3
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Design a mobile layout of screen 2e"
---

# US-083 Design a mobile layout of screen 2e

As a user on a phone, I want a mobile layout that the product owner approved, so the build of [[US-143-build-the-mobile-version-of-screen-2e|US-143]] has a design to match.

Part one of two. The mockup has no mobile design, so this story produces the layout and the build follows it.

Given the mockup of screen 2e, when the layout is drawn for a viewport of 390x844, then it shows the profile row, the tabs, the chart, the steps, and the legend, with touch targets of at least 44 px and no horizontal scroll, and the product owner has approved it.

Dependencies: [[US-077-match-the-depth-chart-columns-and-the|US-077]], [[US-078-show-the-place-names-on-the-start|US-078]], and [[US-082-show-the-travel-time-and-the-maximum|US-082]], so the layout covers the final components.
Covers the third "Try next" line (G6).
Evidence: None yet.

## Status history

- **2026-10-10, estimate M to L.** Compared with US-001 (M for one chart).
  A mobile layout covers the profile row, the tabs, the chart, the steps, and the legend, and starts with a layout that the product owner approves.
  Split it before it enters a sprint: one story for the approved layout, one for the build.
- **2026-10-13, Ready.** Split into two parts at refinement for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]]. This part is the approved layout (S, 2 points), and [[US-143-build-the-mobile-version-of-screen-2e|US-143]] is the build (M, 3 points). Picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
