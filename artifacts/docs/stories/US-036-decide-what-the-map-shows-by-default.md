---
date_drafted: 2026-09-29
type: user-story
us_id: "US-036"
story_label: "5"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: S
sprint: 2
subsystem: floodmap-frontend, floodmap-backend
related: ["[[EP-07-carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Decide what the map shows by default, and close or schedule the latency work"
---

# US-036 Decide what the map shows by default, and close or schedule the latency work

As the product owner, I want the map's "now" behavior accepted or changed on purpose, so the label and the data agree.
Given the map shows the latest published step at or before now and captions it "As of `time`", when the user reviews [[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]] and [[five-minute-tile-freshness]], then the user records one decision on the blocker page: accept the caption and the 1.5 to 3 minute publish delay, or choose a freshness option and add its stories to a sprint.
Dependencies: None.
Evidence: ![[map-now-caption-as-of-0130.png|420]]
Details:
1. What: the map's "now" behavior (Option C, latest published step at or before now, captioned "As of `time`") is accepted as built.
   The user chose to keep narrowing the 1.5 to 3 minute publish delay rather than accept it as final.
2. How: the user picked [[five-minute-tile-freshness]]'s option D, finishing the worker-concurrency fix's own follow-on (a per-run critical-path narrowing, not the bigger staggered-streams option E).
3. Why: option D is the cheapest of the remaining options and doesn't require the added pipeline load and shrunk 3Di turnaround margin that option E needs.
4. Effect: scheduled as Story 6 below.
   Option E, and accepting the delay as final, are both closed for this plan; either can be revisited from [[five-minute-tile-freshness]] if Story 6's result doesn't reach a satisfactory margin.
5. Evidence: a screenshot the user took on the running map at 2026-09-30 01:36 (the menu-bar clock shows it) with the legend caption "As of 30/09/2026 01:30", a step six minutes before the capture.
   The address bar is not in the image.
   Earlier that day the caption read 16:45, because `flood_mapping_full` was paused.
   The image shows the accepted behavior.
   It does not measure the publish delay, which Story 6 covers.

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed.
  It also said: estimate "S for the decision".
