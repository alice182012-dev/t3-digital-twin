---
date: 2026-09-30
type: plan
status: done
tags: [plan, frontend, us-058, us-038, sprint-3]
related: ["[[EP-05-mockup-screen-coverage|mockup-screen-coverage]]", "[[EP-07-carried-over-backlog|carried-over-backlog]]", "[[SP-01-prd-and-backlog|sprint-plan]]", "[[2026-09-30]]", "[[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]]"]
---

# Plan: the rest of 2026-09-30

Two rows of Sprint 3 are still open, and this plan finishes both today. Both are in `TODOS.md` (items 10 and 12).
Nothing else is scheduled for Sprint 3. Every coordinate in a test stays inside the model border (`.claude/CLAUDE.md`).

## Order

1. `US-038`, the acceptance check. It takes minutes and closes the last `Reviewed` row that is not a build.
2. `US-058`, the build. It is the main work of the afternoon.

## 1. US-038: check the drift fix ([[EP-07-carried-over-backlog|carried-over-backlog]] Story 7)

1. Compare the variables in `.env.example` with the ones `compose.yml` reads. The lists must match, with `THREEDI_API_PERSONAL_API_TOKEN` present and `VALHALLA_PORT` and `FLOODMAP_FRONTEND_PORT` absent.
2. Search the repository outside `artifacts/raw/` for `[[SW Architecture]]`. No match may remain.
3. Confirm the 3Di orchestration page states `*/15` and `max_active_runs=2` once.
4. Confirm every file that `PINNED_COMMIT.md` lists exists.
5. Render the command output to an image with its capture time and host, save it under `artifacts/docs/user-stories/evidence/`, and move `US-038` and [[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]] to `Done` and `resolved`.

## 2. US-058: the second tap fills From ([[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 5)

The rules are in the story. In short: with a set destination and an empty From, a tap fills From and still opens the popup. The arrow then moves that point to To and empties From.

Design notes from reading the code:

- `App.tsx` receives every tap through `onPlaceClick={floodMode ? setPlaceCoordinate : undefined}`. The tap rule belongs there, next to `routeToPlace`.
- The place name comes from `GET /places/reverse` inside `PlaceDepthPopup`, after the tap. So the tap fills From with the coordinates at once. When the name arrives and From still holds that same point, From takes the name.
- `destinationForPlace` always moves the last query point. Add a pure function beside it that chooses the point a tap fills, and one that builds the arrow's result.

Steps:

1. Write failing tests in `test/floodmap/routeToPlace.test.ts` first. Cases: tap with a set destination and empty From fills From. Tap with both empty changes nothing. Tap with both set changes nothing. The arrow after an auto-fill moves the point to To and empties From. The arrow with both set keeps the `US-023` result.
2. Add the pure functions and wire them in `App.tsx`. Open the routing panel on the filling tap.
3. Run the frontend tests and the type check.
4. Build a preview on the server, as for `US-057`. Test with 21.0250, 105.7550 as the destination and 21.0255, 105.7620 as the second tap, which routed on 2026-09-29. Confirm From fills, the popup shows the depth, the route is planned, and the arrow empties From.
5. Move the story to `Reviewed`, deploy, repeat the check on the live site, save two screenshots, and move it to `Done`.

## Not scheduled today

`US-025` and `US-026` sit in Sprint 4, which the user placed. They have no dependency, so they could start today. Moving them into Sprint 3 needs the user's answer first (`.claude/CLAUDE.md`, rule 10).

## Status history

- **2026-09-30, active.** Plan written after the day was logged in [[2026-09-30]].
- **2026-09-30, done.** `US-038` and `US-058` are `Done`, both with evidence. `US-025` and `US-026` moved to Sprint 3 and are not built. The `US-058` live check found a side effect, now `US-059`.
