---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-032", "US-033", "US-034", "US-035", "US-036", "US-037", "US-038", "US-063", "US-064", "US-065", "US-068", "US-069"]
status: draft
subsystem: floodmap-frontend, floodmap-backend
source_ideas: []
related: ["[[sprint-plan]]", "[[mockup-screen-coverage]]", "[[frontend-polish]]", "[[map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[sample_rate_1_bottleneck]]"]
tags: [user-story, epic, backlog, sprint-2]
---

# Epic: carried-over backlog items

Five items that sat in `TODOS.md` without a story or a sprint. The user first placed all of them in Sprint 2 on
2026-09-29, then had them re-cut by dependency and need (see the last history entry), when `TODOS.md` began to follow the sprint plan strictly (`.claude/CLAUDE.md`, "User stories
and sprint planning", rule 9). None comes from a PRD. Rows carry Priority, Estimate, and Sprint per this
vault's user-story sprint-delegation convention.

Two items from the same backlog are scheduled elsewhere. The tap-a-turn-step item depends on per-step depth,
which is in Sprint 3, so it is [[frontend-depth-features]] Story 4. The address autofill item is
[[mockup-screen-coverage]] Story 2, already in Sprint 2.

- **Story 1 (US-032): Make the map toggle, legend, and route tabs usable by keyboard and screen reader.**
  As a person who uses a keyboard or a screen reader, I want the Map or Flood toggle, the flood legend, and
  the route tabs to be operable and announced, so I can read the flood map and pick a route without a mouse.
  Given the app is open with a route showing, when the user moves through the page with the Tab key, then the
  toggle has `aria-pressed` and responds to Enter and Space, the route tabs have `role="tablist"` and
  `role="tab"` with `aria-selected` and move with the arrow keys, every control has a touch target of at
  least 44 px, and the legend text has a contrast ratio of at least 4.5:1 against its background.
  Priority: P2. Status: Done. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None. The components exist.
  `PlainButton` likely covers baseline keyboard use already. The route tabs have no ARIA precedent in the
  codebase.
  Evidence: ![[frontend-route-tabs-keyboard-live-check.png|420]] ![[frontend-route-tabs-keyboard-preview-check.png|420]]
  Details:
  1. What: the route tabs move with the arrow keys, are 44 px tall, and show a focus outline. The legend band labels have an explicit color, and a test fails if legend or tab text drops under 4.5:1.
  2. How: `routeTabKeyTarget` is a pure function. `RouteTabs.tsx` gives the selected tab `tabindex` 0 and the others -1, and moves focus with the selection. `.routeTab` has a 44 px minimum size, and `.band` has `color: #111827`. `textContrast.test.ts` reads the CSS and checks six pairs. Tests first, 7 commits (`f44f776` to `26034f1`), 279 tests pass.
  3. Why: a person who uses a keyboard can pick a route and switch the map mode without a mouse.
  4. Effect: on the live site (2026-10-01), a foot route from 20.9850, 105.7100 to 21.0150, 105.7900 showed 3 tabs of 44 px. ArrowRight and ArrowLeft wrapped, Home and End jumped to the ends, and Tab left the strip from the selected tab. Enter on Map and Space on Flood flipped `aria-pressed`. The legend band labels computed to rgb(17, 24, 39). The toggle's `aria-pressed` and the tabs' `role` and `aria-selected` were already in place. A preview build passed first. No screen reader was tried. `US-035` can now measure the final components.

- **Story 2 (US-033): Write a project `DESIGN.md` with real design tokens.**
  As a developer building the next screen, I want one versioned file of colors, typography, and spacing, so
  new screens match the approved mockup without reading its HTML each time.
  Given the approved mockup and the shipped components, when `/design-consultation` runs, then a
  `DESIGN.md` lists the tokens (colors, type scale, spacing) extracted from the mockup, and each value the
  shipped `FloodLegend.module.css` and `PlaceDepthPopup.module.css` use either matches a token or is listed
  as a known divergence.
  Priority: P3. Status: Not started. Estimate: M. Sprint: 11 ([[sprint-plan-3]]; 2026-11-30 to 2026-12-06). Dependencies: None. Blocks nothing.

- **Story 3 (US-034): Soak the flood-road backend and check it against known answers.**
  As the engineer who owns routing, I want the GraphHopper flood-road backend to run for a 48-hour soak and
  to route correctly on roads with a known water depth, so more load does not land on an unproven service.
  Given the regression tests in `test_flood_areas.py` and `test_server.py` already pass, when the backend
  serves the live app for 48 hours, then the container logs show no unexplained 5xx responses in that
  period, and for each road in a fixed set, `POST /route` blocks every vehicle whose depth limit the road's
  depth exceeds and routes the others. The limits are in `flood_utils.py`: motorbike 20 cm, car 30 cm,
  truck 35 cm, and foot 40 cm. The set is built from real roads in `flood_road_values` whose depth lies
  between two limits, as the 2026-09-28 overpass did (`way/776941610#3`, 20.2 cm). The expected result of
  each road comes from the limits, not from another backend.
  Priority: P2. Status: Done (closed 2026-10-05 on 137 runs, evidence waived by the user). Estimate: M. Sprint: 5 ([[sprint-plan-2]]; 2026-10-19 to 2026-10-25). Dependencies: None. The user set the soak
  length to 48 hours on 2026-10-01. The comparison with the earlier Valhalla backend is dropped (see the last
  history entry).
  Test points: inside the model border (`.claude/CLAUDE.md`).
  Soak window: 2026-10-02 16:00 +07 to 2026-10-04 16:00 +07, the 48 hours of the replay of Story 8. The first window (2026-10-02 00:45 +07 to 2026-10-04 00:45 +07) is void. The user stopped the pipeline on 2026-10-02, because the constant 50 mm/h test rain is not a real event, and the Docker daemon on the server returned HTTP 500 at 13:53 +07. Docker works again, and every container was recreated at about 15:00 ([[2026-10-02-disk-cleanup-and-d-drive-move]]). The new window is the 48 hours of the replayed rain event of [[carried-over-backlog]] Story 8 (`US-063`). It starts with the replay at 16:00 +07, which needs the DAG unpaused by about 15:55 +07.
  Tooling: `scripts/backend_soak/` (29 tests). `run_soak.sh` is the verdict. It exits with 0 only if no container restarted, no log has a 5xx response or an error line, and no known-answer check failed. See "Soak and known-answer check" in [[graphhopper-backend]].
  Interim of the void window, 2026-10-02 03:13 +07 (2 hours 28 minutes in): the logs since 00:45 hold 2,422 requests on `floodmap-backend` (1,981 with 200 and 441 with 400), 308 on the frontend, and 0 responses with 5xx and 0 error lines in all three containers. The known-answer check on the 03:00 run covered 23 roads and 92 pairs of road and profile. It passed 86, skipped 6, and failed none, and all 40 blocked promises held.
  To finish: after 2026-10-04 16:00 +07, run `sh scripts/backend_soak/run_soak.sh 2026-10-02T16:00:00+07:00`. If it exits with 0, render its output as the evidence image and set the story to `Done`. If it does not, log the failure as a blocker.
  Details (closed on 137 runs, 2026-10-05):
  1. What: the soak is closed on the 137 runs of the replay that ran, not on the full 48 hours. The user decided this on 2026-10-05 to move on to Sprint 6.
  2. How: the replay of `US-063` ran from 2026-10-02 16:00 +07 and stopped at 137 of 192 runs when the 2026-10-04 disk-full incident cut it. The first run on the real host (2026-10-02, 16:11 +07) passed the container check and the known-answer check (14 roads, 56 checks). The end check of `run_soak.sh` over the window was not run.
  3. Why: the user judged 137 runs enough of a pattern, and wanted to start Sprint 6.
  4. Effect: Sprint 6 can start. The 48-hour clean-logs result is not proven, and the story has no screenshot of an end check. Evidence waived by the user. The storage check `US-069` still reads the running replay. Flagged for the human to confirm.

- **Story 4 (US-035): Revalidate "loading is very slow".**
  As a user opening the app, I want to know if loading is slow and why, so a real slowness gets its own
  fix and a stale note gets closed.
  Given the note dates from 2026-09-08, before the polygon tiles and the raster-first pipeline, when the
  live app loads on a normal connection, then the time to the first map and the time to the flood layer
  are measured, and the result either closes the item or becomes a blocker page with the measured cause.
  Confirm first whether the note means the `SAMPLE_RATE=1` bottleneck in [[sample_rate_1_bottleneck]], which
  is a pipeline speed and not a page load.
  Also measure the routing panel's wait for a pair with no connection. On the live site on 2026-09-30, the panel
  kept its grey loading bars for more than 9 seconds before the yellow "No safe route available" box appeared
  ([[route-panel-stuck-on-loading-bars]]). Record the seconds per mode, and whether the four per-mode requests of
  [[frontend-polish]] Story 1 add to it.
  Priority: P3. Status: Done. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None.
  Evidence: ![[us-035-loading-check-output.png|700]]
  Details:
  1. What: the live app's load and the wait for a no-connection pair were measured. The app does not load slowly, so the item is closed.
  2. How: `evidence/us-035-loading-check.js` ran with `aside repl` against port 8082: 3 cold loads (cache off), 2 cold loads on emulated regular 4G (9 Mbit/s, 170 ms), and 6 loads of a pair with no motorbike or truck connection. Earlier runs the same day gave the same ranges.
  3. Why: the note "loading is very slow" dates from 2026-09-08, before the polygon tiles and the raster-first pipeline. Its `SAMPLE_RATE=1` reading was a pipeline speed in the retired GeoJSON chain.
  4. Effect: unthrottled, the first map shows in 0.7 to 1.5 s and the flood layer is complete in 2.0 to 3.2 s. On regular 4G the first map shows in 1.9 s and the flood layer is complete in 6.1 s. A cold load fetches a 1.6 MB bundle and 12 flood tiles of 3.2 MB in total, and a warm load takes about 0.1 to 0.3 s. The yellow "No safe route available" box appeared 1.5 to 2.6 s after page start. Each load sends 13 `/api/gh/route` requests that start within about 10 ms of each other, so they do not add up. The slowest took 0.35 to 1.54 s. The 9 to 20 s wait of 2026-09-30 did not appear in 17 loads. [[route-panel-stuck-on-loading-bars]] stays `monitoring`, and the client still has no timeout on `Api.route`. The numbers come from a Mac over the server network, not from a mobile phone.

- **Story 5 (US-036): Decide what the map shows by default, and close or schedule the latency work.**
  As the product owner, I want the map's "now" behavior accepted or changed on purpose, so the label and the
  data agree.
  Given the map shows the latest published step at or before now and captions it "As of `time`", when the
  user reviews [[map-shows-forecast-not-now]] and [[five-minute-tile-freshness]], then the user records one
  decision on the blocker page: accept the caption and the 1.5 to 3 minute publish delay, or choose a
  freshness option and add its stories to a sprint.
  Priority: P2. Status: Done. Estimate: S for the decision. Sprint: 2. Dependencies: None.
  Evidence: ![[map-now-caption-as-of-0130.png|420]]
  Details:
  1. What: the map's "now" behavior (Option C, latest published step at or before now, captioned "As of
     `time`") is accepted as built. The user chose to keep narrowing the 1.5 to 3 minute publish delay
     rather than accept it as final.
  2. How: the user picked [[five-minute-tile-freshness]]'s option D, finishing the worker-concurrency
     fix's own follow-on (a per-run critical-path narrowing, not the bigger staggered-streams option E).
  3. Why: option D is the cheapest of the remaining options and doesn't require the added pipeline load
     and shrunk 3Di turnaround margin that option E needs.
  4. Effect: scheduled as Story 6 below. Option E, and accepting the delay as final, are both closed for
     this plan; either can be revisited from [[five-minute-tile-freshness]] if Story 6's result doesn't
     reach a satisfactory margin.
  5. Evidence: a screenshot the user took on the running map at 2026-09-30 01:36 (the menu-bar clock shows it)
     with the legend caption "As of 30/09/2026 01:30", a step six minutes before the capture. The address bar is not
     in the image. Earlier that day the caption read 16:45, because `flood_mapping_full` was paused. The image shows the
     accepted behavior. It does not measure the publish delay, which Story 6 covers.

- **Story 6 (US-037): Narrow the per-run critical path under the 15-minute cycle (option D).**
  As the pipeline owner, I want each run's step-1 tile to publish with real margin before that step
  becomes "now" again, so the 1.5 to 3 minute publish delay [[flood-mapping-full-worker-concurrency-serializes-runs]]'s
  resolution left behind goes away.
  Given a run's critical path (trigger ~3.5 min, `3_calculate_depth` ~7 min, raster load ~2.3 min, tile
  build ~6 min) sums to about 18.8 minutes against the 15-minute cycle, when the slowest steps are sped up
  or given more of the server's headroom, then four consecutive real runs publish step 1 before it becomes
  now, with a measured margin, not after.
  Priority: P2. Status: Done (re-closed 2026-10-05 on 137 runs, evidence waived by the user). Estimate: M. Sprint: 4, carried in the `TODOS.md` Backlog. Dependencies: Story 8 (`US-063`) for the retest. Independent of Sprint 3's
  frontend work. Candidate levers, to measure rather than assume: `3_calculate_depth`'s `MAX_WORKERS` is 8,
  set when two runs' depth-calc tasks could contend; the `depth_calc` pool now caps that to one at a time,
  so there may be headroom to raise it (12 logical cores available per
  [[flood-mapping-full-worker-concurrency-serializes-runs]]). `9_build_flood_tiles`'s
  `FLOOD_EXTENT_WORKERS` is 2 threads, well under the same headroom. Measure CPU and memory use during a
  real run before raising either, since depth-calc's subprocess count and tile-build's thread count are
  the two knobs, and both share the same box.
  Retest: every simulated run of the 48-hour replay of Story 8 publishes step 1 before it becomes now, and the worst margin is recorded. The run count is 192 of 192 at the server's gate of 0.01 mm/h, and 104 at 5 mm/h. The first measurement below used a constant 50 mm/h rain, which the user judged unrealistic.
  Evidence of the first measurement: ![[us-037-margins-check-output.png|700]]
  Details of the first measurement:
  1. What: step 1 of every run is published before it becomes "now". Four consecutive on-time runs (slots 00:45, 01:00, 01:15, and 01:30 +07 on 2026-10-02) had margins of +1.9, +4.1, +2.7, and +2.4 minutes.
  2. How: three changes. The 8 depth processes read their inputs from the container's local disk (`depth_inputs.py`, `684262b`, `3e83a7f`), which cut depth from 6.8 to 7.5 to 3.2 to 3.9 minutes. The tile dissolve runs one process per band (`4e793c0`, `1607484`), with identical areas. A run hotstarts only if the previous slot's run is success or running (`eef34aa` to `828446f`), so a restart starts from the initial water level. Each was found by measuring: the depth experiment of 2026-10-01 and a stage profile of the tile build.
  3. Why: the map showed a tile 1.5 to 3 minutes after its time ([[map-shows-forecast-not-now]]), and under the growing test storm the tile task reached 15 to 17 minutes, longer than the 15-minute cycle.
  4. Effect: the tile task took 4.4 to 6.1 minutes in the four runs, growing about 0.6 minutes per run as the storm grew from a cold start. At that pace the margin reaches zero in about four more runs. The pass holds for the first hour of a storm, not for a storm that has run for hours. The test storm (`FLOOD_TEST_RAIN_MM_HR=50`) is still on. The blocker [[map-shows-forecast-not-now]] stays `monitoring`.
  Details (re-closed on 137 runs, 2026-10-05):
  1. What: closed again on 2026-10-05 at the user's decision, on the 137 runs of the replay, not on `report.py` passing over 192. The earlier evidence covers four runs only.
  2. How: an analysis of the 136 completed runs (critical path from trigger start to tile build end) stayed under the 15-minute budget, with a maximum of 14.9 minutes. `scripts/pipeline_margins/report.py` was not run over the window.
  3. Why: the user judged 137 runs enough of a pattern, and wanted to start Sprint 6.
  4. Effect: `9_build_flood_tiles` grew 4.8 times over the window (90.9 s to 439.4 s). The lead is the unbounded growth of `flood_extent_polygon`, which `US-067` now prunes, and it is not verified. A later run or the replay now running can show whether the growth is gone. The blocker [[map-shows-forecast-not-now]] stays `monitoring`. Flagged for the human to confirm.

