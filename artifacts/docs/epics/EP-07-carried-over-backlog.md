---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-032", "US-033", "US-034", "US-035", "US-036", "US-037", "US-038", "US-063", "US-064", "US-065", "US-068", "US-069"]
status: draft
subsystem: floodmap-frontend, floodmap-backend
source_ideas: []
related: ["[[SP-01-prd-and-backlog|sprint-plan]]", "[[SP-04-frontend-recheck|sprint-plan-4]]", "[[EP-05-mockup-screen-coverage|mockup-screen-coverage]]", "[[EP-02-frontend-polish|frontend-polish]]", "[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[sample_rate_1_bottleneck]]"]
tags: [user-story, epic, backlog, sprint-2]
---

# Epic: carried-over backlog items

Five items that sat in `TODOS.md` without a story or a sprint. The user first placed all of them in Sprint 2 on
2026-09-29, then had them re-cut by dependency and need (see the last history entry), when `TODOS.md` began to follow the sprint plan strictly (`.claude/CLAUDE.md`, "User stories
and sprint planning", rule 9). None comes from a PRD. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention.

Two items from the same backlog are scheduled elsewhere. The tap-a-turn-step item depends on per-step depth,
which is in Sprint 3, so it is [[EP-01-frontend-depth-features|frontend-depth-features]] Story 4. The address autofill item is
[[EP-05-mockup-screen-coverage|mockup-screen-coverage]] Story 2, already in Sprint 2.

- [[US-032-make-the-map-toggle-legend-and-route|US-032]] Make the map toggle, legend, and route tabs usable by keyboard and screen reader. Story 1.
- [[US-033-write-a-project-design-md-with-real|US-033]] Write a project `DESIGN.md` with real design tokens. Story 2.
- [[US-034-soak-the-flood-road-backend-and-check|US-034]] Soak the flood-road backend and check it against known answers. Story 3.
- [[US-035-revalidate-loading-is-very-slow|US-035]] Revalidate "loading is very slow". Story 4.
- [[US-036-decide-what-the-map-shows-by-default|US-036]] Decide what the map shows by default, and close or schedule the latency work. Story 5.
- [[US-037-narrow-the-per-run-critical-path-under|US-037]] Narrow the per-run critical path under the 15-minute cycle (option D). Story 6.
- [[US-038-fix-the-documentation-and-config-drift-found|US-038]] Fix the documentation and config drift found by the README rewrite. Story 7.
- [[US-063-replay-a-realistic-48-hour-rain-for|US-063]] Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak. Story 8.
- [[US-064-make-the-soak-check-fail-when-it|US-064]] Make the soak check fail when it cannot read the server. Story 9.
- [[US-065-report-the-step-1-margin-of-every|US-065]] Report the step-1 margin of every run of the replay. Story 10.
- [[US-068-show-the-rain-ingested-into-the-simulation|US-068]] Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`. Story 11.
- [[US-069-check-the-storage-after-the-48-hour|US-069]] Check the storage after the 48-hour replay to see if the retention fixes work. Story 12.

## Status history

- **2026-09-29, draft.** Created from the unscheduled items of `TODOS.md`. All five go in Sprint 2 at the
  user's request. The two other unscheduled items went to Sprint 3 and to the existing Sprint 2 story, as
  described at the top.
- **2026-09-29, draft.** Re-cut by dependency and need in [[SP-01-prd-and-backlog|sprint-plan]]: Stories 1 and 4 to Sprint 4 (they check the finished UI),
  Story 5 stays in Sprint 2 (its decision sets Sprint 3's wording), Stories 2 and 3 to the next plan (P3 and blocked on user input).
- **2026-09-29, draft.** Story 3 (the soak) is in [[SP-02-routing-engine-foundations|sprint-plan-2]] Sprint 5, before the routing engine builds on the backend. Story 2
  (`DESIGN.md`) is in [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]] Sprint 11.
- **2026-10-07, draft.** Story 2 (`US-033`) moved from Sprint 11 to Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request, so the tokens come from the UI that the stories of [[EP-11-frontend-mockup-recheck|frontend-mockup-recheck-stories]] finish.
- **2026-10-08, draft.** Story 2 (`US-033`) moved out of Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request to finish the routing first. Its dependencies `US-077` to `US-083` are in Sprints 13 to 16 of [[SP-04-frontend-recheck|sprint-plan-4]], so it carries to plan 5. The user asked for Sprint 13. Rule 3 puts it after `US-083`, so the user is asked to confirm.
- **2026-09-29, draft.** Story 5 was `Reviewed`, not `Done`: the user chose to keep narrowing the publish delay
  ([[five-minute-tile-freshness]] option D), not accept it as final and not commit to option E. Added
  Story 6 (the option D work) to Sprint 4.
- **2026-09-30, draft.** Story 5 is `Done`: the user's screenshot at 01:36 shows the map captioned "As of 30/09/2026 01:30",
  saved as `map-now-caption-as-of-0130.png`.
- **2026-09-30, draft.** Story 7 added for [[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]]. It blocks no later build, so a subagent fixes it (rule 11).
- **2026-09-30, draft.** Story 7 (`US-038`) moved to `Reviewed`: the fix landed as `1792d37`. The acceptance check and its screenshot are still to do.
- **2026-09-30, draft.** Story 7 (`US-038`) is `Done`: the check script passes and its output is saved as `us-038-drift-check-output.png`.
- **2026-09-30, draft.** Story 4 (`US-035`) also measures the routing panel's wait for a no-connection pair, after the 9-second loading bars seen on the live site.
- **2026-10-01, draft.** Story 3 (`US-034`) lost its Valhalla comparison. The user said the Valhalla model was wrong when it ran, so a match or a mismatch with it proves nothing. The story now checks GraphHopper against the vehicle depth limits, and the soak length is set to 48 hours. The title changed from "compare it with the earlier backend" to "check it against known answers". Restoring Valhalla from `6394e27^` is no longer needed. The only input the user owed, the soak length, is given, so the Sprint 5 gate is cleared.
- **2026-10-01, draft.** Story 1 (`US-032`) is `In progress`. A check of the code found the toggle's `aria-pressed` and the tabs' `role` and `aria-selected` already in place, and the legend title contrast at 4.83:1. The gaps are arrow-key movement and roving `tabindex` on the route tabs, tab height (about 27 px against 44 px), and an explicit color on the legend band labels. Plan: [[us-032-keyboard-and-screen-reader-access]].
- **2026-10-01, draft.** Story 1 (`US-032`) is `Reviewed`: the route tabs move with the arrow keys (`routeTabKeyTarget`, roving `tabindex`, focus follows selection), the tabs are 44 px with a focus outline, the legend band labels have an explicit color, and a CSS test fails if any legend or tab text drops under 4.5:1. Commits `f44f776` to `26034f1` (279 tests pass). No browser check yet.
- **2026-10-01, draft.** Story 1 (`US-032`) is `Done`: deployed after the user's push and checked on the live site with screenshots (`frontend-route-tabs-keyboard-live-check.png`, `frontend-route-tabs-keyboard-preview-check.png`).
- **2026-10-01, draft.** Story 4 (`US-035`) is `Done`: measured on the live app with Aside, no slow load found, and the 9 to 20 s no-connection wait of 2026-09-30 did not reproduce in 17 loads. Evidence: `us-035-loading-check-output.png`.
- **2026-10-01, draft.** Story 6 (`US-037`) is `In progress`. The user unpaused `flood_mapping_full` at 18:19 +07 and kept the test rain. Baseline from 8 recorded runs: step 1 published 1.6 to 6.8 minutes after it became now. Measuring first, then one knob at a time. Plan: [[us-037-narrow-the-per-run-critical-path]].
- **2026-10-01, draft.** Story 3 (`US-034`) is in Sprint 5, which started today. `US-037` is not a dependency, but the soak should start after the `US-037` knob settles, so the 48 hours run under one worker configuration. Story 6 (`US-037`) stays `In progress` in Sprint 4.
- **2026-10-02, draft.** Story 6 (`US-037`) is `Done`: four consecutive on-time runs published step 1 with margins of +1.9, +4.1, +2.7, and +2.4 minutes. Evidence: `us-037-margins-check-output.png`.
- **2026-10-02, draft.** Story 3 (`US-034`) is `In progress`. The user gave the soak start as 2026-10-02 00:45 +07, so the 48 hours end on 2026-10-04 00:45 +07. The logs since then were retrieved from the containers, and the tooling in `scripts/backend_soak/` found no 5xx and no failed check at the 2 hour 28 minute mark. A first version of the check failed 3 of 120 pairs because of long GraphHopper edges, recorded in [[graphhopper-backend]].
- **2026-10-02, draft.** Story 6 (`US-037`) moved from `Done` back to `In progress`. The user stopped the pipeline, because a constant 50 mm/h rain that never stops is not a real event, and the margins shrank about 0.6 minutes per run under it. The four-run pass stays recorded as the first measurement. The retest runs under Story 8.
- **2026-10-02, draft.** Story 3 (`US-034`) lost its soak window. The user stopped the pipeline, and Docker on the server returned HTTP 500. The soak restarts under the replay of Story 8 and ends 48 hours after the replay starts.
- **2026-10-02, draft.** Story 8 (`US-063`) added, in Sprint 5, at the user's request. The user named the event file. The unit in the file the user first named was unclear, so the source hyetograph settled it: the values are mm per 30 minutes, and the pipeline takes `precipitation_mm_hr`, which is twice as large.
- **2026-10-02, draft.** Story 8 (`US-063`): the pipeline's own gate gives 104 simulating runs of 192 at 5 mm/h, not the 98 first written. The first count used a different lookahead alignment. The counts at 2 and 1 mm/h are 156 and 174.
- **2026-10-02, draft.** Stories 9 (`US-064`) and 10 (`US-065`) added to Sprint 5 at the user's request, to plan the work that needs no server. Story 9 came from the false pass of `run_soak.sh` during the Docker outage.
- **2026-10-02, draft.** Story 9 (`US-064`) is `Done`: `run_soak.sh` exits with 1 when a Docker call fails, a log has no timestamped line, or a container started inside the window. 42 tests pass in `scripts/backend_soak/`. Evidence: `us-064-soak-check-output.png`, rendered from a replay of the 13:53 outage on the Mac.
- **2026-10-02, draft.** Docker on the server works again after a disk cleanup, a restart of `com.docker.service`, and a move of `./data` and the `airflow-logs` volume to `D:` ([[2026-10-02-disk-cleanup-and-d-drive-move]]). Stories 3, 6, and 8 wait for the user's go on the server, not for Docker.
- **2026-10-02, draft.** Story 8 (`US-063`) is deployed. The server pulled `c3d398e` at 15:20 +07, and the recreated worker reads `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START=2026-10-02T09:00:00Z`, with `FLOOD_TEST_RAIN_MM_HR` empty. The server's `.env` sets the rain gate to 0.01 mm/h, not the compose default of 5, so all 192 runs of the window simulate. `flood_mapping_full` was paused until the user unpauses it. Story 3 (`US-034`) now has its window, 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07.
- **2026-10-02, draft.** Story 8 (`US-063`): the schedule preview is built (tests first, 16 in `scripts/test_rain_replay.py`). At the server's gate of 0.01 mm/h the window is one chain of 192 runs, and only the first run cold-starts.
- **2026-10-02, draft.** Story 10 (`US-065`) is `Done`. Run on 50 real runs of the 50 mm/h storm (2026-10-02 00:45 to 13:00 +07), the report fails. The mean margin was +2.3 minutes in the 01:00 hour, +0.5 in the 02:00 hour, and -0.7 or lower from the 03:00 hour, as the tile task grew from 5.8 to 11.5 minutes. Evidence: `us-065-margin-report-check-output.png`. The margin is measured to the end of the tile task, 1 to 1.3 minutes after step 1.
- **2026-10-02, draft.** Story 6 (`US-037`) stays `In progress` by the user's decision. It is tested on every run of the 48-hour replay (Story 8), and it is `Done` only when `scripts/pipeline_margins/report.py` passes over the whole window. The default pass mark applies (no margin below 0 minutes at the end of the tile task) until the user sets another.
- **2026-10-02, draft.** Story 9 (`US-064`), first run on the real host at 16:11 +07: the container check passed, the known-answer check passed (14 roads, 56 checks), and the logs check exited with 1 for an empty GraphHopper log, because no request had come in since 16:00. The message wrongly said the read failed, and it now names both causes (`e07c4ea`). The story stays `Done`.
- **2026-10-05, draft.** Story 6 (`US-037`) stays `In progress`. The Story 8 replay stopped early at 137 of the intended 192 runs (last one 2026-10-03 19:00 UTC, a stale run ended during an unrelated disk incident), so the window is incomplete, and nobody has run `scripts/pipeline_margins/report.py` (this story's own pass check) against it yet. A separate cut of the same data, each run's critical path end to end over the 136 completed runs, stayed under the 15-minute budget throughout (max 14.9 min), unlike the stress-test baseline, but `9_build_flood_tiles` alone grew 4.8x over the window (90.9 s to 439.4 s) with no cross-run overlap to explain it. An unverified lead: `flood_extent_polygon` had no retention and grew unbounded for the entire window before a same-day manual fix, and if `9_build_flood_tiles` reads that table, its growth is a plausible cause. Full numbers and the open follow-up in [[us-037-narrow-the-per-run-critical-path]].
- **2026-10-05, draft.** Story 11 (`US-068`) added to Sprint 5 at the user's request: the XCom of `1_trigger_simulation` should show the rain ingested into the simulation. The user chose Sprint 5 and a summary (not the full series) in the XCom.
- **2026-10-05, draft.** The user said the replay is running again and will be checked after 48 hours. Story 12 (`US-069`) added to Sprint 5 at the user's request, to check the storage after the 48 hours. `US-034`, `US-037`, and this story all read the same window.
- **2026-10-05, draft.** Stories 3 (`US-034`) and 6 (`US-037`) are `Done` at the user's decision, on the 137 runs of the replay, so Sprint 6 can start. Neither has its end check (`run_soak.sh`, `report.py`) or a new screenshot, and the user waived the evidence. The Details of each say so.
- **2026-10-05, draft.** Story 12 (`US-069`) moved to Sprint 8 at the user's request: no testing now, continue after Sprint 7. Story 11 (`US-068`) is `Reviewed`: the XCom is built and tested (22 tests pass). The acceptance check on a real DAG run waits for the DAG to be unpaused.
- **2026-10-08, draft.** Story 12 (`US-069`) is checked on the 12-hour replay, from hour 6 to hour 12 (D-015). The user decided this. The user confirmed the 10 percent growth mark on 2026-10-08.
