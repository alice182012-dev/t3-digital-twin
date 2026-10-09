---
date_drafted: 2026-10-07
type: user-story
us_id: "US-082"
story_label: "7"
epic: "[[EP-11-frontend-mockup-recheck]]"
status: Not started
priority: P3
estimate: S
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the travel time and the maximum depth on each route tab"
---

# US-082 Show the travel time and the maximum depth on each route tab

As a user choosing between routes, I want each tab to show its time and its deepest water, so I pick one without
opening each.
Given a route with alternatives, when the tabs render, then each tab shows the road name, the travel time, and the
maximum depth along that route in centimetres.
Priority: P3. Status: Not started. Estimate: S. Sprint: 15 ([[SP-04-frontend-recheck|sprint-plan-4]]; 2026-12-28 to 2027-01-03), moved from Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] on 2026-10-08. Dependencies: Story 2 (the tab text). The depth comes from
`POST /flood/profile` for each alternative, so check the cost of one request per tab first. Covers the second "Try
next" line (G6).
Evidence: None yet.