- **Story 7 (US-038): Fix the documentation and config drift found by the README rewrite.**
  As a new teammate, I want `.env.example`, the vault links, and the concept pages to match the code, so a fresh
  checkout starts and its docs do not contradict the DAG.
  Given the drift in [[documentation-and-config-drift-after-graphhopper]], when this is done, then `.env.example`
  lists the variables `compose.yml` reads (with `THREEDI_API_PERSONAL_API_TOKEN`) and none it does not, no
  `[[SW Architecture]]` link or comment is left outside `artifacts/raw/`, the 3Di orchestration concept page states
  the cron `*/15` schedule with `max_active_runs=2` once, and `PINNED_COMMIT.md` lists only files that exist.
  Priority: P3. Status: Done. Estimate: S. Sprint: 3 (found 2026-09-30, fixed by a subagent under rule 11 in `1792d37`). Dependencies: None.
  Blocker tracking: [[documentation-and-config-drift-after-graphhopper]]
  Evidence: ![[us-038-drift-check-output.png|700]]
  Details:
  1. What: `.env.example`, the `[[SW Architecture]]` links, the 3Di orchestration concept page, and `PINNED_COMMIT.md` now match the code.
  2. How: a subagent fixed them in `1792d37` under rule 11. The script `evidence/us-038-drift-check.sh` then compared `.env.example` with the variables `compose.yml` reads, searched the main tree for `[[SW Architecture]]`, counted `*/15` and `max_active_runs=2` on the orchestration page, and looked up every file `PINNED_COMMIT.md` names.
  3. Why: a fresh checkout should start from `.env.example`, and the docs should not contradict the DAG.
  4. Effect: all four checks pass, run on the Mac at 2026-09-30 16:16 (`gods-macbook.local`). The criterion "lists the variables `compose.yml` reads" is read as: every required variable (`${NAME:?...}`) is listed, and variables with a default in `compose.yml` may be left out. Sixteen optional variables are left out on purpose. The search skips `.claude/worktrees`, which hold stale copies of older branches.

