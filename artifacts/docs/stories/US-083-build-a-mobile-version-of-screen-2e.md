---
date_drafted: 2026-10-07
type: user-story
us_id: "US-083"
story_label: "8"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P3
estimate: L
sprint: 
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Build a mobile version of screen 2e"
---

# US-083 Build a mobile version of screen 2e

As a user on a phone, I want the route result, the chart, and the steps to fit a 390 px screen, so I can use the app
where I am.
Given a viewport of 390x844, when a route result is open, then the profile row, the tabs, the chart, and the steps
are all reachable without horizontal scroll, the legend is not covered, and the touch targets are at least 44 px.
The mockup has no mobile design, so the story starts with a layout the user approves.
Priority: P3. Status: Not started. Estimate: L. Sprint: 16 ([[SP-04-frontend-recheck|sprint-plan-4]]; 2027-01-04 to 2027-01-10), moved from Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] on 2026-10-08. Dependencies: Stories 2, 3, and 7, so the layout covers the
final components. Covers the third "Try next" line (G6).
Evidence: None yet.

## Status history

- **2026-10-10, estimate M to L.** Compared with US-001 (M for one chart). A mobile layout covers the profile row, the tabs, the chart, the steps, and the legend, and starts with a layout that the product owner approves. Split it before it enters a sprint: one story for the approved layout, one for the build.
