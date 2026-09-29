---
date_drafted: 2026-09-29
type: user-story
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

- **Story 1: Make the map toggle, legend, and route tabs usable by keyboard and screen reader.**
  As a person who uses a keyboard or a screen reader, I want the Map or Flood toggle, the flood legend, and
  the route tabs to be operable and announced, so I can read the flood map and pick a route without a mouse.
  Given the app is open with a route showing, when the user moves through the page with the Tab key, then the
  toggle has `aria-pressed` and responds to Enter and Space, the route tabs have `role="tablist"` and
  `role="tab"` with `aria-selected` and move with the arrow keys, every control has a touch target of at
  least 44 px, and the legend text has a contrast ratio of at least 4.5:1 against its background.
  Priority: P2. Status: Not started. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None. The components exist.
  `PlainButton` likely covers baseline keyboard use already. The route tabs have no ARIA precedent in the
  codebase.

- **Story 2: Write a project `DESIGN.md` with real design tokens.**
  As a developer building the next screen, I want one versioned file of colors, typography, and spacing, so
  new screens match the approved mockup without reading its HTML each time.
  Given the approved mockup and the shipped components, when `/design-consultation` runs, then a
  `DESIGN.md` lists the tokens (colors, type scale, spacing) extracted from the mockup, and each value the
  shipped `FloodLegend.module.css` and `PlaceDepthPopup.module.css` use either matches a token or is listed
  as a known divergence.
  Priority: P3. Status: Not started. Estimate: M. Sprint: 11 ([[sprint-plan-3]]; 2026-11-30 to 2026-12-06). Dependencies: None. Blocks nothing.

- **Story 3: Soak the flood-road backend and compare it with the earlier backend.**
  As the engineer who owns routing, I want the GraphHopper flood-road backend to run for a soak period and
  to match the earlier Valhalla backend on known cases, so more load does not land on an unproven service.
  Given the regression tests in `test_flood_areas.py` and `test_server.py` already pass, when the backend
  serves the live app for a soak period, then the container logs show no unexplained 5xx responses in that
  period, and a side-by-side run of a fixed set of routes and flood scenarios is recorded with the
  differences explained.
  Priority: P2. Status: Not started. Estimate: M. Sprint: 5 ([[sprint-plan-2]]; 2026-10-19 to 2026-10-25). Dependencies: None. Open: the soak length and
  the route set are the user's to set. The Valhalla proof of concept was deleted in commit `5d1a606`, so the
  comparison needs it restored from git history (`6394e27^`).

- **Story 4: Revalidate "loading is very slow".**
  As a user opening the app, I want to know if loading is slow and why, so a real slowness gets its own
  fix and a stale note gets closed.
  Given the note dates from 2026-09-08, before the polygon tiles and the raster-first pipeline, when the
  live app loads on a normal connection, then the time to the first map and the time to the flood layer
  are measured, and the result either closes the item or becomes a blocker page with the measured cause.
  Confirm first whether the note means the `SAMPLE_RATE=1` bottleneck in [[sample_rate_1_bottleneck]], which
  is a pipeline speed and not a page load.
  Priority: P3. Status: Not started. Estimate: S. Sprint: 4 (re-cut 2026-09-29). Dependencies: None.

- **Story 5: Decide what the map shows by default, and close or schedule the latency work.**
  As the product owner, I want the map's "now" behavior accepted or changed on purpose, so the label and the
  data agree.
  Given the map shows the latest published step at or before now and captions it "As of `time`", when the
  user reviews [[map-shows-forecast-not-now]] and [[five-minute-tile-freshness]], then the user records one
  decision on the blocker page: accept the caption and the 1.5 to 3 minute publish delay, or choose a
  freshness option and add its stories to a sprint.
  Priority: P2. Status: Reviewed. Estimate: S for the decision. Sprint: 2. Dependencies: None.
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

- **Story 6: Narrow the per-run critical path under the 15-minute cycle (option D).**
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

## Status history

- **2026-09-29, draft.** Created from the unscheduled items of `TODOS.md`. All five go in Sprint 2 at the
  user's request. The two other unscheduled items went to Sprint 3 and to the existing Sprint 2 story, as
  described at the top.
- **2026-09-29, draft.** Re-cut by dependency and need in [[sprint-plan]]: Stories 1 and 4 to Sprint 4 (they check the finished UI),
  Story 5 stays in Sprint 2 (its decision sets Sprint 3's wording), Stories 2 and 3 to the next plan (P3 and blocked on user input).
- **2026-09-29, draft.** Story 3 (the soak) is in [[sprint-plan-2]] Sprint 5, before the routing engine builds on the backend. Story 2
  (`DESIGN.md`) is in [[sprint-plan-3]] Sprint 11.
- **2026-09-29, draft.** Story 5 is `Reviewed`, not `Done`: the user chose to keep narrowing the publish delay
  ([[five-minute-tile-freshness]] option D), not accept it as final and not commit to option E. Added
  Story 6 (the option D work) to Sprint 4.