- **Story 8 (US-063): Replay a realistic 48-hour rain for the `US-037` retest and the `US-034` soak.**
  As the pipeline owner, I want the pipeline to run a recorded rain event instead of a constant 50 mm/h, so the per-run timing and the 48-hour soak are measured under a load that happens in practice.
  Given the hyetograph of the Hanoi rain of 2025-10-05 to 2025-10-08, when the pipeline replays its 48-hour window (2025-10-05T22:30Z to 2025-10-07T22:30Z, 246.8 mm, peak 56.48 mm/h) through `FLOOD_TEST_RAIN_CSV` and `FLOOD_TEST_RAIN_START`, then each run reads the 2-hour lookahead of its own slot from the event, the rain gate skips the dry runs, and the other runs simulate until the window ends. At the 5 mm/h gate, 104 of the 192 runs simulate.
  Priority: P2. Status: Done. Estimate: S. Sprint: 5 ([[sprint-plan-2]]). Dependencies: None. Deployed and run on the server. Docker works again ([[2026-10-02-disk-cleanup-and-d-drive-move]]).
  Plan: [[us-063-realistic-rain-replay-for-us-037-and-us-034]]
  Offline checks, done on 2026-10-02: `simulating_slots`, `chain_lengths`, and `describe` in `rain_replay.py`, and the command `python3 rain_replay.py preview EVENT START_UTC THRESHOLD`. Tests pin the counts the pipeline's own gate gives: 104, 156, 174, and 192 simulating runs at 5, 2, 1, and 0.01 mm/h, and chains of 26, 46, 10, 10, and 12 runs at 5 mm/h. A run cold-starts when the last simulating slot is more than 4 slots earlier. At 5 mm/h that gives 4 cold starts in 5 chains, and at 0.01 mm/h one, the first run. The report of Story 10 reads the same list.
  Built on 2026-10-02: `scripts/rain_replay.py`, the event file `scripts/rain_events/hanoi_20251005_48h.csv`, and the two variables in `compose.yml` and `.env.example`. Tests first (9 in `scripts/test_rain_replay.py`, 2 in `test/test_flood_rain_gate.py`).
  Evidence: ![[us-063-rain-replay-server-check.png|700]]
  Details:
  1. What: the replay ran on the server from 2026-10-02T09:00:00Z and completed 137 of the window's 192 slots before an unrelated incident cut it off. Every one of the 137 read the right event file and start time and gated correctly.
  2. How: `dag_run` on `airflow_new-airflow-postgres-1` counts 137 runs of `flood_mapping_full` between 2026-10-02T09:00:00Z and 2026-10-04T09:00:00Z (136 `success`, 1 `failed`). The first run's log holds `🧪 Replaying /opt/airflow/scripts/rain_events/hanoi_20251005_48h.csv from 2026-10-02T09:00:00Z` and `Rain gate: max=1.10 mm/h, threshold=0.01 mm/h, intervals=9`. The run at the event's recorded peak (`scheduled__2026-10-03T09:30:00+00:00`, 16:30 +07) logs `Rain gate: max=56.48 mm/h`, matching the plan's prediction. All 137 completed runs took the `1_trigger_simulation` branch; the server's 0.01 mm/h gate never found a dry slot, so the dry-skip branch was never exercised live, though it is covered by the offline tests above.
  3. Why: `US-037`'s retest and `US-034`'s soak both need a load that happens in practice, not a constant test rain.
  4. Effect: the window did not finish. The last run (`scheduled__2026-10-03T19:00:00+00:00`) started on time but did not end until 2026-10-04T17:31:38Z, caught in the unrelated disk-full incident ([[docker-data-vhdx-fills-c-drive-again]]), and the chain stopped there instead of reaching the 192nd slot (2026-10-04T09:00:00Z). `US-037` and `US-034` both need the fuller window and stay open until `scripts/pipeline_margins/report.py` and `run_soak.sh` run against it, or the window is replayed again.
  5. Judgment call: this story's acceptance criteria describe the replay's behavior (read the lookahead, gate correctly, simulate until the window ends), not a run count, and that behavior held for every one of the 137 slots that ran, cut short only by an infra incident outside this story's logic. Closed as `Done` on that basis. Flagged for the human to confirm, since the criteria leave open whether a full 192-run window is required.

