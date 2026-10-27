---
date_drafted: 2026-09-23
type: prd
status: draft
subsystem: floodmap-frontend
source_ideas: []
tags: [prd, floodmap-frontend, mockup-gap]
related: ["[[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]", "[[lessons#L-009|verify-table-capability-against-write-path-not-summary-or-current-query]]"]
---

# Flood routing mockup to frontend gap

## Problem

`artifacts/raw/mockups/Flood Routing Mockups v2.dc.html` (screens 2a through 2f) shows six flood-routing
UI states approved for `floodmap/graphhopper-maps`. Several elements in those screens have no
matching code in `floodmap/graphhopper-maps/src`. A user comparing the shipped app against the
approved design finds three categories of gap.

First, the map has no way to show water depth at a point the user taps. Screen 2b shows a pin
placed on the map opening a card with the location's name, its address, and "Water depth now: 30
cm". `floodmap/graphhopper-maps/src/layers/ContextMenu.tsx` only opens on right-click, and its
content (`floodmap/graphhopper-maps/src/map/ContextMenuContent.tsx`) has no depth field.
`floodmap/graphhopper-maps/src/layers/MapFeaturePopup.tsx`, the closest existing popup, renders a
raw `key=value` list of whatever properties the hovered map feature carries. It has no card layout, no
place name or address lookup, and no depth line. A grep for `depth` across every file under
`floodmap/graphhopper-maps/src/layers/` (`MapFeaturePopup.tsx`, `PathDetailPopup.tsx`,
`POIPopup.tsx`, `InstructionPopup.tsx`, `MapPopup.tsx`) returns no matches.

Second, once a route exists, the mode-selector row shows no time estimate. Screen 2e shows a travel
time under each of the four mode icons (car, motorbike, walking, truck) at once, for example "4
min" under car and "14 min" (bold, the selected mode) under walking.
`floodmap/graphhopper-maps/src/sidebar/search/routingProfiles/RoutingProfiles.tsx` renders only the
four mode icons. It has no per-mode time, and it issues no request for modes the user has not
selected.
The only travel time in the running app is the single value in
`floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx`, for the currently selected profile.

Third, once a route exists, neither the route panel nor the map shows the forecast depth along that
route over time. Screen 2e's sidebar has an "Average water depth" chart: five 30-minute columns,
the second column (labeled "Now") highlighted green, a dashed line at the route's average depth at
now, and a value label ("20 cm") at that line. The map itself carries small pill badges along the
route polyline, each showing a point depth ("8 cm", "22 cm", "5 cm", "0 cm").
`floodmap/graphhopper-maps/src/pathDetails/ElevationInfoBar.tsx` and
`floodmap/graphhopper-maps/src/pathDetails/elevationWidget/ElevationWidget.tsx` build a
distance-versus-elevation chart from `path.ascend`, `path.descend`, and per-point elevation, not a
time-versus-depth forecast. `floodmap/graphhopper-maps/src/sidebar/instructions/Instructions.tsx`
shows each turn's distance (`metersToText(instruction.distance, ...)` at line 61) with no depth
figure, where screen 2e's step list shows both on one line ("320 m · 8 cm"). No component draws a
depth badge along the route polyline. A grep for `depth` across
`floodmap/graphhopper-maps/src/pathDetails/` and
`floodmap/graphhopper-maps/src/layers/UsePathDetailsLayer.tsx` returns no matches.

A fourth, smaller gap: `floodmap/graphhopper-maps/src/floodmap/FloodLegend.tsx` renders the title
and the color bands, but not the "Updated 12/09/2026 23:24" line the mockup's legend card shows
below the bands (screens 2b, 2e). The legend's bucket boundaries also don't match the mockup: the
shipped legend (`floodmap/graphhopper-maps/src/floodmap/depthScale.ts`,
`DISPLAY_DEPTH_BANDS`) uses 5, 10, 20, 30, 40, 50, and 60 cm, seven bands total, while the mockup
uses 1, 5, 10, 30, and 60 cm, five bands total. `depthScale.ts`'s own comment explains this bucketing
was chosen to match a QML color ramp used elsewhere in the pipeline, not the mockup. This is a
confirmed intentional divergence, not an unbuilt gap. See Decisions.

