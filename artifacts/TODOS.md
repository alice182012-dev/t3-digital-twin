# TODOS

This file holds one daily section and a backlog. The daily section lists what to do today, one
item at a time, with a manual check after each. A finished item is set to `Status:: done` with a
one-line result and stays in the daily section for the rest of the day. At the next day's
rollover, done items are deleted, because the logs (`artifacts/logs/`) and the sprint plan
already record them, and unfinished items move to the backlog.

## Today, 2026-09-30

Sprint 2 has no open blocker, so today starts the stories of Sprint 3 (2026-10-05 to 2026-10-11) that
nothing else gates. Every coordinate in a test stays inside the model border (see the `CLAUDE.md`
section "Test points stay inside the model border").

### 1. US-001 Save evidence for the depth forecast chart and hand-check its average

**Result (2026-09-30):** Saved a server screenshot of the chart (`depth-forecast-chart-server-check.png`)
and hand-checked the 17:00 and 18:15 columns against `flood_depth_raster_tile`. Mean depth, maximum
depth, and wet fraction all match the endpoint. [[depth-forecast-chart]] is `Done`. The screenshot
needed a browser clock set to 2026-09-29 17:00 +07:00, because `flood_mapping_full` is paused.

**Sprint:** 3, [[depth-forecast-chart]] (US-001), in [[sprint-plan]].

Status:: done

### 2. US-009 Show no route and a clear message when a mode has none

**Result (2026-09-30):** Fixed both causes in [[failed-route-shows-previous-mode-route]]. `server.py`
passes GraphHopper's error body through, and `RouteStore.ts` clears the route on
`RouteRequestFailed`. Deployed (branch `front-end-according-to-mock-up`, now at `f2c0534`) and checked
on the live UI: car shows no route and "Connection between locations not found", and walking returns
its 760 m route. [[frontend-polish]] Story 4 is `Done`, and the blocker is `resolved`.

**Sprint:** 3, [[frontend-polish]] Story 4 (US-009), in [[sprint-plan]].

Status:: done

### 3. US-003 Show the depth at each turn-by-turn step

**What:** Each step in the expanded instructions list shows its depth next to its distance, for
example "320 m · 8 cm", matching mockup screen 2e ([[frontend-depth-features]] Story 2). Call
`GET /flood/points` for each step's start point with the selected step's `valid_time` and `run`.
Check the wording for a step older than 45 minutes or in the future against
`placeDepth.ts`, so the list never calls a forecast depth the present.

**Why:** A user can see what to expect before reaching each turn. The route badges in the backlog
reuse the same lookup.

**Effort:** S (human ~half a day / CC ~1 hr)
**Priority:** P0
**Depends on:** None. `GET /flood/points` is done, and the pooling and latency stories that this
needed are done (30 concurrent requests all returned 200). Time a route with about 40 steps. Add a
batch endpoint only if that is too slow, as the Sprint 3 risk row says.

**Sprint:** 3, [[frontend-depth-features]] Story 2 (US-003), in [[sprint-plan]].

**Result (2026-09-30):** Built, deployed (`ac1ab84`), and checked on the live frontend. The 17-step car route shows "N m · 0 cm" on every step, and the values match `GET /flood/points` for 22 step start points, including a start point 16 cm deep. [[frontend-depth-features]] Story 2 is `Done`.

Status:: done

### 4. US-005 Tap a turn step to highlight its segment on the map

**What:** Clicking a turn-by-turn instruction row highlights that segment on the map. Reuse the
click handler of `RHButton` (`floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx:508-531`),
which dispatches `PathDetailsElevationSelected` (highlights a segment) and `SetBBox` (zooms and
pans to it).

**Why:** It is not in the mockup, but the app already has this pattern for route-hint buttons, so it
is cheap once item 3 gives each step a depth.

**Result (2026-09-30):** Built, deployed (`448a434`), and checked on the live frontend: clicking a step zooms the map to it and draws it in red, and the step popup still opens. [[frontend-depth-features]] Story 4 is `Done`.

