---
date_drafted: 2026-09-29
type: user-story
us_id: "US-048"
story_label: "R3"
epic: "[[EP-09-time-aware-routing-engine]]"
status: Superseded
priority: P1
estimate: S
sprint: 
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]"]
title: "Show \"no route\" for a mode that has none"
---

# US-048 Show "no route" for a mode that has none

As a driver, I want the app to say that my mode has no route, so I never see another mode's route under my
mode's icon.
Given the reproduction in [[BL-014-failed-route-shows-previous-mode-route|failed-route-shows-previous-mode-route]], when the car request fails with
`ConnectionNotFoundException`, then the map clears the previous route, the alert shows a message with text,
and the backend passes GraphHopper's error body through in a shape `Api.ts` reads.
This is todo 13 in [[frontend-todos-and-backend-dependencies]]. The user scheduled the same fix as
[[EP-02-frontend-polish|frontend-polish]] Story 4 in [[SP-01-prd-and-backlog|sprint-plan]] Sprint 3 (2026-10-05 to 2026-10-11) on 2026-09-29, so this story is
superseded by US-009 and left out of [[SP-02-routing-engine-foundations|sprint-plan-2]].
Priority: P1. Status: Superseded by [[EP-02-frontend-polish|frontend-polish]] Story 4. Estimate: S. Sprint: none. Dependencies: None.
