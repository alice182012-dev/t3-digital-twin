---
date_drafted: 2026-10-07
type: user-story
us_id: "US-085"
story_label: "10"
epic: "[[EP-11-frontend-mockup-recheck]]"
status: Not started
priority: P2
estimate: S
sprint: 13
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
---

# US-085 Time out a route request in the client

As a user on a slow connection, I want a route request to end with a message, so the panel does not show loading bars
for ever.
Given a route request that gets no answer, when it has waited longer than a limit the story sets from the numbers of
`US-035`, then the request is cancelled, the panel shows a retry message, and the loading bars stop. A request that
answers in time is not affected.
Priority: P2. Status: Not started. Estimate: S. Sprint: 13 ([[SP-04-frontend-recheck|sprint-plan-4]]; 2026-12-14 to 2026-12-20), moved from Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] on 2026-10-08. Dependencies: None.
Blocker tracking: [[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]]
Evidence: None yet.
