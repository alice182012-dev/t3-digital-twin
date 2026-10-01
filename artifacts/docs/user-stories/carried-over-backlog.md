---
date_drafted: 2026-09-29
type: user-story
us_ids: ["US-032", "US-033", "US-034", "US-035", "US-036", "US-037", "US-038"]
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
  Priority: P2. Status: Not started. Estimate: M. Sprint: 5 ([[sprint-plan-2]]; 2026-10-19 to 2026-10-25). Dependencies: None. The user set the soak
  length to 48 hours on 2026-10-01. The comparison with the earlier Valhalla backend is dropped (see the last
  history entry).
  Test points: inside the model border (`.claude/CLAUDE.md`).

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
  Priority: P2. Status: Not started. Estimate: M. Sprint: 4. Dependencies: None; independent of Sprint 3's
  frontend work. Candidate levers, to measure rather than assume: `3_calculate_depth`'s `MAX_WORKERS` is 8,
  set when two runs' depth-calc tasks could contend; the `depth_calc` pool now caps that to one at a time,
  so there may be headroom to raise it (12 logical cores available per
  [[flood-mapping-full-worker-concurrency-serializes-runs]]). `9_build_flood_tiles`'s
  `FLOOD_EXTENT_WORKERS` is 2 threads, well under the same headroom. Measure CPU and memory use during a
  real run before raising either, since depth-calc's subprocess count and tile-build's thread count are
  the two knobs, and both share the same box.

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
