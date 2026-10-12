---
date_drafted: 2026-10-09
type: user-story
us_id: "US-098"
story_label: "2"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Not started
priority: P2
estimate: S
sprint: 
subsystem: routing, frontend
related: ["[[EP-16-precaution-depth-routing]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Show the recommended route and the through-water option in the app"
---

# US-098 Show the recommended route and the through-water option in the app

As a driver, I want to see both routes with a label that says the second one passes through water between the precaution depth and my limit.
Given a response with two options, when the route panel opens, then it shows the recommended route first and the through-water route as a second tab with its label and its deepest road.
With one option, it shows one route.
The no-route message changes to match D-021.
Dependencies: `US-097`, `US-076`, and the design of the no-route state in `US-084`.
Evidence: None yet.

## Status history

- **2026-10-12, not picked.** The product owner asked to add every backend story to [[SPR-014-finish-the-remaining-backend|SPR-014]]. This story is left out: its backend, [[US-097-recommend-a-route-that-avoids-the-precaution|US-097]], is `Done`, so what remains is the route panel, which is frontend work, and its dependencies [[US-076-compare-the-live-app-with-the-mockup|US-076]] and the design of [[US-084-design-the-no-route-and-wait-until|US-084]] have not started.