Everything else in the mockup's six screens has a working match in the current frontend: the
collapsed search pill labeled "Search Floodmap"
(`floodmap/graphhopper-maps/src/App.tsx:280-288`, `styles.sidebarOpenLabel`), the bottom-left
Map or Flood thumbnail toggle (`floodmap/graphhopper-maps/src/floodmap/MapModeToggle.tsx`, its own
comment cites screens 2a to 2f), the top-right flood-depth legend gated on flood mode
(`floodmap/graphhopper-maps/src/floodmap/FloodLegend.tsx`, same citation), the start and destination
input pair with a red destination pin and a dotted via-point rail
(`floodmap/graphhopper-maps/src/sidebar/search/AddressInput.tsx`,
`floodmap/graphhopper-maps/src/sidebar/search/Search.tsx`), and route alternatives shown as pill
tabs (`floodmap/graphhopper-maps/src/sidebar/RoutingResults.tsx`'s `RouteTabs`, backed by
`floodmap/graphhopper-maps/src/sidebar/routingResultsView.ts`'s `buildRouteTabs`).

## Goals

- Add a place popup that opens when the user taps or clicks a point on the map (not just right-click) and shows
  that point's name, its address, and "Water depth now: `N` cm" at the nearest available flood
  timestep, matching screen 2b's card layout and copy.
- Add a per-mode travel time under each of the four mode icons in `RoutingProfiles.tsx` once a
  route exists, sourced from a request per mode (or a single multi-profile request, whichever the
  routing backend supports more cheaply), matching screen 2e.
- Add a time-versus-depth forecast chart to the route result panel: 30-minute columns spanning the
  forecast window, the "now" column highlighted, and a dashed line at the route's current average
  depth with its value labeled, matching screen 2e's "Average water depth" chart.
- Add a depth figure to each turn-by-turn step in `Instructions.tsx`, shown alongside the existing
  distance on the same line ("320 m · 8 cm"), matching screen 2e.
- Add point depth badges along the rendered route polyline on the map, matching screen 2e's four
  floating pill badges.
- Add the "Updated `date` `time`" line to `FloodLegend.tsx`, below the color bands, sourced from the
  selected flood timestep's `valid_time`.

## Non-goals

- Rebuilding or restyling any element the current frontend already matches (search pill, map or
  flood toggle, legend bands and their gating, start or destination inputs, route alternative tabs).
  Their existing implementations are the reference. This PRD only tracks what is missing.
- Any mockup screen or interaction not in the six numbered screens (2a to 2f) of
  `Flood Routing Mockups v2.dc.html`. The sibling `Flood Routing Mockups v2.html` in the same folder
  is a bundler-rendered copy of the same content, not a separate design. It adds nothing this PRD
  needs to track independently.
- The implementation plan for any of the Goals above. That belongs in
  `artifacts/docs/claude-plan/` once this PRD is approved, not in this document.
- Changes to the flood forecast data pipeline (Airflow DAGs, MinIO tile generation, GraphHopper
  routing backend) beyond what a new frontend query needs from an existing endpoint. If a goal turns
  out to need a new backend endpoint or field, that becomes a Dependency, not scope for this PRD to
  design.

## Dependencies and assumptions

- The place-depth popup (goal 1) and the per-step and per-point depth figures (goals 4 and 5) all
  read a single point's depth at a single timestep. [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] builds
  `GET /flood/points` for exactly this (see this PRD's Decisions and that PRD's Goals): each is a
  call to that endpoint at a tapped point (goal 1), at each turn's location (goal 4), or at each
  point along the route polyline where depth changes (goal 5). `flood_road_values` and
  `flood_extent_polygon` can't serve this: the first only has depth at road segments, the second
  only has banded ranges, and the mockup shows an exact figure ("30 cm", "8 cm").
- The depth-versus-time forecast chart (goal 3) is different: it needs depth averaged along the
  whole route across five 30-minute columns, not one point at one timestep. `GET /flood/points`
  doesn't cover this, but a route-forecast query [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] now builds
  does (see this PRD's Decisions): `flood_road_values` already holds a full per-segment forecast
  time series per run, written by `geojson_to_pg.py`'s `build_rows`, not just a single snapshot.
- The place-depth popup also assumes a reverse-geocoding source for the place name and address shown
  in the card ("Đại Mỗ", "Nam Từ Liêm, Hà Nội" in the mockup). Confirm which existing geocoder in
  `floodmap/graphhopper-maps/src/pois/` or `floodmap/graphhopper-maps/src/sidebar/search/` already
  does this, if any. The search inputs' forward-geocoding autofill
  (`sidebar/search/AddressInputAutocomplete.tsx`'s `GeocodingItem`, backed by the `geocodingApi`
  config, per `NavBar.ts`'s geocode-then-reverse-geocode flow) is the likely starting point to check
  first, since `NavBar.ts` already calls `.reverseGeocode(...)` on the same Nominatim-backed client
  for its own two-stage POI search. This is the opposite direction (point to place, not text to
  suggestions) but may be the same underlying client and config.
- The per-mode travel time (goal 2) assumes the routing backend can answer a time-only query per
  profile cheaply enough to run four of them (or one batched call) on every route request without a
  visible delay. This needs a timing check against the live GraphHopper instance before committing to
  four separate requests.
- Goals 1, 4, and 5's calls to `GET /flood/points` need to land within the same interactive latency
  budget as the existing `GET /flood/areas` call, since a popup tap and a rendered route are both
  synchronous UI moments. [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] flags the same timing check as its
  own open risk. Don't duplicate that check here, just block implementation on its result.
- Goal 3's route-forecast query depends on [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] resolving how a
  route's road segments get matched against `flood_road_values`'s rows (that PRD's Dependencies and
  assumptions section). If the match turns out wrong, the chart would show a plausible but
  incorrect average, not an obvious error, so don't wire up goal 3 until that PRD's own
  spot-checked verification passes.
- The "Updated" line (goal 6) assumes the selected timestep's `valid_time`
  (`FloodStore.ts:FloodTimestep.valid_time`) is already in a format `FloodLegend.tsx` can format into
  the mockup's `DD/MM/YYYY HH:MM` display, or that a small date-formatting change is enough.

## Definition of done

Given the app is open with a route already showing on screen (any two points, any mode), when the
user taps a point on the map that isn't a query point, then a card opens at that point showing its
name, its address, and a "Water depth now: `N` cm" line, matching screen 2b.

Given a route exists between two points, when the route result renders, then each of the four mode
icons in the profile row shows a travel time below it, and the selected mode's time is visually
distinguished (bold, matching screen 2e), without the user selecting each mode in turn to see its
time.

Given a route exists, when the route result panel renders, then it shows a 30-minute-column depth
chart with the "now" column highlighted and a dashed line labeled with the route's current average
depth, and separately, each turn-by-turn step in the expanded instructions list shows its depth next
to its distance on the same line.

Given a route exists, when the route renders on the map, then the map shows depth badges at points
along the route polyline where the depth changes, matching the four badges in screen 2e (not fewer,
and not one badge per turn regardless of whether depth changed there).

Given flood mode is on, when the legend renders, then it shows an "Updated" line below the color
bands with the selected timestep's date and time.

## Risks and open questions

- The per-mode travel time (goal 2) still risks a visible delay if four separate route requests are
  needed per query. Accepted for now since goal 2 isn't shown to real users yet (see Decisions).
  Revisit before it reaches real users: either add a loading state per mode icon, or find a cheaper
  multi-profile query.
- Goal 3's data source is now confirmed (see Decisions): a route-forecast query against
  `flood_road_values`, built by [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]. The remaining open question
  is that PRD's own: how to match a route's road segments against the table's rows, since the table
  has no stable segment ID. See that PRD's Risks and open questions.
- The search inputs' forward-geocoding autofill (`AddressInputAutocomplete.tsx`, verified working
  2026-09-23 against the live UI at `http://100.67.84.55:8082`) sent its query with `&locale=en`
  (`/api/geocode/geocode?...&locale=en&...`), derived from `index.tsx`'s translation-locale default
  (`navigator.language`). Typing "Hồ Gươm" returned correct, correctly-encoded Vietnamese matches
  ("Hồ Gươm Plaza", "Hoàn Kiếm Lake") mixed with unrelated same-name hits outside Vietnam ("Ho Guom"
  in Ottawa, Canada and Munich, Germany). Fixed in `index.tsx` (see Decisions): the default locale
  is now `vi` instead of `navigator.language`, which also fixes `Api.ts`'s `geocode()` call, since
  it derives its `locale` param from the same translation language. Not yet re-verified live: needs
  a rebuild and redeploy on the remote host, then a repeat of the "Hồ Gươm" search to confirm the
  Ottawa or Munich hits are gone.

## Decisions

| Date | Question | Decision | Why |
| ---- | -------- | -------- | --- |
| 2026-09-23 | Where does the place-depth popup (goal 1), and the per-step and per-point depth figures (goals 4 and 5), read water depth from? | `GET /flood/points`, a new endpoint built by [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]], backed by `depth.tif` loaded into PostGIS as a raster (`postgis_raster`, `ST_Value`). Not `flood_road_values`. | Corrected 2026-09-23: `flood_road_values` only has depth at road segments, so it can't answer an arbitrary-point query. `depth.tif` is always the source of truth for depth values, confirmed by the user. |
| 2026-09-23 | What resolution is the flood timestep list the depth-versus-time chart (goal 3) depends on? | 30 minutes, matching the mockup's five 30-minute columns. | Confirmed by the user. No resampling or column-width change needed. |
| 2026-09-23 | Does goal 3 (forecast chart) still have no data source, now that `flood_road_values`'s write path is checked directly? | No. `flood_road_values` already holds a complete per-segment forecast time series per run (`geojson_to_pg.py`'s `build_rows` writes one row per segment per forecast timestep). [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]] builds a route-forecast query against it instead of a new table or endpoint. | The earlier "no data source" conclusion was reasoned from the architecture doc's one-line schema summary and `flood_areas.py`'s single-timestep query, not the table's write path. See [[lessons#L-009|verify-table-capability-against-write-path-not-summary-or-current-query]]. |
| 2026-09-23 | Should `DISPLAY_DEPTH_BANDS` change from its current seven QML-derived bands to the mockup's five bands? | Keep the current seven bands (5, 10, 20, 30, 40, 50, 60 cm; `#deebf7` through `#08306b`). The mockup's five-band scheme is not adopted. | Confirmed by the user. `depthScale.ts` and `FloodExtentLayer.tsx` stay unchanged. |
| 2026-09-23 | Does the per-mode request latency risk (goal 2) block implementation? | No. Accepted for the current build, since goal 2 isn't shown to real users yet. | Confirmed by the user. Revisit before real users see it (see Risks and open questions). |
| 2026-09-23 | The geocoder's `en` locale returns same-name results outside Vietnam ("Ho Guom" in Ottawa, Munich) alongside correct Vietnamese matches. Switch locale, add a bounding-box bias, or accept it? | Switch the default locale to `vi`. `floodmap/graphhopper-maps/src/index.tsx`'s `setTranslation(locale \|\| navigator.language)` changed to `setTranslation(locale \|\| 'vi')`; the `?locale=` URL override still works. | Confirmed by the user. This app only ever routes within a Vietnam flood-simulation area, so `navigator.language` (a visiting browser's own setting, not the app's actual audience) was the wrong default. |