**Effort:** XS (human ~2-3 hrs / CC ~15 min)
**Priority:** P3
**Depends on:** Item 3.

**Sprint:** 3, [[frontend-depth-features]] Story 4 (US-005), in [[sprint-plan]].

Status:: done

### 5. US-004 Show depth badges along the route

**What:** The map shows depth badges at the points along the route where the depth changes, matching the
four badges of mockup screen 2e ([[frontend-depth-features]] Story 3). A badge is a white pill with a dot in
the depth-band color and text such as "22 cm". A new `POST /flood/profile` returns the depth at evenly
spaced samples along the route at the selected timestep, and the frontend picks the badge points. The
plan and the badge rule are in [[route-depth-badges]].

**Why:** A user can spot the flooded stretches on the map itself, not only in the step list.

**Result (2026-09-30):** Built, deployed (`1b80cc3`, backend and frontend), and checked on the live site: a 6.4 km walking route shows 6 badges, `POST /flood/profile` matched separate raster reads on 66 samples, and a mode with no route no longer risks a blank app. [[frontend-depth-features]] Story 3 is `Done`.

**Effort:** M (human ~1 day / CC ~2-3 hrs)
**Priority:** P0
**Depends on:** None. Per-step depth (item 3) is done and the sampling code exists in `flood_forecast.py`.

**Sprint:** 3, [[frontend-depth-features]] Story 3 (US-004), in [[sprint-plan]].

Status:: done

### 6. US-023 Route to a place from the place popup

**What:** The place popup has a route button in its header. Clicking it opens the routing panel with the
place's name as the destination and the start empty, matching mockup screen 2f
([[mockup-screen-coverage]] Story 1). The right-click menu already has a route-to action in
`ContextMenuContent.tsx` to reuse.

**Why:** A user who tapped a place should not retype it in the destination field.

**Result (2026-09-30):** Built, deployed (`5d08b99`), and checked on the live site: the popup's round blue button opens the panel with the place name in To, an empty From stays empty, and a start already set is kept and the route is planned. [[mockup-screen-coverage]] Story 1 is `Done`.

**Effort:** S (human ~half a day / CC ~1 hr)
**Priority:** P1
**Depends on:** None. The place popup is done.

**Sprint:** 3, [[mockup-screen-coverage]] Story 1 (US-023), in [[sprint-plan]].

Status:: done

### 7. US-010 Do not blank the app when a route description is a list

**What:** Fix [[route-description-list-blanks-app]]. `buildRouteTabs` calls `.trim()` on `path.description`,
and the backend can return a list of strings there, so the whole app goes blank. Read the description as a
string or a list of strings, in one helper, with a test first.

**Why:** Found while checking item 6. Any route with a description takes the whole UI down, and it likely
caused the earlier unexplained blank pages.

**Result (2026-09-30):** Fixed test first (four tests reproduced `trim is not a function`), deployed (`5d08b99`), and checked on the live site: a route with a list description shows its tab and the app stays up. [[frontend-polish]] Story 5 is `Done` and [[route-description-list-blanks-app]] is `resolved`.

**Effort:** XS (human ~1 hr / CC ~15 min)
**Priority:** P0
**Depends on:** None.

**Blocker tracking:** [[route-description-list-blanks-app]]

**Sprint:** 3, [[frontend-polish]] Story 5 (US-010), in [[sprint-plan]].

Status:: done

### 8. US-016 Fix test_server.py's tile-edge check

**What:** [[test-server-tile-edge-check-fails]]. The "edge of two tiles" check compares the endpoint with
`gdallocationinfo` at a point 3e-11 pixels off a pixel boundary, and the two break the tie differently. Expect
the pixel that owns the boundary instead ([[point-depth-lookup-backend]] Story 6). Fixed by a subagent under rule 11
while the next work continues.

**Why:** It keeps `test_server.py` a regression pass that ends green, so the checks after the failed one run
again. It blocks no later build and has no effect on production.

