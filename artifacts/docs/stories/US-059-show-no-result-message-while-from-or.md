---
date_drafted: 2026-09-24
type: user-story
us_id: "US-059"
story_label: "6"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: XS
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-05-mockup-screen-coverage]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Show no result message while From or To is empty"
---

# US-059 Show no result message while From or To is empty

As a user who just pressed the arrow on a point that filled From, I want the panel to say nothing about routes until both points are set, so I am not told there is no safe route when I have not asked for one.
Given a route was shown and the user presses the arrow on the point that filled From, when From goes back to empty, then the panel shows no route result and no "No safe route available" box.
With both points set and no route, the box still shows.
Cause and evidence are in [[BL-016-no-safe-route-box-shown-with-empty-start|no-safe-route-box-shown-with-empty-start]].
Dependencies: US-058, US-057.
Blocker tracking: [[BL-016-no-safe-route-box-shown-with-empty-start|no-safe-route-box-shown-with-empty-start]]
Evidence: ![[frontend-no-message-empty-from-live-check.png|420]] ![[frontend-no-message-empty-from-preview-check.png|420]]
Details: On the live site, the arrow on the point that filled From moves it to To, From shows its hint, and no "No safe route" text shows.
Checked on a preview build first, then on the live site.
Frontend and backend deployed on 2026-09-30.

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed.
  It also said: sprint "3 (follow-up to US-058, found 2026-09-30)".
