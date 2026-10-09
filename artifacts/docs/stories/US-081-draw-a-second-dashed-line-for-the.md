---
date_drafted: 2026-10-07
type: user-story
us_id: "US-081"
story_label: "6"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Not started
priority: P3
estimate: S
sprint: 
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Draw a second dashed line for the selected mode's depth limit"
---

# US-081 Draw a second dashed line for the selected mode's depth limit

As a user who drives a motorbike, a car, or a truck, I want the chart to show my vehicle's limit, so I see when the
route depth crosses it.
Given a route and a selected mode, when the chart renders, then a second dashed line marks that mode's limit in
centimetres, labelled, and it moves when the user selects another mode. The limits come from one owner (`US-074`).
Dependencies: Story 2, and `US-074` for the limits.
Covers the first "Try next" line of the mockup (G6).
Evidence: None yet.