## Rollback

Each goal in this PRD adds a component or a field to an existing screen. None replaces or removes
existing behavior, so no goal needs a rollback plan beyond reverting its own commit. If the per-mode
travel time (goal 2) turns out to add unacceptable latency to every route request, revert to the
current single-time display rather than shipping a slower four-request version.

## Status history

- **2026-09-23, draft.**
- **2026-09-23, draft.** Corrected goal 1's data source from `flood_road_values` to
  `GET /flood/points` (raster-backed, [[PRD-002-t3-digital-twin-architecture-gaps|t3-digital-twin-architecture-gaps]]), since a road-segment
  table can't answer an arbitrary-point query. Same endpoint resolves goals 4 and 5. Goal 3 (the
  forecast chart) still has no confirmed source.
- **2026-09-23, draft.** Fixed the search autofill's `en`-locale relevance risk: `index.tsx`'s
  default locale is now `vi`. Not yet rebuilt or redeployed on the remote host; needs a repeat of
  the "Hồ Gươm" test once it is.
- **2026-09-23, draft.** Resolved goal 3's "no confirmed data source" finding: `flood_road_values`
  already holds a full per-segment forecast time series, reversing the earlier conclusion. See
  [[lessons#L-009|verify-table-capability-against-write-path-not-summary-or-current-query]].