**Result (2026-09-30):** A subagent fixed it under rule 11. I reviewed the diff, had it reworked once (one four-pixel rule for both edge points in place of a reference per point), landed it as `03f7aa6`, and reran the script green. [[point-depth-lookup-backend]] Story 6 is `Done` and the blocker is `resolved`. Not pushed yet.

**Effort:** XS (human ~1 hr / CC ~15 min)
**Priority:** P3
**Depends on:** None.

**Blocker tracking:** [[test-server-tile-edge-check-fails]]

**Sprint:** 3, [[point-depth-lookup-backend]] Story 6 (US-016), in [[sprint-plan]].

Status:: done

### 9. US-024 Verify the first-load, empty-panel, and autofill screens against the mockup

**What:** Check screens 2a, 2c, and 2d of the approved mockup against the live app at 1366x768
([[mockup-screen-coverage]] Story 2). 2a is the first load with the "Search Floodmap" pill, Map on, and Flood
off. 2c is the empty routing panel with both inputs and their placeholder text. 2d is the autofill for "C5" and
for "Hồ Gươm", with no result from outside Vietnam. Log every difference as a new story or a blocker. It also
closes the `needs-revalidation` autofill item below and re-verifies the `vi` locale fix.

**Why:** It confirms that these screens match, not only assumes it, now that the Sprint 3 UI stories are deployed.

**Result (2026-09-30):** Compared screens 2a, 2c, and 2d with the live app and logged every difference. The autofill works and every "Hồ Gươm" result is in Vietnam. Found: the app opens in Flood mode where the mockup opens in Map mode (kept on purpose, D-008 in [[decision-log]]), plus two differences added as [[mockup-screen-coverage]] Stories 3 and 4, with no sprint yet. Story 2 is `Done`.

**Effort:** S (human ~half a day / CC ~1 hr)
**Priority:** P2
**Depends on:** The Sprint 3 UI stories, all deployed.

**Sprint:** 3, [[mockup-screen-coverage]] Story 2 (US-024), in [[sprint-plan]].

Status:: done

### 10. US-038 Fix the documentation and config drift

**What:** [[documentation-and-config-drift-after-graphhopper]]. Bring `.env.example`, the `[[SW Architecture]]`
links, the 3Di orchestration concept page, and `PINNED_COMMIT.md` in line with the code
([[carried-over-backlog]] Story 7). Fixed by a subagent under rule 11 while the next work continues.

**Why:** A fresh checkout should start from `.env.example`, and the docs should not contradict the DAG. It blocks
no later build.

**Effort:** S (human ~2 hrs / CC ~30 min)
**Priority:** P3
**Depends on:** None.

**Blocker tracking:** [[documentation-and-config-drift-after-graphhopper]]

**Sprint:** 3, [[carried-over-backlog]] Story 7 (US-038), in [[sprint-plan]].

Status:: active

## Backlog

Every item here is unfinished and not scheduled for today. Pull an item into the daily section when
it starts.

### Time-aware routing (P1)

[[routing-not-time-aware]] is a P1 safety gap. Research is done: industry practice and the academic
literature (2026-09-28), an engine survey for Option C, and a build plan that keeps GraphHopper
(2026-09-29), all in that blocker page. It still needs your decision on the approach (A-prime first,
then C-lite if a measurement justifies it) and the trip-time bound.

**Blocker tracking:** [[routing-not-time-aware]]

**Sprint:** the stories are in [[sprint-plan-2]] (Sprints 5 to 8) and [[sprint-plan-3]] (Sprints 9 and 10).

Status:: active

### US-034 Backend hardening and validation for the GraphHopper flood-road backend

**What:** Harden and validate `floodmap/graphhopper-flood-road/backend/` (`server.py`,
`flood_areas.py`) before or alongside stacking more infrastructure on it.

