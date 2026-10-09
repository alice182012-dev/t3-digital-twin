---
date_drafted: 2026-10-07
type: user-story
us_ids: ["US-076", "US-077", "US-078", "US-079", "US-080", "US-081", "US-082", "US-083", "US-084", "US-085"]
status: draft
subsystem: floodmap-frontend
source_ideas: []
related: ["[[SP-04-frontend-recheck|sprint-plan-4]]", "[[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]", "[[frontend-mockup-recheck-and-sprint-11-start]]", "[[EP-05-mockup-screen-coverage|mockup-screen-coverage]]", "[[PRD-001-flood-routing-mockup-frontend-gap|flood-routing-mockup-frontend-gap]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]", "[[BL-018-route-panel-stuck-on-loading-bars|route-panel-stuck-on-loading-bars]]", "[[decision-log]]"]
tags: [user-story, epic, frontend, mockup, sprint-13, sprint-14, sprint-15, sprint-16]
---

# Epic: frontend recheck against the mockup

The stories of [[EP-05-mockup-screen-coverage|mockup-screen-coverage]], [[EP-02-frontend-polish|frontend-polish]], and [[EP-01-frontend-depth-features|frontend-depth-features]] built the six screens of
`artifacts/raw/frontend-mockups/Flood Routing Mockups v2.dc.html`. The recheck of 2026-10-07 found seven differences
that none of those stories records, and one open blocker with no story. The evidence for each is in
[[frontend-mockup-recheck-and-sprint-11-start]]. This epic turns every one of them into a story. They were in Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. On 2026-10-08 they moved to
[[SP-04-frontend-recheck|sprint-plan-4]] (Sprints 13 to 16), so the routing work finishes first. Dependencies set the sprint of each row.

Each row carries Priority, Status, Estimate, Sprint, and Dependencies, as an extension of the base Epic shape in
[[user-story-types]]. A story reaches `Done` only with a screenshot and numbered details, recorded here and in
`SP-04-frontend-recheck.md`. A UI story takes its screenshot from the running UI. Test points stay inside the model border
(`.claude/CLAUDE.md`). Story 1 runs first, because its screenshots show which of the other differences are visible at
1366x768.

- [[US-076-compare-the-live-app-with-the-mockup|US-076]] Compare the live app with the mockup in Aside at 1366x768. Story 1.
- [[US-077-match-the-depth-chart-columns-and-the|US-077]] Match the depth chart columns and the route tab text to screen 2e. Story 2.
- [[US-078-show-the-place-names-on-the-start|US-078]] Show the place names on the start and destination pins. Story 3.
- [[US-079-name-the-page-floodmap-and-remove-the|US-079]] Name the page "Floodmap" and remove the "Powered by GraphHopper" line and its links. Story 4.
- [[US-080-keep-as-of-and-bring-the-us|US-080]] Keep "As of" and bring the `US-007` record in line. Story 5.
- [[US-081-draw-a-second-dashed-line-for-the|US-081]] Draw a second dashed line for the selected mode's depth limit. Story 6.
- [[US-082-show-the-travel-time-and-the-maximum|US-082]] Show the travel time and the maximum depth on each route tab. Story 7.
- [[US-083-build-a-mobile-version-of-screen-2e|US-083]] Build a mobile version of screen 2e. Story 8.
- [[US-084-design-the-no-route-and-wait-until|US-084]] Design the no-route and "wait until" states, then match the UI to the design. Story 9.
- [[US-085-time-out-a-route-request-in-the|US-085]] Time out a route request in the client. Story 10.

## Status history

Story-level progress lines up to 2026-10-10 are in [[EP-11-frontend-mockup-recheck-history|the archived history]]. This section keeps plan-level changes only.

- **2026-10-07, draft.** Written from the recheck of the frontend against the mockup. The user asked for every candidate to
  become a story in the sprint after Sprint 11, and for a browser comparison in Aside in the same sprint. The third
  candidate of the plan (the "Try next" lines) became three stories (6, 7, and 8), and the legend and "Powered by" questions
  became Stories 4 and 5 after the user's decisions (D-010).
