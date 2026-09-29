---
date_drafted: 2026-09-29
type: prd
status: draft
subsystem: floodmap-backend
source_ideas: ["[[sticky-c-lite-routing]]"]
tags: [prd, routing, graphhopper, forecast, safety]
related: ["[[routing-not-time-aware]]", "[[edge-depth-table]]", "[[departure-time-advice-research]]", "[[graphhopper-backend]]", "[[failed-route-shows-previous-mode-route]]", "[[map-shows-forecast-not-now]]", "[[frontend-todos-and-backend-dependencies]]", "[[time-aware-routing-engine-stories]]", "[[sprint-plan-2]]"]
---

# Time-aware routing engine (sticky C-lite)

## Problem

`POST /route` judges every road at one forecast step, the `valid_time` in the request. A road that is dry
at that step and floods 10 minutes later passes, so a traveller who reaches it in 15 minutes drives into
water. This is scenario 1 in the test table of [[routing-not-time-aware]] and it is a safety fault, not a
tuning issue. GraphHopper cannot fix it alone, because its search carries no arrival time.

Two related gaps sit next to it.

- **No answer to "when should I go?"** When every road is blocked, GraphHopper fails with a
  `ConnectionNotFoundException` (HTTP 400). The user learns nothing about when the route opens.
- **The request time is ignored.** `server.py` never reads the wall clock for routing. The map picks a
  step, and that step can lie in the future ([[map-shows-forecast-not-now]]).

The team compared four tiers and chose sticky C-lite on 2026-09-29. The reasoning, cost-benefit, and
roadmap are in [[sticky-c-lite-routing]]. This PRD turns that choice into requirements. The depth data the
engine reads is the subject of [[edge-depth-table]].

## Goals

Each goal has one testable outcome.

1. **No route crosses a road that is impassable at its arrival step.** For a departure at step `t0`, sticky
   closure applies from `t0`: an edge is impassable at arrival time `a` when its depth reaches the vehicle's
   limit at any forecast step in `[t0, a + margin]`. The margin is 10 minutes and is fixed on the server. The
   offline checker finds zero crossings on the four synthetic scenarios, for `motorbike` and `car`, with and
   without a detour.
2. **The departure step is never before the request time.** The server reads its own clock. `t0` is the later
   of the request's `valid_time` and now, rounded to the step that contains it. A trip that ends after the
   run's last step returns `unknown`, and the response says so.
3. **All four modes have a time-aware profile.** `motorbike`, `car`, `truck`, and `foot` each route through a
   `td` profile that applies the mode's own depth limit to the table's depth.
4. **A flag restores today's behavior exactly.** With the flag off, `POST /route` returns the same body as
   before this work for a fixed request.
5. **A missing, stale, or mismatched depth table falls back safely.** The backend routes with today's
   single-step model and the response carries a flag. The frontend shows "timing check unavailable".
6. **The no-route alert shows "wait until".** When a route request fails with no connection, the client
   requests `POST /route/departures`. The alert shows the earliest clear departure, or says that no clear
   departure appears in the run.
7. **Latency stays inside a factor of today's.** The p50 and p95 of `POST /route` on the server stay within a
   factor the user sets. The baseline comes first.

## Non-goals

- **Arrival-only closure.** A road that drains does not reopen for a traveller who arrives later during the
  same trip. Measuring how many routes this would change is a later item in the backlog.
- **Waiting at intersections.** Forbidding waiting on receding water is NP-hard in general. Only the wait
  at the origin exists, and only through the departure advice.
- **Tier A-prime.** It is not built and stays a reserve option.
- **The map overlay.** `GET /flood/areas` keeps showing one timestep, because the engine reads the depth
  table and not areas.
- **A sweep over alternative routes.** The advice walks one flood-free route. Comparing detours across
  departures waits for a measurement.
- **Saved routes and push alerts.** They need accounts and an alert channel, which do not exist.

## Dependencies and assumptions

Each item is a fact that could turn out false. The first three come from the server or the repo and are
verified. The rest are not.