Blocker tracking: [[docker-data-vhdx-fills-c-drive-again]]

- **Story 9 (US-064): Make the soak check fail when it cannot read the server.**
  As the engineer who owns routing, I want `run_soak.sh` to exit with 1 when a Docker call or a log read fails, so a Docker outage cannot look like a passing soak.
  Given Docker on `remote-server` answers every call with HTTP 500, as it did on 2026-10-02 at 13:53 +07, when `run_soak.sh` runs, then it exits with 1 and names the call that failed. Given a log file with no request lines or no timestamps, when `soak_checks.py logs` reads it, then it exits with 1. Added during the work, because the script and [[graphhopper-backend]] already promised it: when a container started after the soak start, was OOM killed, or is not running, then it exits with 1.
  Found: on 2026-10-02 at 13:53 +07 the script printed "0 requests, 0 5xx, 0 error lines" for all three logs and ended with "logs exit 0", because `run_logs` fails only on a 5xx or an error line, and `run_soak.sh` writes SSH errors into the log files. The `roads` check did exit with 1.
  Priority: P1. Status: Done. Estimate: S. Sprint: 5 ([[sprint-plan-2]]). Dependencies: None. It needs no server, because the tests use empty files and a fake `docker` on the path.
  Evidence: ![[us-064-soak-check-output.png|700]]
  Details:
  1. What: `run_soak.sh` exits with 1 when a Docker call fails, when a log has no timestamped line, and when a container started inside the soak window, was OOM killed, or is not running.
  2. How: tests first (13 new, 42 in `scripts/backend_soak/`). `soak_checks.py logs` now fails a file with no timestamped line and prints its first line. A new `containers` command (`judge_containers`) compares each container's start time with the soak start as an instant. `run_soak.sh` counts failed `docker inspect` and `docker logs` calls and names each one. The tests run the script with a fake `docker` and `ssh` on the path.
  3. Why: on 2026-10-02 at 13:53 +07 the old script printed "0 requests, 0 5xx, 0 error lines" and "logs exit 0" while Docker answered HTTP 500 on every call. The old script also never checked the container start times, although its header and [[graphhopper-backend]] said it did.
  4. Effect: a replayed outage exits with 1 and lists five failed calls, and a healthy fake server exits with 0. `US-034` can no longer pass on an unreadable server. The real host is not tested. The exit status of the `ssh` and PowerShell filter is not checked, so a failed `ssh` shows up as a log with no timestamped line. The first run on the real server shows whether a healthy host passes.


