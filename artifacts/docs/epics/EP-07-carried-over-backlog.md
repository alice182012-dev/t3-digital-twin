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

Story-level progress lines up to 2026-10-10 are in [[EP-07-carried-over-backlog-history|the archived history]]. This section keeps plan-level changes only.

- **2026-09-29, draft.** Created from the unscheduled items of `TODOS.md`. All five go in Sprint 2 at the
  user's request. The two other unscheduled items went to Sprint 3 and to the existing Sprint 2 story, as
  described at the top.
- **2026-10-07, draft.** Story 2 (`US-033`) moved from Sprint 11 to Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request, so the tokens come from the UI that the stories of [[EP-11-frontend-mockup-recheck|frontend-mockup-recheck-stories]] finish.
- **2026-10-08, draft.** Story 2 (`US-033`) moved out of Sprint 12 of [[SP-03-engine-in-backend-and-rollout|sprint-plan-3]], at the user's request to finish the routing first. Its dependencies `US-077` to `US-083` are in Sprints 13 to 16 of [[SP-04-frontend-recheck|sprint-plan-4]], so it carries to plan 5. The user asked for Sprint 13. Rule 3 puts it after `US-083`, so the user is asked to confirm.
- **2026-09-29, draft.** Story 5 was `Reviewed`, not `Done`: the user chose to keep narrowing the publish delay
  ([[five-minute-tile-freshness]] option D), not accept it as final and not commit to option E. Added
  Story 6 (the option D work) to Sprint 4.
- **2026-09-30, draft.** Story 7 added for [[BL-015-documentation-and-config-drift-after-graphhopper|documentation-and-config-drift-after-graphhopper]]. It blocks no later build, so a subagent fixes it (rule 11).
- **2026-09-30, draft.** Story 7 (`US-038`) moved to `Reviewed`: the fix landed as `1792d37`. The acceptance check and its screenshot are still to do.
- **2026-10-02, draft.** Story 6 (`US-037`) moved from `Done` back to `In progress`. The user stopped the pipeline, because a constant 50 mm/h rain that never stops is not a real event, and the margins shrank about 0.6 minutes per run under it. The four-run pass stays recorded as the first measurement. The retest runs under Story 8.
- **2026-10-02, draft.** Story 8 (`US-063`) added, in Sprint 5, at the user's request. The user named the event file. The unit in the file the user first named was unclear, so the source hyetograph settled it: the values are mm per 30 minutes, and the pipeline takes `precipitation_mm_hr`, which is twice as large.
- **2026-10-02, draft.** Story 8 (`US-063`): the pipeline's own gate gives 104 simulating runs of 192 at 5 mm/h, not the 98 first written. The first count used a different lookahead alignment. The counts at 2 and 1 mm/h are 156 and 174.
- **2026-10-02, draft.** Stories 9 (`US-064`) and 10 (`US-065`) added to Sprint 5 at the user's request, to plan the work that needs no server. Story 9 came from the false pass of `run_soak.sh` during the Docker outage.
- **2026-10-05, draft.** Story 11 (`US-068`) added to Sprint 5 at the user's request: the XCom of `1_trigger_simulation` should show the rain ingested into the simulation. The user chose Sprint 5 and a summary (not the full series) in the XCom.
- **2026-10-05, draft.** The user said the replay is running again and will be checked after 48 hours. Story 12 (`US-069`) added to Sprint 5 at the user's request, to check the storage after the 48 hours. `US-034`, `US-037`, and this story all read the same window.
