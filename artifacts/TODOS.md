# TODOS

## Today, 2026-09-28

Working through these one at a time, with a manual check after each before starting the next.

### 1. Run the Stage 2 fifteen-minute-cycle test — done, blocker found, fixed, and confirmed

**What it was:** Trigger two overlapping `flood_mapping_full` runs under `FLOOD_TEST_RAIN_MM_HR`
(15-minute clock, `max_active_runs=2`) to measure the contention risk flagged in
[[fifteen-minute-cycle-tiles-and-histogram]] (risk 3: tiling, raster load, and flood on roads
overlapping at 8 steps, not yet measured across two runs).

**Result (2026-09-28):** Ran at `FLOOD_TEST_RAIN_MM_HR=50`. Runs under overlap took 20 to 37
minutes and the delay compounded run over run (found across two rounds of live testing: no
Airflow `pool=` separated the trigger chain from the heavy tasks, then even after that fix, the
heavy tasks still contended with each other and could oversubscribe the server's CPU). Fixed in two
parts, both deployed: a `threedi_trigger` pool (2 slots) for `0_check_forecast_rain` and
`1_trigger_simulation`, and a `depth_calc` pool (1 slot) for `3_calculate_depth` paired with raising
`AIRFLOW__CELERY__WORKER_CONCURRENCY` from 2 to 4 (`main` at `26b6133`). Confirmed live across four
consecutive real runs: the trigger chain never queues behind a previous run's heavy tasks, no two
depth-calc tasks ever overlap, and run duration is now flat at 17 to 18 minutes instead of growing
run over run. Full detail: [[flood-mapping-full-worker-concurrency-serializes-runs]] (now
`resolved`). Residual, smaller, and now a latency question rather than a contention one: each run's
own critical path still runs a bit past the 15-minute cycle, so tiles publish 1.5 to 3 minutes after
their target moment instead of with margin before it. Tracked in [[five-minute-tile-freshness]].

**Effort:** S (human ~1 hr / CC ~30 min, plus DAG run time)
**Priority:** P1
**Depends on:** None. Unblocks closing [[map-shows-forecast-not-now]], pending its own residual
latency question.

**Blocker tracking:** [[flood-mapping-full-worker-concurrency-serializes-runs]] (resolved
2026-09-28)

**Blocker tracking:** [[map-shows-forecast-not-now]]

Status:: active

### 2. Mount flood_utils.py where Airflow can import it — done

Same item as below ("Mount flood_utils.py where Airflow can import it"), bumped to today's
priority: it unblocks [[timescaledb-and-flood-metrics]]'s Story 4.

**Result (2026-09-28):** Mounted `./floodmap/graphhopper-flood-road/scripts` into the Airflow
containers read-only (`main` at `245fe66`). Confirmed live on the server: `impassable_from_m()`
now returns real values inside `airflow-worker` instead of raising `ImportError`, no DAG import
errors. Full detail: [[airflow-cannot-import-flood-utils]] (resolved). Story 4 itself is still not
started, only unblocked.

Status:: done

### 3. Route each vehicle with its own flood depth limit — done, spot-checked

Same item as below ("Route each vehicle with its own flood depth limit"), bumped to today's
priority: small fix, unblocks [[truck-routing-profile]] reaching real users.

**Result (2026-09-28):** Removed `body.vehicle_type = state.vehicleType` from the routing
interceptor (`main` at `18d1c42`), so `server.py` falls back to each request's real `profile`.
Built and deployed. Mechanism confirmed (bundle no longer sends the field). The first spot-check
attempt was inconclusive (test area too deeply flooded for any vehicle). Redone later the same day
against a moderately-flooded railway overpass (20.2 cm): motorbike (20 cm limit) is blocked with
`ConnectionNotFoundException`, while car, truck, and foot (30/35/40 cm limits) all route through it
at 928-932 m. `GET /flood/areas` also showed motorbike and car now get different avoid-polygon
counts (814 vs. 651) for the same timestep. Full detail:
[[flood-routing-vehicle-type-always-motorbike]] (resolved 2026-09-28).

Status:: done

### 4. Bias Photon place search toward Hanoi — done

Same item as below ("Make place search work with the vi locale"), specifically its still-open
relevance half: pass the frontend's `point` and `location_bias_scale` on to Photon, or bound
results to a Vietnam box, so "Hồ Gươm" ranks the Hanoi lake above Ottawa and Munich.

**Result (2026-09-28):** `place_search.py`'s `geocode_gh_shape()` now forwards the frontend's
`point` (split into Photon's `lat`/`lon`) and `location_bias_scale`, and always sends
`countrycode=VN` to Photon, with a response-side backstop dropping any non-VN feature. `server.py`'s
`/geocode` route parses and forwards both params, reusing `place_search`'s existing validation so a
malformed `point` or out-of-range `location_bias_scale` returns 400. `main` at `6429923`. Verified
live on the server: "Hồ Gươm" now returns only Hanoi results (Hồ Gươm Plaza, Hoàn Kiếm Lake, Ho Guom
Theatre), Ottawa and Munich are gone, a malformed `point` returns 400, and the no-bias fallback path
(Enter-key search, `NavBar` URL resolution) stays Vietnam-filtered. New unit and live-Photon tests in
`test_place_search.py`.

Status:: done

### 5. Time-aware routing (P1) and the mobile legend overlap

[[routing-not-time-aware]] is a P1 safety gap. Research is done: industry practice and the academic
literature (2026-09-28), an engine survey for Option C, and a build plan that keeps GraphHopper
(2026-09-29), all in that blocker page. It still needs your decision on the approach (A-prime first,
then C-lite if a measurement justifies it) and the trip-time bound. The "Keep the flood legend visible
on mobile" item (below) is done.

**Blocker tracking:** [[routing-not-time-aware]]

Status:: active

## Untriaged (from artifacts/block.md, 2026-09-08, not yet revalidated)

### Depth TIF generation looks wrong

**What:** The depth TIF generated by the pipeline "looks weird" (no further detail recorded at
the time).

**Context:** Raised 2026-09-08, before the raster-to-polygon vectorization decision
(`artifacts/logs/2026-09-18.md`). May already be resolved by that change — needs a fresh look
before treating as open.

Status:: done
**Priority:** unknown (needs revalidation)

### Tile and TIF data don't match

**What:** The vector tiles and the source TIF don't look the same; the tiles don't cover all of
the TIF's data.

**Context:** Same 2026-09-08 note as above. Predates the switch to polygon vector tiles
(`artifacts/logs/2026-09-18.md`, `artifacts/docs/claude-plan/flood-extent-polygon-tiles-airflow-minio.md`)
— may already be resolved or superseded.

Status:: done
**Priority:** unknown (needs revalidation)

### Loading is very slow

**What:** Flagged as "very slow" with no further detail at the time.

**Context:** See [[sample_rate_1_bottleneck]] memory (SAMPLE_RATE=1 pipeline perf facts) for a
measured, more recent characterization of a related slowness — confirm whether this note refers
to the same bottleneck before treating as a separate issue.

Status:: needs-revalidation
**Priority:** unknown (needs revalidation)

### Address autofill/geolocation search for the user

**What:** User should be able to search for a place via autofill geolocation data.

**Context:** `floodmap/graphhopper-maps/src/sidebar/search/AddressInputAutocomplete.tsx` and
`AddressInput.tsx` already exist, suggesting this may already be implemented. Confirm the actual
UX still matches the ask before treating as open; likely closeable.

Status:: needs-revalidation
**Priority:** unknown (needs revalidation)

## FloodNav Map Redesign

### The map's default zoom is too tight

**What:** The frontend opens too zoomed in. `floodmap/graphhopper-maps/src/map/map.ts:19` sets the
initial view's `zoom: 17`, centered on the flood-forecast study area. Bring it down to somewhere in
the 13 to 15 range so more of the study area is visible on open.

**Context:** Found 2026-09-28 while checking what the frontend's current default zoom is. The
comment at `map.ts:16-17` notes this is a fixed initial view (not overridden by the routing graph's
own bbox), so the fix is just changing the literal.

**Effort:** XS (human ~15 min / CC ~5 min, plus eyeballing the right value in the range)
**Priority:** P3
**Depends on:** None.

Status:: active

### Tap-a-turn-step-to-highlight-that-segment-on-the-map

**What:** Clicking a turn-by-turn instruction row highlights that segment on the map.

**Why:** Delight/consistency detail — not shown in the mockup, but the app already has this exact
pattern end-to-end for route-hint buttons, so it's cheap to extend once per-step depth ships.

**Context:** Reuse `RHButton`'s click handler (`floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx:508-531`),
which already dispatches `PathDetailsElevationSelected` (highlights a segment) and `SetBBox`
(zooms/pans to it). Wire the same two actions from an `Instructions.tsx` step's `onClick` once
per-step depth data exists (see the mockup-adaptation plan's Phase C item 10).

**Effort:** XS (human ~2-3 hrs / CC ~15 min)
**Priority:** P3
**Depends on:** Phase C item 10 (per-step depth) landing first, so there's a segment to highlight.

Status:: active

### Backend hardening/validation for the GraphHopper flood-road backend

**What:** Harden and validate `floodmap/graphhopper-flood-road/backend/` (`server.py`,
`flood_areas.py`) before or alongside stacking more infrastructure on it.

**Why:** This backend is the result of a single commit (`6394e27`, "replace valhalla with
grasshopper routing logic to embed flood as a cost factor more effectively") — no regression
tests, no production soak time. The mockup-adaptation plan's Phase B (MinIO + rasterio) and
Phase C (TimescaleDB dependency) all add new load and new dependencies on top of this same,
unproven backend.

**Context:** Surfaced by an outside-voice review during `/plan-ceo-review` on the mockup-adaptation
plan (`~/.gstack/projects/alice182012-dev-t3-digital-twin/ceo-plans/2026-09-12-floodnav-mockup-adaptation.md`).
Not this plan's own scope, but a real risk it depends on: Phase B/C effectively bet that the
one-commit-old rewrite is solid. Consider a validation pass (regression tests against known
routes/flood scenarios, a soak period, comparing behavior against the old Valhalla-based backend
for known cases) before or in parallel with Phase B/C.

**Effort:** M (human ~2-3 days / CC ~4-6 hrs)
**Priority:** P2
**Depends on:** None — doesn't block Phase A (pure frontend chrome). Ideally lands before or
alongside Phase B/C, since those are what actually stack new load onto this backend.

**Progress (2026-09-23):** [[point-depth-lookup-backend]]'s Story 1 added
`backend/test_flood_areas.py` and `backend/test_server.py`, a regression pass against a real
PostGIS and a stub GraphHopper covering `derive_areas()`, `build_custom_model()`, and `server.py`'s
full HTTP surface. Still open: a soak period and a side-by-side comparison against the old
Valhalla-based backend for known routes and flood scenarios.

Status:: active

### Route each vehicle with its own flood depth limit — RESOLVED 2026-09-28

**What it was:** Every route request sent `vehicle_type=motorbike`, so car, foot, and truck routes
used the 20 cm motorbike limit instead of 30, 40, and 35 cm. `FloodStore.ts`'s `SelectFloodVehicle`
action was never dispatched.

**Fix:** Stopped sending `vehicle_type` from the interceptor, so `server.py` falls back to each
request's own `profile` (`main` at `18d1c42`). Deployed and mechanism-verified.

**Spot-checked 2026-09-28:** Unpaused `flood_mapping_full`, let a cycle complete, and tested a
railway overpass at 20.2 cm depth: motorbike (20 cm) is blocked with `ConnectionNotFoundException`,
car/truck/foot (30/35/40 cm) all route through at 928-932 m. `GET /flood/areas` also returned
different avoid-polygon counts for motorbike (814) versus car (651) at the same timestep.

**Blocker tracking:** [[flood-routing-vehicle-type-always-motorbike]] (resolved, full detail and
verification)

Status:: resolved

### Keep the flood legend visible on mobile — RESOLVED 2026-09-28

**What it was:** On a phone-width screen, the mobile search panel covers the top of the flood
legend, and the "Updated" line added by [[frontend-polish]]'s Story 2 makes the legend one line
taller. Position the legend so no band is hidden, with the panel collapsed and expanded.

**Fix:** Moved the legend to bottom-right on mobile via a `@media (max-width: 44rem)` override in
`FloodLegend.module.css`, mirroring `MapModeToggle`'s existing bottom-left placement, instead of
tracking the search panel's runtime height (`main` at `e5b155a`). Desktop is unchanged. Verified
live: at 390x844 the full legend (title, all seven bands, "As of" line) renders clear of the search
panel and the Map/Flood toggle; at 1440x900 the desktop position is unchanged.

**Blocker tracking:** [[mobile-flood-legend-covered-by-search-panel]] (resolved, full detail and
verification)

Status:: resolved

### Show the right icon for the motorbike routing profile

**What:** The user reported that the bike profile icon is wrong. `findIcon('motorbike')` in `profileIcons.ts` has no
`motorbike` key, so it likely returns the question-mark icon. Confirm what shows on screen, check the mockup for the
intended glyph, and map the profile to it.

**Effort:** XS (human ~1 hr / CC ~10 min)
**Priority:** P3
**Depends on:** None.

**Blocker tracking:** [[motorbike-profile-icon-wrong]]

Status:: resolved

### Mount flood_utils.py where Airflow can import it — RESOLVED 2026-09-28

**What it was:** The flood metric extractor imports `flood_utils.py` from
`floodmap/graphhopper-flood-road/scripts`, which the Airflow containers did not mount, so it failed
with `ImportError` inside Airflow.

**Fix:** Mounted `./floodmap/graphhopper-flood-road/scripts` into the Airflow containers, read-only
(`main` at `245fe66`). Verified live: the extractor's `impassable_from_m()` returns real values
inside `airflow-worker`, no DAG import errors.

**Still open:** Wiring the extractor into a DAG (this only unblocks that) — see
[[timescaledb-and-flood-metrics]]'s Story 4.

**Blocker tracking:** [[airflow-cannot-import-flood-utils]] (resolved, full detail and verification)

Status:: resolved

### Make place search work with the vi locale — RESOLVED 2026-09-28

**What it was:** The frontend sent `locale=vi`, `place_search.py` passed it to Photon as `lang=vi`, and
Photon rejects it (it supports only `default`, `de`, `en`, `fr`). The backend answered 502 and search
showed no suggestions on the live UI.

**Fix:** The frontend default became `en` and place search worked on the live UI (deployed
2026-09-24). On 2026-09-28 `place_search.py` also started forwarding the request's `point` and
`location_bias_scale` to Photon and filtering to `countrycode=VN` (`main` at `6429923`). Verified
live: "Hồ Gươm" returns only Hanoi results, ranked first, with Ottawa and Munich gone.
Full detail: [[photon-rejects-vi-locale]] (resolved).

**Effort:** S (human ~2 hrs / CC ~30 min)
**Priority:** P1
**Depends on:** None.

**Blocker tracking:** [[photon-rejects-vi-locale]]

Status:: resolved

### Hotstart from the saved state valid at the run's slot

**What:** [[hotstart-state-saved-at-end-of-run]]. Each 3Di run saved its state at the end of the run,
so the next run hotstarted from a state that lagged the clock. The fix saves a state at
`HOTSTART_SAVE_SECONDS` (default 900 s) with a backup at twice that, and `choose_saved_state` picks the
state whose `valid_at` matches the run's 15-minute slot (`main` at `dd78bcb` and `09e8650`,
`scripts/create_simulation.py`). The 2026-09-26 test-DAG log shows "Hotstart, exact ... offset 0 min".

**Still open (monitoring, 2026-09-29):** No live `flood_mapping_full` run shows a hotstart under the
real schedule yet. The earlier concerns are handled in code: `choose_saved_state` accepts only a state
at most two cycles (30 minutes) before the slot and otherwise cold starts, a backup state at twice the
save interval covers a failed run, and the one-day expiry no longer matters because no state older than
30 minutes is used. Close this item when a live run logs "Hotstart, exact" or "Hotstart, fallback".

**Effort:** S (human ~2 hrs / CC ~30 min)
**Priority:** P1
**Depends on:** None.

**Blocker tracking:** [[hotstart-state-saved-at-end-of-run]]

Status:: active

### Reuse database connections in floodmap-backend

**What:** `server.py` opens a new PostgreSQL connection for every request, and the first raster call
in a new session loads the PostGIS raster library. That makes a `GET /flood/points` request take about
58 ms locally although the tiled lookup takes 0.2 ms. Pool the connections in `db.py`, then measure on
the server.

**Effort:** S (human ~half a day / CC ~1 hr)
**Priority:** P2
**Depends on:** [[raster-first-pipeline-stories]] Story 2 deployed. Feeds the latency check in
[[point-depth-lookup-backend]]'s Story 4.

**Blocker tracking:** [[flood-points-connection-per-request]]

Status:: active

### Decide what the map shows by default: now or the forecast

**What:** The map, the "Updated" line, and routing show the timestep closest to now. Every timestep is a forecast, and no t0 raster
exists (3Di's step 0 is a placeholder), so at 21:22 the page showed 21:40. The user wants the map to show the situation at now, with the
forecast in routing and the histogram. Brainstorm the options (relabel, latest past step, a real t0) before any code.

**Effort:** unknown until the options are chosen (relabel S, real t0 L)
**Priority:** P2
**Depends on:** [[route-forecast-query]] and [[depth-forecast-chart]] for the forecast side.

**Blocker tracking:** [[map-shows-forecast-not-now]]

Status:: active

### Establish a project DESIGN.md

**What:** Run `/design-consultation` to establish a project DESIGN.md with real design tokens
(colors, typography, spacing scale).

**Why:** This plan (and future ones) currently calibrate against a one-off approved mockup HTML
file, read manually each review, rather than a reusable, versioned token set. Risk of drift over
time as more screens get built without a shared vocabulary.

**Context:** Surfaced by `/plan-design-review`'s Pass 5 (Design System Alignment) on the
mockup-adaptation plan (`~/.claude/plans/dazzling-percolating-raven.md`). The mockup itself (Claude
Design project "Flood-Aware Routing Map," screens 2a-2f) has real values worth extracting into a
proper DESIGN.md rather than continuing to read the source HTML ad hoc.

**Pros:** Reusable tokens, faster future design reviews, consistent vocabulary across screens.
**Cons:** Upfront time investment; not blocking any current work.

**Effort:** M (human ~half day / CC ~1-2 hrs)
**Priority:** P3
**Depends on:** None.

Status:: active

### Accessibility spec for Phase A's new interactive elements

**What:** Keyboard nav, ARIA roles, touch target sizing, and contrast requirements for
`MapModeToggle`, `FloodLegend`, and the route tabs (e.g. `role="tablist"`/`"tab"` with arrow-key
navigation, `aria-pressed` on the toggle, `aria-selected` on the active tab, 44px minimum touch
targets, 4.5:1 minimum contrast on legend text).

**Why:** Nothing in the current plan requires these new elements to be keyboard-operable or
screen-reader-friendly — surfaced by `/plan-design-review`'s Pass 6 (Responsive & Accessibility),
where this was explicitly deferred rather than specified now.

**Context:** `PlainButton` (the base component `MapModeToggle` is built on, per the eng review's
Code Quality finding) likely already covers baseline keyboard-operability, but the route tabs are
a new interaction pattern with no existing ARIA precedent in this codebase to copy from.

**Pros:** Real accessibility instead of an afterthought; avoids a compliance/usability gap.
**Cons:** Needs a dedicated audit pass once Phase A actually exists to test against.

**Effort:** S (human ~1-1.5 hrs / CC ~20-30 min)
**Priority:** P2
**Depends on:** Phase A implementation existing to audit against.

Status:: active

### Pinned GraphHopper build rejects any new vehicle profile — RESOLVED 2026-09-23

**What it was:** Not a broken build. The pinned image's `graphhopper.sh` entrypoint always injects
`-Ddw.graphhopper.graph.location=/data/default-gh` (its own default) as a JVM system property,
which overrides `config.yml`'s `graph.location: /data/graph-cache`. `compose.yml`'s entrypoint
never passed `-o` to change that default, so every start loaded a graph frozen into the image at
build time, with only `car_access`/`hgv`/friends encoded, and the real mounted `graph-cache` volume
was never used at all.

**Fix:** Added `-o /data/graph-cache` to the `graphhopper` service's `entrypoint` in `compose.yml`,
restored the `foot` profile and its encoded values (`foot_access`, `foot_average_speed`,
`foot_road_access`) in `graphhopper/config.yml`, and added `foot: {}` to
`graphhopper-maps/config-local.js.example`. Verified live on the remote host: real OSM import,
`foot` registered with its encoded values, and an actual walking route returned end to end.

**Still open:** `truck` is still missing from `config-local.js.example`'s `profiles`, a separate,
already-understood config gap: add `truck: {}` to its `profiles` object and rebuild the frontend.
GraphHopper already serves the profile, so no backend change is needed. Scheduled as [[truck-routing-profile]] in Sprint 4. See
`artifacts/docs/concepts/graphhopper-backend.md`'s Open items.

A separate P1 bug was found and fixed the same day while verifying this in the UI: routing (any
profile) failed with "No safe route available" whenever a flood timestep was attached, i.e.
always. Unrelated root cause to this item — see [[flood-route-missing-geom-column]] (resolved
2026-09-23).

**Blocker tracking:** [[graphhopper-vehicle-profile-rejection]] (full investigation, all 5
approaches, and verification steps)

Status:: resolved