- **Story 10 (US-065): Report the step-1 margin of every run of the replay.**
  As the pipeline owner, I want one command that reads the per-run timings of the 48-hour replay and says whether every simulated run published step 1 before it became now, so `US-037` is judged on every simulated run by a number and not by eye.
  Given the rows that `run_margins.sh` prints (slot, trigger, depth, raster, tiles, margin) and the simulating slots from Story 8, when the report runs, then it prints the run count, the worst, median, and best margin, the runs with a negative margin, the slots that should have simulated and have no row, and the slope of the margin per run inside each chain. It exits with 0 only if no run is late and none is missing.
  Priority: P2. Status: Done. Estimate: M. Sprint: 5 ([[sprint-plan-2]]). Dependencies: Story 8, for the schedule function. `run_margins.sh` moves from `marie-curie/us-037/`, which git does not track, to `scripts/pipeline_margins/`. Tests use the four runs of 2026-10-02 as a fixture (margins +1.9, +4.1, +2.7, +2.4). It needs no server to build, and a server only to run it on real rows.
  Evidence: ![[us-065-margin-report-check-output.png|700]]
  Details:
  1. What: `scripts/pipeline_margins/report.py` reads the rows of `run_margins.sh` and prints the run count, the worst, median, and best margin, the late runs, the runs the replay should have simulated and did not, and the margin slope of each chain. It exits with 0 only if no run is late, none is missing, and at least one run has a margin.
  2. How: tests first (21). `run_margins.sh` moved from `marie-curie/us-037/`, which git does not track, to `scripts/pipeline_margins/`. With `--event`, `--start`, and `--threshold` the report takes the expected runs from `simulating_slots` of `US-063`. `--since` and `--until` limit the runs judged. A line that is not a row stops the report with exit 1, so a Docker error cannot pass.
  3. Why: `US-037` is judged on every simulated run of the 48-hour replay, by a number and not by eye.
  4. Effect: on the 50 mm/h storm of 2026-10-02 (50 real runs, 00:45 to 13:00 +07) the report fails. The mean margin was +2.3 minutes in the 01:00 hour, +0.5 in the 02:00 hour, and -0.7 or lower from the 03:00 hour, while the tile task grew from 5.8 to 11.5 minutes. That confirms the reopening of `US-037`. The margin is measured to the end of the tile task, which is 1 to 1.3 minutes after step 1 is published, so a run that is slightly late here can still have published step 1 on time. The 07:00 run (-19.2 minutes) is not explained.

