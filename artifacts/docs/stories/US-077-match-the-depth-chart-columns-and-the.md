---
date_drafted: 2026-10-07
type: user-story
us_id: "US-077"
story_label: "2"
epic: "[[EP-11-frontend-mockup-recheck]]"
status: Not started
priority: P2
estimate: S
sprint: 14
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
---

# US-077 Match the depth chart columns and the route tab text to screen 2e

As a user comparing routes, I want the chart to show the next hours at a glance and each tab to name its road, so I
read the chart and the tabs the way the approved design shows them.
Given a route with a depth forecast, when the chart renders, then it shows 5 columns that are 30 minutes apart (every
second 15-minute step), only full hours are labelled, and the "now" column is the latest step at or before now, in
green, with the dashed line at its depth. Given a route with a road description, when the tabs render, then each tab
reads "Via `road`", and a tab with no unique description still reads "Route N".
The pipeline publishes 15-minute steps, so the chart takes every second step. The PRD decision of 2026-09-23 ("30
minutes, matching the mockup") stays true for the chart.
Priority: P2. Status: Not started. Estimate: S. Sprint: 14 ([[SP-04-frontend-recheck|sprint-plan-4]]; 2026-12-21 to 2026-12-27), moved from Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] on 2026-10-08. Dependencies: Story 1 (screenshots of the chart and the
tabs). Covers G1 and G3.
Evidence: None yet.