1. **Verified, 2026-09-29.** GraphHopper 12.0 on the server returns the `edge_id` and `time` path details for a
   route, with the same 199 segments on the test route. It rejects `osm_way_id` ("Cannot find the path
   details"), so the pinned build does not enable that encoded value.
2. **Verified.** `alternative_route` accepts a `custom_model` on the server. This PRD does not depend on it.
3. **Verified.** The repo has no Java, Maven, or Gradle files. The Java toolchain is new work.
4. **Unverified.** The pinned image has the extension points the module needs (a `GraphHopper` subclass, a
   custom weighting, a replaceable search algorithm, a Dropwizard application class). The source revision
   of the pinned image is not recorded.
5. **Unverified.** A weighting that only raises weights keeps LM's lower bounds valid. A unit test settles
   it. If it fails, the search runs without LM and latency must be measured again.
6. **Unverified.** The 2-hour horizon holds for every run, and steps are 15 minutes. The user stated the
   horizon on 2026-09-29. The step length comes from the tile timesteps and is checked in the baseline story.
7. **Assumed, not yet confirmed by the user.** Sticky closure is measured from the departure step, not
   from the first flooded step of the run. Without this wording a road that drained before `t0` stays closed
   and "wait until" cannot help. See Decisions.
8. **Assumed.** A road outside the model reads as clear. The user said on 2026-09-29 that roads outside the
   model do not matter.
9. **Depends on [[edge-depth-table]].** The engine reads depth per edge and step from that table. Until the
   real table exists, the engine is developed and tested against a synthetic table of the same format.
10. **Depends on the frontend.** The alert needs a "no route for this mode" state. Todo 13 in
    [[frontend-todos-and-backend-dependencies]] and [[failed-route-shows-previous-mode-route]] add it. Today
    `RouteStore.ts` has no branch for `RouteRequestFailed`, so a failed request leaves the previous mode's
    route on the map.
11. **Server operations.** Docker runs on the remote host over SSH, whose shell is PowerShell. Local edits
    reach the host only after a push and a pull, and compose commands run on the host with `--no-deps`.

## Definition of done

Run each check on the server, not on a laptop.

1. **Scenario check.** Given the synthetic corridor from [[sticky-c-lite-routing]] and a synthetic table,
   when `POST /route` runs the four scenarios for `motorbike` and `car`, then the results match the
   sticky column of the blocker's test table, and the offline checker finds no route that crosses an
   edge impassable at its arrival step.
2. **Real run.** Given a real run and its depth table, when a route request departs at a step in the run,
   then the route avoids every edge that floods before arrival and the response names the run.
3. **Request time.** Given a request with a `valid_time` earlier than now, when the server handles it, then
   `t0` is the step that contains now. Given a trip that ends after the run's last step, then the response
   marks the answer `unknown`.
4. **Flag off.** Given a fixed request, when the flag is off, then the response body equals the body from
   the commit before this work.
5. **Fallback.** Given a depth table for a different graph hash, when a route request runs, then the backend
   routes with today's model, the response carries the fallback flag, and the log names the mismatch.
6. **Wait until.** Given a scenario where the route drains at 18:00, when the user requests a route at
   17:00 and it fails with no connection, then the alert shows a clear departure at 18:00. Given a clear
   route, then the alert does not appear.
7. **Latency.** The p50 and p95 of `POST /route` on the server for short, medium, and long Hanoi trips are
   within the factor the user set, measured against the baseline story's numbers.
8. **Evidence.** Each story records a screenshot or rendered output, as the sprint plan requires.

## Risks and open questions

- **The image becomes ours to keep working.** The stock pinned image is replaced by an image built from
  our module. A GraphHopper upgrade can break the extension points. Mitigation: keep the version pinned,
  keep the module small, and build it in CI against the pinned version.
- **The fallback reintroduces the fault.** Today's model is the fallback. The response flag and the
  frontend message are what keep this visible. This is a required part of goal 5.
- **Latency is unmeasured.** A unidirectional search visits more nodes than a bidirectional one. Story R1
  records the baseline, and the user sets the factor before the last sprint.
- **The Java toolchain is new.** No build, CI job, or test exists for it. Story R4 builds them.
- **Two depth sources on one screen.** The depth chart reads raster tiles and the engine reads the edge
  table. Both sample the same tiles, but at different spacing. The chart's `max_depth_m` can read lower than
  the depth the router used. The stories do not change the chart. Note it in the chart's documentation.
- **Open question.** What latency factor is acceptable? Needed before the rollout story.
- **Open question.** Does the user confirm the sticky-from-departure wording? Needed before the engine story.
- **Open question.** What exact text does the alert show in each of the three states (clear departure found,
  none in this run, timing check unavailable)? The draft wording is in [[departure-time-advice-research]].

## Decisions

| Date | Question | Decision | Why |
| ---- | -------- | -------- | --- |
| 2026-09-29 | Which routing tier? | Sticky C-lite | Exact under sticky closure, no tuning parameters, and it passes the roads A-prime blocks unnecessarily. See [[sticky-c-lite-routing]]. |
| 2026-09-29 | What answer does the advice give? | "Wait until", the earliest clear departure | The user's product answer. |
| 2026-09-29 | What margin? | 10 minutes, fixed on the server | The user set 5 and then 10. A client cannot pick a smaller margin. |
| 2026-09-29 | When does the check run? | On request, from the client, when a route fails with no connection | No saved routes exist, and stored advice goes stale on every run. |
| 2026-09-29 | Forecast horizon? | 2 hours, and every run covers it | Stated by the user. |
| 2026-09-29 | Roads outside the model? | Read as clear | Stated by the user. |
| 2026-09-29 | Is the departure step ever before now? | No. The server clock decides | A traveller cannot leave in the past. |
| 2026-09-29 | How is sticky measured? | From the departure step (assumed) | Lets the router and the advice agree. Confirm with the user. |
| 2026-09-29 | Where does the advice read depth? | The edge depth table by edge id | The user chose option C for the timeline. `osm_way_id` is not available, so no other exact key exists. |

## Rollback

- Turn the flag off. `POST /route` returns today's behavior.
- Point the compose service back at the pinned stock image.
- Turn off the frontend advice request. The alert then shows its current text.
- The depth table files can stay on disk. Nothing else reads them.

## Status history

- **2026-09-29, draft.** Written from the decisions in [[sticky-c-lite-routing]] and
  [[departure-time-advice-research]]. Stories are in [[time-aware-routing-engine-stories]].