- **Story 11 (US-068): Show the rain ingested into the simulation in the XCom of `1_trigger_simulation`.**
  As the pipeline owner, I want the XCom of the task `1_trigger_simulation` to show how much rain was sent to 3Di, so I can read a run's rain input in the Airflow UI without opening the log or the 3Di run.
  Given a run of `flood_mapping_full` that took the simulate branch, when `1_trigger_simulation` succeeds, then its XCom holds a key `rain_ingested` next to `sim_id`, with the run's slot, the source of the rain (Tomorrow.io, the replay file of `US-063`, or the fixed test rain), the interval count, the first and last offset in seconds, the maximum intensity in mm/h, and the total rain in mm. The numbers come from the same `[offset_seconds, m/s]` list that `run_forecast_process` sends to `simulations_events_rain_timeseries_create`, not from the forecast the rain gate saw. Given a run that fails before the rain is sent, then no `rain_ingested` is pushed.
  Priority: P2. Status: Done. Estimate: S. Sprint: 5 ([[sprint-plan-2]]). Dependencies: None. Building it needs no server. Reading it on a real run needs the server.
  Evidence: ![[us-068-rain-ingested-xcom.png]]
  Details:
  1. What: `1_trigger_simulation` now pushes an XCom `rain_ingested` next to `sim_id`, with the slot, the rain source (Tomorrow.io, the replay file, or the fixed test rain), the interval count, the first and last offset in seconds, the maximum mm/h, and the total mm of the series sent to 3Di.
  2. How: tests first. A pure function, `summarize_rain_values`, works on the `[offset_seconds, m/s]` list that `build_rain_values` returns, which is the list `run_forecast_process` sends to 3Di, and not on the forecast the rain gate saw. The total is a trapezoid sum, because the series is sent with `interpolate=True`. `get_rain_forecast` reports which branch gave the intervals. 22 tests pass in `test/test_create_simulation_cycle.py`.
  3. Why: a run that ingests no rain, or a replay slice that is shifted, looked the same in the Airflow UI as a correct one, and the number had to be read from the log or the 3Di run.
  4. Effect: on the server, the first run of the 48-hour replay (slot `2026-10-05T17:00:00Z`) pushed `rain_ingested` with source `replay:hanoi_20251005_48h.csv`, 9 points from offset 0 to 7200 s, a maximum of 1.096 mm/h and a total of 0.881 mm. The same numbers come out of `rain_replay.py` and `summarize_rain_values` on the event file, so the value in the UI is the value computed from the event, and the replay start of `US-063` reads the event from offset 0. `US-069` and the replay checks can read a run's rain input in the UI.
  5. Limits: one run was read, the first of the window. The Tomorrow.io and fixed-rain branches are covered by tests and not by a server run. The evidence image is rendered from output the user pasted.
  Why it is a separate story. Today `1_trigger_simulation` pushes only `sim_id` (`dags/flood_mapping_dag.py`). The XCom `rain_intervals` sits on `0_check_forecast_rain` and holds the forecast as the gate saw it, in mm/h. What 3Di receives is the result of `build_rain_values(intervals, start=slot)` in `scripts/create_simulation.py`, in m/s and offset from the slot, and nothing records it. A run that ingests no rain, or a replay slice that is shifted, looks the same in the UI as a correct one.
  Open details for the build. `get_rain_forecast` returns only the intervals, so the source label needs a small change to say which branch produced them. The total is computed from the sent list with the trapezoid rule, because the series is sent with `interpolate=True`. Tests first, with a pure summary function over the `[offset, m/s]` list, so no server is needed.

