---
date_drafted: 2026-10-09
type: user-story
us_id: "US-098"
story_label: "2"
epic: "[[EP-16-precaution-depth-routing]]"
status: Not started
priority: P2
estimate: S
sprint: 14
subsystem: routing, frontend
related: ["[[EP-16-precaution-depth-routing]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the recommended route and the through-water option in the app"
---

# US-098 Show the recommended route and the through-water option in the app

As a driver, I want to see both routes with a label that says the second one passes through water between the precaution depth and my limit.
Given a response with two options, when the route panel opens, then it shows the recommended route first and the through-water route as a second tab with its label and its deepest road. With one option, it shows one route. The no-route message changes to match D-021.
Priority: P2. Status: Not started. Estimate: S. Sprint: 14 ([[SP-04-frontend-recheck|sprint-plan-4]]).
Dependencies: `US-097`, `US-076`, and the design of the no-route state in `US-084`.
Evidence: None yet.
