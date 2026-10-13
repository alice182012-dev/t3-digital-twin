---
date: 2026-10-13
type: sprint
sprint_id: "SPR-015"
sprint: 15
start_date: 2026-10-13
end_date: 2026-10-25
status: active
tags: [sprint]
related: ["[[scrum-framework]]", "[[Velocity]]", "[[SPR-014-finish-the-remaining-backend|SPR-014]]", "[[EP-19-frontend-against-the-mockup|EP-19]]", "[[decision-log|D-051]]"]
---

# SPR-015 Sprint 15: Match the frontend to the mockup

## Sprint goal

Match the frontend to the approved mockup: the live app is compared with screens 2a to 2f at 1366x768, every difference is fixed or logged, and the demo flood banner, the route panel, and the two missing states (no route, "wait until") are built.

Chosen by the product owner on 2026-10-13 ("Frontend against the mockup").  The owner confirmed the wording on 2026-10-13.

## Planning

- **Dates.** The sprint runs from Tuesday 2026-10-13 to Sunday 2026-10-25, which is 13 days. It ends on the Sunday that the calendar of [[decision-log|D-026]] gave to [[SPR-014-finish-the-remaining-backend|SPR-014]], so Sprint 16 still starts on Monday 2026-10-26., confirmed by the owner on 2026-10-13 ([[decision-log|D-051]]).
- **Velocity.** [[SPR-014-finish-the-remaining-backend|SPR-014]] gave 45 points in two days, and [[SPR-013-prove-the-storm-replay-and-finish-the-replay-stories|SPR-013]] gave 10 in one day ([[Velocity]]). The owner set the forecast at 45 points.
- **Picks.** Sixteen stories make 35 points, which is 10 under the forecast. The backlog holds no more `Ready` frontend work: [[US-083-build-a-mobile-version-of-screen-2e|US-083]] (an L) was split into a layout part and [[US-143-build-the-mobile-version-of-screen-2e|US-143]], and nothing else of [[EP-19-frontend-against-the-mockup|EP-19]] is left. Stories that come up in the sprint fill the gap.
- **Left out.** [[US-141-host-photon-for-vietnam-next-to-the-backend|US-141]] is on hold by the owner's decision of 2026-10-13. [[US-061-show-the-place-name-faster-after-a|US-061]] waits for it, and the owner set it to the lowest priority. [[US-114-prove-the-real-rain-archive-and-measure-growth|US-114]] waits for real rain.
- **Order and risk.** [[US-076-compare-the-live-app-with-the-mockup|US-076]] comes first, because six stories depend on its screenshots and its list of differences. Its output can add stories, which enter the sprint only if they threaten the goal. [[US-082-show-the-travel-time-and-the-maximum|US-082]] starts with a check of the cost of one depth request for each tab. [[US-083-build-a-mobile-version-of-screen-2e|US-083]] and [[US-084-design-the-no-route-and-wait-until|US-084]] need the owner's approval of a design before their build.
- **Two backend stories.** [[US-142-stop-the-standing-flood-chain-when-the-depths-stop-changing|US-142]] is the action of the last retrospective, and it is the only story that touches the pipeline. [[US-131-show-the-demo-flood-banner-and-the-pinned-frame|US-131]] reads the backend of [[US-130-serve-the-forecast-mode-and-read-the-pinned-step|US-130]], which is `Done`.
- **Work in progress.** At most two stories are `In progress` at once.

| Order | Story | Title | Estimate | Points | Depends on |
| ----- | ----- | ----- | -------- | ------ | ---------- |
| 1 | [[US-076-compare-the-live-app-with-the-mockup\|US-076]] | Compare the live app with the mockup in Aside at 1366x768 | M | 3 | none |
| 2 | [[US-077-match-the-depth-chart-columns-and-the\|US-077]] | Match the depth chart columns and the route tab text to screen 2e | S | 2 | US-076 |
| 3 | [[US-078-show-the-place-names-on-the-start\|US-078]] | Show the place names on the start and destination pins | S | 2 | US-076 |
| 4 | [[US-084-design-the-no-route-and-wait-until\|US-084]] | Design the no-route and "wait until" states, then match the UI | M | 3 | US-076 |
| 5 | [[US-131-show-the-demo-flood-banner-and-the-pinned-frame\|US-131]] | Show the demo flood banner and the pinned frame | M | 3 | none |
| 6 | [[US-085-time-out-a-route-request-in-the\|US-085]] | Time out a route request in the client | S | 2 | none |
| 7 | [[US-142-stop-the-standing-flood-chain-when-the-depths-stop-changing\|US-142]] | Stop the standing-flood chain when the depths stop changing | S | 2 | none |
| 8 | [[US-098-show-the-recommended-route-and-the-through\|US-098]] | Show the recommended route and the through-water option | S | 2 | US-076, US-084 |
| 9 | [[US-081-draw-a-second-dashed-line-for-the\|US-081]] | Draw a second dashed line for the selected mode's depth limit | S | 2 | US-077 |
| 10 | [[US-082-show-the-travel-time-and-the-maximum\|US-082]] | Show the travel time and the maximum depth on each route tab | M | 3 | US-077 |
| 11 | [[US-079-name-the-page-floodmap-and-remove-the\|US-079]] | Name the page Floodmap and remove the Powered by GraphHopper line | XS | 1 | none |
| 12 | [[US-080-keep-as-of-and-bring-the-us\|US-080]] | Keep "As of" and bring the US-007 record in line | XS | 1 | none |
| 13 | [[US-008-switch-the-search-geocoder-s-default-locale\|US-008]] | Switch the search geocoder's default locale to vi | S | 2 | none, `Reviewed` |
| 14 | [[US-083-build-a-mobile-version-of-screen-2e\|US-083]] | Design a mobile layout of screen 2e | S | 2 | US-077, US-078, US-082 |
| 15 | [[US-143-build-the-mobile-version-of-screen-2e\|US-143]] | Build the mobile version of screen 2e | M | 3 | US-083 |
| 16 | [[US-033-write-a-project-design-md-with-real\|US-033]] | Write a project DESIGN.md with real design tokens | S | 2 | US-077 to US-083 |
| | | Total | | 35 | |

- **Open decisions.** None.

## Sprint backlog

```dataview
TABLE title AS "Story", kind AS "Kind", priority AS "Priority", estimate AS "Estimate", status AS "Status", epic AS "Epic"
FROM "docs/stories"
WHERE sprint = 15
SORT priority ASC, file.name ASC
```

## Review

Fill this on 2026-10-25. Walk through each story that is `Done` by its evidence screenshot, and record the product owner's accept or reject.

- **Goal met:** yes or no, with one sentence.
- **Points delivered:** N of 45 forecast.
- **Not done:** each story that left the sprint, back to the backlog with `sprint` cleared.
- **Estimate misses:** each `Done` story whose size was clearly wrong, with the number it should have had (1, 2, 3, or 5). Check that the reference stories in [[scrum-framework]] still fit.

## Retrospective

Three bullets and one action. Check the last retrospective's action first: [[US-142-stop-the-standing-flood-chain-when-the-depths-stop-changing|US-142]] gives the standing-flood chain a stop test.

- **Worked:**
- **Did not work:**
- **Action:** a story, a rule change, or an `L-nnn` lesson.

## Refinement for the next sprint

The top of the backlog after this review: the order, the stories split, and the questions to answer.

## Status history

- **2026-10-13, active.** Planned right after [[SPR-014-finish-the-remaining-backend|SPR-014]] ended early ([[decision-log|D-051]]). Sixteen stories are picked with `sprint: 15`, and they make 35 points against a forecast of 45.
