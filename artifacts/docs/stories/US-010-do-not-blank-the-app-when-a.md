---
date_drafted: 2026-09-23
type: user-story
us_id: "US-010"
story_label: "5"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P0
estimate: XS
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Do not blank the app when a route description is a list"
---

# US-010 Do not blank the app when a route description is a list

As a user, I want a route with a description to show its tab, so the app never goes blank on a normal route.
Given a route response whose `description` is a list of strings (for example `["Đường Hoàng Tùng"]`), when
the route panel renders, then the tab is labeled with that text and the app stays up. A response with no
description, an empty one, or one that is not text still labels the tab "Route N".
Dependencies: None.
Blocker tracking: [[BL-017-route-description-list-blanks-app|route-description-list-blanks-app]]
Evidence: ![[frontend-route-description-list-live-check.png|420]] ![[frontend-route-description-list-preview-check.png|420]]
Details:
1. What: a route whose description is a list of street names labels its tab with them, and the app stays up. A description that is empty, or is not text or a list of text, still gives "Route N".
2. How: `descriptionText` in `routingResultsView.ts` reads the description as text or a list of text. `buildRouteTabs` uses it in both places it read the field.
3. Why: `.trim` on a list threw `trim is not a function` and blanked the whole app.
4. Effect: four new tests failed with the exact production error before the fix. On a preview build on the server, a response with `["Đường Hoàng Tùng"]` shows the tab "Đường Hoàng Tùng" and the app stays up. Deployed 2026-09-30 (`5d08b99`). On the live site the response with `["Đường Hoàng Tùng"]` shows the tab "Đường Hoàng Tùng" and the app stays up (`frontend-route-description-list-live-check.png`).

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed. It also said: sprint "3 (found 2026-09-30)".
