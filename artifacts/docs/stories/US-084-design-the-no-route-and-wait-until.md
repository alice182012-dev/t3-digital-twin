---
date_drafted: 2026-10-07
type: user-story
us_id: "US-084"
story_label: "9"
epic: "[[EP-19-frontend-against-the-mockup]]"
status: Reviewed
priority: P2
estimate: M
sprint: 15
subsystem: floodmap-frontend
related: ["[[EP-11-frontend-mockup-recheck]]", "[[SP-04-frontend-recheck|sprint-plan-4]]"]
title: "Design the no-route and \"wait until\" states, then match the UI to the design"
---

# US-084 Design the no-route and "wait until" states, then match the UI to the design

As a product owner, I want the two states the mockup lacks to have an approved design, so the wording and layout are a choice and not an accident.
Given the yellow "No safe route available" box and the alert of `US-054`, when the user has approved a design for each state, then the UI matches it at 1366x768 and at 390x844, and a screenshot of each state is saved.
Dependencies: Story 1, and `US-055`, so the "wait until" text comes from the real backend.
Covers G7.
Evidence: None yet.

## Status history

- **2026-10-10, estimate S to M.** Compared with US-057 and US-009 (XS and S: one message each).
  Two states need a design that the product owner approves, then a match at two screen sizes, so the risk and the screenshots double.
- **2026-10-13, Ready.** Passes the INVEST check at refinement and is picked for [[SPR-015-match-the-frontend-to-the-mockup|SPR-015]].
- **2026-10-14, owner answer.** The owner approved the designs of the no-route and "wait until" states (`live-state-no-route.jpg` and `live-state-wait-until.jpg` in `evidence/US-076/`). The build can start, and [[US-098-show-the-recommended-route-and-the-through|US-098]] is unblocked.
- **2026-10-14, Reviewed.** A worker compared the live app with the approved images and found no difference in the two boxes, so no code changed. It waits for the owner's acceptance.

## Evidence and details

![[live-no-route-1366.png|420]]

1. What: the live no-route box and the "wait until" box match the approved designs. The wording is identical ("No safe route available. Please consider getting to the safest location or stay where you are.", "Timing check unavailable", "The usual route is clear from 23:02 (forecast run 21:00)"). The box style is unchanged since the images were taken: background `#fdf0d5`, text `#8a5a00`, 12 px margin and padding.
2. How: Playwright at 1366x768 and 390x844 against the server backend, with the answers of `POST /api/gh/route` and `POST /api/gh/route/departures` faked in the page, because the real backend gives no such state on demand. The pair was `21.025,105.755` to `21.0255,105.762` (truck). jest (299 tests) and `tsc --noEmit` pass.
3. Evidence: `evidence/US-084/` holds `live-no-route-1366.png`, `live-no-route-390.png`, `live-wait-until-1366.png`, and `live-wait-until-390.png`.
4. Differences left as they are: the "wait until" line sits on one line in the 460 px panel, where the image wrapped it in the old 400 px card. The panel around the box is the framed panel of [[US-146-match-the-routing-panel-frame-to-the-mockup|US-146]].
5. Not checked: the real text of `route/departures` ([[US-055-prove-the-engine-on-the-server-and|US-055]] holds it), fonts (Mac browser against Linux container), and 390x844, where no approved design exists. At 390x844 the "wait until" line wraps to two lines, and the sheet shows no drag handle in the no-route state. The owner decides whether the missing handle counts as a difference.
6. Left for `Done`: the server rebuild, a server screenshot, and the update of [[floodmap-frontend]].