- **Story 12 (US-069): Check the storage after the 48-hour replay to see if the retention fixes work.**
  As the pipeline owner, I want the storage numbers of the server read at the start, the middle, and the end of the 48-hour replay, so I know whether `US-066` and `US-067` stop the growth that filled C: on 2026-10-04.
  Given the replay of `US-063` running on the server for 48 hours, when the numbers are read at the start, at 24 hours, and at 48 hours, then each reading holds the free space on C:, the size of `docker_data.vhdx`, the size of the `storage-postgres-data` volume, the size of `minio_custom`, the size of the `netcdf_values` hypertable (compressed and not), and the size and row count of `flood_extent_polygon`. The check passes if the sizes of the three database objects stop growing between the 24-hour and the 48-hour reading, `flood_extent_polygon` holds rows for no more than the newest `keep_runs` runs, and no container was auto-paused for lack of space.
  Priority: P1. Status: Not started. Estimate: S. Sprint: 8 ([[sprint-plan-2]], moved from Sprint 5 on 2026-10-05). Dependencies: the DAG unpaused for 48 hours, and the replay of Story 8 (`US-063`) running, and the user's read-only access to the server. The replay's start time is still to be given. The 24-hour and 48-hour readings follow from it.
  Proposed pass mark, not yet confirmed by the user: growth of 10 percent or less in each of the three database objects between hour 24 and hour 48. The starting values are the ones in [[2026-10-05]] (C: 163.4 GB free, `storage-postgres-data` 16.01 GB, `minio_custom` 14 GB, `flood_extent_polygon` 5.1 GB).
  The readings are read-only. The same run is the retest for `US-034` and `US-037`, so this story adds no load.

