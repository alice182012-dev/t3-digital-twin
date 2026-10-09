---
date_drafted: 2026-09-23
type: user-story
us_id: "US-061"
story_label: "7"
epic: "[[EP-02-frontend-polish]]"
status: Not started
priority: P3
estimate: S
sprint: "none, in the backlog of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]"
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]"]
---

# US-061 Show the place name faster after a map tap

As a user who taps the map, I want the place name to show quickly, so the popup does not look unfinished while it waits.
Given a tap at a point in the flood layer, when the popup opens, then the name or a clear "looking up the place" line shows
without a blank gap, and the name itself arrives in under 1 second for a point already looked up. The user reported about
4 seconds on 2026-10-02. On the same day the backend call took 2.1 to 2.8 seconds and Photon alone took 2.4 to 2.9 seconds,
so the wait is the public Photon service ([[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]]).
Priority: P3. Status: Not started. Estimate: S. Sprint: none, in the backlog of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]]. Dependencies: None.
The user set it to the lowest priority and said to tackle it later. Options are in the blocker page: coordinates at once,
a cache by rounded point, a local Photon, or local road names.
Blocker tracking: [[BL-021-place-name-slow-after-map-tap|place-name-slow-after-map-tap]]
Test points: inside the model border (`.claude/CLAUDE.md`).
