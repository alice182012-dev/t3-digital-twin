---
date_drafted: 2026-09-23
type: user-story
us_id: "US-006"
story_label: "1"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: M
sprint: 1
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Add per-mode travel time under the four mode icons"
---

# US-006 Add per-mode travel time under the four mode icons

As a user comparing routes, I want a travel time under each of the four mode icons at once, so I
can compare modes without selecting each one in turn.
Given a route exists between two points, when the route result renders, then each of the four mode
icons in the profile row shows a travel time below it, and the selected mode's time is visually
distinguished (bold, matching mockup screen 2e), without the user selecting each mode in turn to
see its time.
Priority: P2. Status: Done. Estimate: M. Sprint: 1. Dependencies: None. Known risk: four separate route
requests per query may add visible delay. Accepted for now since this isn't shown to real users
yet (see [[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]'s Decisions).
Evidence: ![[frontend-per-mode-travel-time.png|420]]
Details:
1. What: a travel time under each mode icon, with the selected mode in bold.
2. How: `useProfileTimes` sends one route request per profile for each query.
3. Why: compare modes without switching.
4. Effect: four requests per query. Truck is missing until Sprint 4, and every mode uses the motorbike flood limit ([[BL-005-flood-routing-vehicle-type-always-motorbike|flood-routing-vehicle-type-always-motorbike]]).
