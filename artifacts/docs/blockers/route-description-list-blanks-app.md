---
date_open: 2026-09-30
date_closed: 2026-09-30
type: blocker
status: resolved
severity: P0
subsystem: floodmap-frontend
approaches_tried: 1
approaches_remaining: 0
tags: [blocker, frontend, routing, crash]
related: ["[[frontend-polish]]", "[[graphhopper-backend]]", "[[mockup-screen-coverage]]"]
last_updated: 2026-09-30
---

# A route whose description is a list blanks the whole app

## Description

When a route response carries `"description": ["Đường Hoàng Tùng"]`, the app throws
`TypeError: (intermediate value).trim is not a function` and the page goes blank (the React root has no
children). `buildRouteTabs` in `floodmap/graphhopper-maps/src/sidebar/routingResultsView.ts` calls
`(path.description ?? '').trim()`, and the typed field is a string, but GraphHopper returns a list of
strings when it has a description for the path.

Found on 2026-09-30 while checking the place popup's route button. Reproduction on the live backend: a
foot route from `21.0000,105.7450` to `20.998932,105.740422` at the 02:15 step returns
`"description": ["Đường Hoàng Tùng"]` on one request and no `description` on the next, and the panel
crashes on the first. A response with no `description`, or an empty string, does not crash, which is why
most routes work.

Probably the cause of the blank pages seen earlier in this sprint: after typing into the From field, and
after a long wait when the app re-planned a route. The console showed no error then, because the error is
an uncaught exception, not a logged one.

## Why this matters

Any route with a description takes the entire UI down, not only the panel. A user loses the map, the
legend, and the routing state, and has to reload. It is not specific to any story: it was in the route
tabs since [[frontend-polish]] Story 1.

## Approaches tried

### Approach 1: read the description as text or a list (2026-09-30)

`descriptionText` in `routingResultsView.ts` returns the text of a string, the parts of a list joined with a
comma and a space, and an empty string for anything else. Four new tests in `routingResultsView.test.ts`
failed with the production error, `trim is not a function`, before the change and pass after it. All 233
frontend tests pass. On a preview build on the server, a response with `["Đường Hoàng Tùng"]` shows the tab
"Đường Hoàng Tùng" and the app stays up. Deployed and confirmed on the live site.

## Candidate approaches

1. **Read the description as a string or a list.** In `routingResultsView.ts`, turn a list into one
   string (joined with a comma and a space) and anything else that is not a string into `''`, in one
   helper used by both places that read `path.description`. Frontend change, XS.

## Decision and explanation

Approach 1 shipped on 2026-09-30 (`5d08b99`). On the live site, a route response with `["Đường Hoàng Tùng"]` shows the tab "Đường Hoàng Tùng" and the app stays up. ![[frontend-route-description-list-live-check.png|420]]

## Related topics

- [[frontend-polish]], Story 5

## Status history

- **2026-09-30, open.** Found with a live-backend response. Cause read in `routingResultsView.ts` and
  confirmed in the built bundle. No fix attempted yet.
- **2026-09-30, monitoring.** Fix built and checked on a preview build, see Approaches tried. Moves to `resolved` once it is deployed and checked on the live site.
- **2026-09-30, resolved.** Deployed at `5d08b99` and checked on the live site.
