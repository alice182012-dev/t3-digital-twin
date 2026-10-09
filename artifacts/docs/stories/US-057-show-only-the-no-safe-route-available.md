---
date_drafted: 2026-09-23
type: user-story
us_id: "US-057"
story_label: "6"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Done
priority: P2
estimate: XS
sprint: 3
subsystem: floodmap-frontend
related: ["[[EP-02-frontend-polish]]", "[[SP-01-prd-and-backlog|sprint-plan]]"]
title: "Show only the \"No safe route available\" box when a mode has no connection"
---

# US-057 Show only the "No safe route available" box when a mode has no connection

As a driver whose mode has no route, I want one clear message, so I am not shown the same news twice.
Given a start and destination where GraphHopper answers `ConnectionNotFoundException` for the selected mode, when the panel renders, then it shows the yellow "No safe route available" box and no red error bar.
A failure of another kind, such as "Cannot find point", still shows its message in the red bar.
An earlier error bar goes away when this failure arrives.
This refines [[EP-02-frontend-polish|frontend-polish]] Story 4 (US-009), which put GraphHopper's message in the red bar.
The user judged the bar redundant next to the yellow box on 2026-09-30, after the pair Vincom Center to Cổng Thiên đường Bảo Sơn showed both.
The frontend reads the exception type in the response hints, not the English text, so another locale still matches.
Dependencies: US-009.
Evidence: ![[frontend-no-connection-yellow-only-live-check.png|420]] ![[frontend-no-connection-yellow-only-preview-check.png|420]] ![[frontend-off-road-red-bar-kept-preview-check.png|420]]
Details:
1. What: when GraphHopper answers that no connection exists, the panel shows the yellow "No safe route available" box and no red bar.
   Any other failure keeps its red bar, and a later no-connection failure hides an earlier bar.
2. How: `Api.ts` reads `ConnectionNotFoundException` in the response hints and throws an error with `noConnection` set.
   `routeWithDispatch` passes it to `RouteRequestFailed`, and `ErrorStore` skips the bar for it.
   The exception type is read, not the English text, so another locale still matches.
3. Why: the bar repeated the yellow box, as the user saw on 2026-09-30 with Vincom Center to Cổng Thiên đường Bảo Sơn.
4. Effect: on a preview build on the server, that pair shows only the yellow box, and a pin in Hoàn Kiếm, outside the road data, still shows "Cannot find point 1: 21.0285,105.8542" in the red bar.
   Seven tests are new (`ErrorStore.test.ts` and two in `Api.test.ts`), and all 240 pass.
   Deployed 2026-09-30 (`f87ffb9`).
   On the live site the same pair shows only the yellow box (`frontend-no-connection-yellow-only-live-check.png`), the Hoàn Kiếm pin still shows "Cannot find point 1: 21.0285,105.8542", and a normal walking pair still routes (760 m).

## Status history

- **2026-10-10, body line removed.** The body line of Priority, Status, Estimate, and Sprint repeated the frontmatter and was removed.
  It also said: sprint "3 (follow-up to US-009)".
