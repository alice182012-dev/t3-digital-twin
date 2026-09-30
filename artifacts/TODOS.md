# TODOS

This file holds one daily section and a backlog. The daily section lists what to do today, one
item at a time, with a manual check after each. An item that is not finished by the end of the
day moves to the backlog. A finished item is deleted, because the day's log
(`artifacts/logs/`) and the sprint plan already record it.

## Today, 2026-09-30

Sprint 2 has no open blocker, so today starts the stories of Sprint 3 (2026-10-05 to 2026-10-11) that
nothing else gates. Every coordinate in a test stays inside the model border (see the `CLAUDE.md`
section "Test points stay inside the model border").

### 1. Show no route and a clear message when a mode has none

**What:** Fix both causes in [[failed-route-shows-previous-mode-route]]. In `server.py`
(`_handle_route`), pass GraphHopper's error body through so the response has `message` and `hints`.
In `stores/RouteStore.ts`, reset the route on `RouteRequestFailed`. Cover the store with a unit test,
and cover the walking-then-car scenario with a stub backend, because the live flood that produced
the failure changes and the run is pruned after 8 runs. Then check the live server while the flood
still blocks the pair `21.014103,105.764718` to `21.014534,105.768982`.

**Why:** This is the P1 safety gap. A car driver sees a walking route under the car icon and reads no
error. It is also the same class of bug as [[flood-routing-vehicle-type-always-motorbike]].

**Effort:** S (human ~half a day / CC ~1 hr)
**Priority:** P1
**Depends on:** None. `test_server.py` asserts `payload["error"]` for other errors, so check which of
those cover the `/route` proxy before changing the response shape.

**Blocker tracking:** [[failed-route-shows-previous-mode-route]]

**Sprint:** 3, [[frontend-polish]] Story 4, in [[sprint-plan]].

Status:: active

### 2. Show the depth at each turn-by-turn step

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

**Sprint:** 3, [[frontend-depth-features]] Story 2, in [[sprint-plan]].

Status:: active

### 3. Tap a turn step to highlight its segment on the map

**What:** Clicking a turn-by-turn instruction row highlights that segment on the map. Reuse the
click handler of `RHButton` (`floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx:508-531`),
which dispatches `PathDetailsElevationSelected` (highlights a segment) and `SetBBox` (zooms and
pans to it).

**Why:** It is not in the mockup, but the app already has this pattern for route-hint buttons, so it
is cheap once item 2 gives each step a depth.

**Effort:** XS (human ~2-3 hrs / CC ~15 min)
**Priority:** P3
**Depends on:** Item 2.

**Sprint:** 3, [[frontend-depth-features]] Story 4, in [[sprint-plan]].

Status:: active

## Backlog

Every item here is unfinished and not scheduled for today. Pull an item into the daily section when
it starts.

### Sprint 3 stories not yet started

- **Per-point depth badges along the route** ([[frontend-depth-features]] Story 3, P0, M, Sprint 3).
  The largest Sprint 3 row. Start it after today's item 2, since it decides where depth changes along
  the polyline and needs the same lookup.
- **Route to a place from the place popup** ([[mockup-screen-coverage]] Story 1, P1, S, Sprint 3).
  Reuse the route-to action in `ContextMenuContent.tsx`.
- **Verify screens 2a, 2c, and 2d against the mockup** ([[mockup-screen-coverage]] Story 2, P2, S,
  Sprint 3). The last Sprint 3 row on purpose: one pass checks the finished screens, and it needs the
  frontend rebuilt on the remote host.

### Time-aware routing (P1)

[[routing-not-time-aware]] is a P1 safety gap. Research is done: industry practice and the academic
literature (2026-09-28), an engine survey for Option C, and a build plan that keeps GraphHopper
(2026-09-29), all in that blocker page. It still needs your decision on the approach (A-prime first,
then C-lite if a measurement justifies it) and the trip-time bound.

**Blocker tracking:** [[routing-not-time-aware]]

**Sprint:** the stories are in [[sprint-plan-2]] (Sprints 5 to 8) and [[sprint-plan-3]] (Sprints 9 and 10).

Status:: active

### Backend hardening and validation for the GraphHopper flood-road backend

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

**Sprint:** 5, [[carried-over-backlog]] Story 3 (the soak and the comparison), in [[sprint-plan-2]] (2026-10-19 to 2026-10-25).

Status:: active

### Loading is very slow

**What:** Flagged on 2026-09-08 as "very slow" with no further detail. See [[sample_rate_1_bottleneck]]
memory (SAMPLE_RATE=1 pipeline perf facts) for a measured characterization of a related slowness.
Confirm whether this note refers to the same bottleneck before treating it as a separate issue.

**Sprint:** 4, [[carried-over-backlog]] Story 4, in [[sprint-plan]].

Status:: needs-revalidation
**Priority:** unknown (needs revalidation)

### Address autofill and geolocation search for the user

**What:** User should be able to search for a place via autofill geolocation data.

**Context:** `floodmap/graphhopper-maps/src/sidebar/search/AddressInputAutocomplete.tsx` and
`AddressInput.tsx` already exist, suggesting this may already be implemented. Confirm the actual
UX still matches the ask before treating it as open. Likely closeable.

**Sprint:** 3, absorbed by [[mockup-screen-coverage]] Story 2, in [[sprint-plan]].

Status:: needs-revalidation
**Priority:** unknown (needs revalidation)

### Accessibility spec for Phase A's new interactive elements

**What:** Keyboard nav, ARIA roles, touch target sizing, and contrast requirements for
`MapModeToggle`, `FloodLegend`, and the route tabs (for example `role="tablist"` and `"tab"` with
arrow-key navigation, `aria-pressed` on the toggle, `aria-selected` on the active tab, 44px minimum
touch targets, 4.5:1 minimum contrast on legend text).

**Why:** Nothing in the plan requires these elements to be keyboard-operable or
screen-reader-friendly. Surfaced by `/plan-design-review`'s Pass 6 (Responsive and Accessibility).

**Effort:** S (human ~1-1.5 hrs / CC ~20-30 min)
**Priority:** P2
**Depends on:** Phase A implementation existing to audit against.

**Sprint:** 4, [[carried-over-backlog]] Story 1, in [[sprint-plan]].

Status:: active

### Establish a project DESIGN.md

**What:** Run `/design-consultation` to establish a project DESIGN.md with real design tokens
(colors, typography, spacing scale).

**Why:** Plans calibrate against a one-off approved mockup HTML file, read manually each review,
rather than a reusable, versioned token set. The risk is drift as more screens get built without a
shared vocabulary.

**Effort:** M (human ~half day / CC ~1-2 hrs)
**Priority:** P3
**Depends on:** None.

**Sprint:** 11, [[carried-over-backlog]] Story 2, in [[sprint-plan-3]] (2026-11-30 to 2026-12-06).

Status:: active