**Why:** This backend is the result of a single commit (`6394e27`, "replace valhalla with
grasshopper routing logic to embed flood as a cost factor more effectively") with no production
soak time. Later phases add new load and new dependencies on top of it.

**Progress (2026-09-23):** [[point-depth-lookup-backend]]'s Story 1 added
`backend/test_flood_areas.py` and `backend/test_server.py`, a regression pass against a real
PostGIS and a stub GraphHopper. Still open: a soak period and a side-by-side comparison against the
old Valhalla-based backend for known routes and flood scenarios.

**Effort:** M (human ~2-3 days / CC ~4-6 hrs)
**Priority:** P2
**Depends on:** None.

**Sprint:** 5, [[carried-over-backlog]] Story 3 (US-034) (the soak and the comparison), in [[sprint-plan-2]] (2026-10-19 to 2026-10-25).

Status:: active

### US-035 Loading is very slow

**What:** Flagged on 2026-09-08 as "very slow" with no further detail. See [[sample_rate_1_bottleneck]]
memory (SAMPLE_RATE=1 pipeline perf facts) for a measured characterization of a related slowness.
Confirm whether this note refers to the same bottleneck before treating it as a separate issue.

**Sprint:** 4, [[carried-over-backlog]] Story 4 (US-035), in [[sprint-plan]].

Status:: needs-revalidation
**Priority:** unknown (needs revalidation)

### US-025 Match the empty routing panel to screen 2c

**What:** The empty routing panel reads like the mockup's screen 2c: the inputs say "Choose starting point, or click on the map" and "Choose destination", and the mode row lists car, motorbike, walking, and truck in that order ([[mockup-screen-coverage]] Story 3). Whether to keep the settings gear, "Add location", "Settings", and "Powered by GraphHopper" is a product call.

**Effort:** S
**Priority:** P3
**Depends on:** None.

**Sprint:** 4, item US-025, [[mockup-screen-coverage]] Story 3 (US-025), in [[sprint-plan]].

Status:: active

### US-026 Match the autofill rows to screen 2d

**What:** Each autofill suggestion shows a pin icon, the place name in bold, and its district at the right edge, on one line, as in the mockup's screen 2d ([[mockup-screen-coverage]] Story 4). The live rows show the name with the full address on a second line, and up to six rows.

**Effort:** S
**Priority:** P3
**Depends on:** None.

**Sprint:** 4, item US-026, [[mockup-screen-coverage]] Story 4 (US-026), in [[sprint-plan]].

Status:: active

### US-032 Accessibility spec for Phase A's new interactive elements

**What:** Keyboard nav, ARIA roles, touch target sizing, and contrast requirements for
`MapModeToggle`, `FloodLegend`, and the route tabs (for example `role="tablist"` and `"tab"` with
arrow-key navigation, `aria-pressed` on the toggle, `aria-selected` on the active tab, 44px minimum
touch targets, 4.5:1 minimum contrast on legend text).

**Why:** Nothing in the plan requires these elements to be keyboard-operable or
screen-reader-friendly. Surfaced by `/plan-design-review`'s Pass 6 (Responsive and Accessibility).

**Effort:** S (human ~1-1.5 hrs / CC ~20-30 min)
**Priority:** P2
**Depends on:** Phase A implementation existing to audit against.

**Sprint:** 4, [[carried-over-backlog]] Story 1 (US-032), in [[sprint-plan]].

Status:: active

### US-033 Establish a project DESIGN.md

**What:** Run `/design-consultation` to establish a project DESIGN.md with real design tokens
(colors, typography, spacing scale).

**Why:** Plans calibrate against a one-off approved mockup HTML file, read manually each review,
rather than a reusable, versioned token set. The risk is drift as more screens get built without a
shared vocabulary.

**Effort:** M (human ~half day / CC ~1-2 hrs)
**Priority:** P3
**Depends on:** None.

**Sprint:** 11, [[carried-over-backlog]] Story 2 (US-033), in [[sprint-plan-3]] (2026-11-30 to 2026-12-06).

Status:: active