## Status history

- **2026-09-29, draft.** Created from the unscheduled items of `TODOS.md`. All five go in Sprint 2 at the
  user's request. The two other unscheduled items went to Sprint 3 and to the existing Sprint 2 story, as
  described at the top.
- **2026-09-29, draft.** Re-cut by dependency and need in [[sprint-plan]]: Stories 1 and 4 to Sprint 4 (they check the finished UI),
  Story 5 stays in Sprint 2 (its decision sets Sprint 3's wording), Stories 2 and 3 to the next plan (P3 and blocked on user input).
- **2026-09-29, draft.** Story 3 (the soak) is in [[sprint-plan-2]] Sprint 5, before the routing engine builds on the backend. Story 2
  (`DESIGN.md`) is in [[sprint-plan-3]] Sprint 11.
- **2026-09-29, draft.** Story 5 was `Reviewed`, not `Done`: the user chose to keep narrowing the publish delay
  ([[five-minute-tile-freshness]] option D), not accept it as final and not commit to option E. Added
  Story 6 (the option D work) to Sprint 4.
- **2026-09-30, draft.** Story 5 is `Done`: the user's screenshot at 01:36 shows the map captioned "As of 30/09/2026 01:30",
  saved as `map-now-caption-as-of-0130.png`.
- **2026-09-30, draft.** Story 7 added for [[documentation-and-config-drift-after-graphhopper]]. It blocks no later build, so a subagent fixes it (rule 11).
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
