> **SUPERSEDED 2026-09-04:** This document has been consolidated into `artifacts/FloodNav_Phase1_Consolidated_Plan.md` (Part B) along with the CEO backend plan, to stop the two documents drifting from each other. This file is kept for history; treat the consolidated doc as authoritative going forward.

**User Requirements Document (URD)**

**Flood-Aware Routing Map App (Wireframe 2a)**

**Document Version: 4.2**

**Date: July 14, 2026 (rev. September 4, 2026 — /plan-design-review pass; rev. September 4, 2026 — reconciled data-source refs against CEO plan's raster/PostGIS cutover)**

**Project: Flood-prone Routing Map App — TECOTEC / NAWAPI / FloodNav lineage**

**Parent scope doc:** `~/.gstack/projects/3plus1wheels-airflow_new/ceo-plans/2026-08-07-floodnav-phase1-core-pipeline.md` (CEO-approved Phase 1 backend scope — this URD is that plan's "Frontend: citizen floodmap + routing engine UI" line, spec'd out). Backend data-source assumptions below are reconciled against that plan's raster/PostGIS cutover, not the full target-platform vision in `artifacts/SW Architecture.md`, which is explicitly out of Phase 1 scope.

# **1\. Purpose**

The Flood-Aware Routing Map App gives citizens and stakeholder viewers a Google-Maps-style interface — built on wireframe 2a's layout — for finding routes that account for real-time and forecast flood depth in Hanoi. It re-skins the existing, already-functional floodmap-frontend (Leaflet \+ Valhalla \+ MinIO flood data, per ARCHITECTURE\_AND\_FEATURES.md) into wireframe 2a's split-panel-plus-layer-strip design, adds place-name search, and extends vehicle costing to match the fuller vehicle picker the wireframe calls for. The tool is intended to run continuously and be demonstrated to stakeholders on demand — it is not a public-facing product at this stage.

# **2\. Users**

**Primary Users**

* Citizen drivers/riders — motorbike, car, and truck operators seeking flood-aware directions

* TECOTEC / NAWAPI project team — building, testing, and operating the app

**Secondary Users**

* Stakeholder viewers — government/NAWAPI/MAE representatives viewing scheduled demos (view-only, no distinct UI needed beyond what citizen users see)

* Backend/infrastructure owners — responsible for the floodmap-backend, Valhalla, and MinIO services this app depends on

# **3\. List of Functional Requirements**

*Priority Legend: M \= Must Have, S \= Should Have, L \= Could Have*

## **3.1. Map & Flood Layer**

### ***3.1.1. REQ-MAP-001: Display base map with pan/zoom***

| Requirement ID | REQ-MAP-001 |
| :---- | :---- |
| **Requirement Title** | Display base map with pan/zoom |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display a Leaflet-based map (reusing the existing floodmap-frontend map instance) covering the Hanoi service area, supporting standard pan and zoom interaction. This is the always-on base layer beneath all other map content; it is not user-toggleable. |
| **Acceptance Criteria** | The map loads and centers on the Hanoi service area by default.  Pan and zoom work via mouse, touch, and keyboard. |

### ***3.1.2. REQ-MAP-002: Toggle flood data layers via a single “Flood” control***

| Requirement ID | REQ-MAP-002 |
| :---- | :---- |
| **Requirement Title** | Toggle flood data layers via a single “Flood” control |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall expose one “Flood” icon in the bottom-right layer strip (per wireframe 2a).  Selecting it opens the Flood layer. Data source: raster depth tiles (GeoTIFF/XYZ) rendered from the per-cycle 3Di output via `floodmap-backend`, per the Phase 1 CEO plan's raster-only cutover — **not** flood\_timestamp.geojson from MinIO, which the backend has moved off of. When the rendered layer is sourced from the scenario library rather than a live 3Di run, the layer strip's Flood icon shall carry the `--scenario-library` indicator (small dot/badge) so viewers don't mistake replayed data for a live simulation. |
| **Acceptance Criteria** | Clicking the Flood icon opens the Flood layer. When scenario-library data is active, the `--scenario-library` indicator is visible on the Flood icon; it is absent when the layer reflects a live/current simulation. |

### ***3.1.3. REQ-MAP-003: Auto-activate flood layer when a model run is triggered***

| Requirement ID | REQ-MAP-003 |
| :---- | :---- |
| **Requirement Title** | Auto-activate the flood layer when a model run is triggered |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall automatically activate the Flood layer the moment a 3Di model run is triggered.  If no model run has been triggered, the map shall remain on its default base layer with the Flood layer inactive.  The model-trigger event is the on/off signal. Users may still manually override the layer state at any time via REQ-MAP-002. While a triggered model run is in a designated storm-mode state (elevated trigger frequency/severity, per the pipeline's storm-mode logic), the system shall surface a `--storm-mode` banner near the layer strip so users understand why data is refreshing unusually often. |
| **Acceptance Criteria** | The flood layer switches to active automatically within one refresh cycle of a model trigger event.  When no model has been triggered, the Flood layer defaults to inactive on load. Manual toggle overrides the automatic state until the next trigger event or page reload. The `--storm-mode` banner appears only while storm-mode is active on the backend and disappears when it ends. |

### ***3.1.4. REQ-MAP-004: Render flood depth using the standardized blue depth scale***

| Requirement ID | REQ-MAP-004 |
| :---- | :---- |
| **Requirement Title** | Render flood depth using the standardized blue depth scale |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall render flood raster-tile fill and depth-forecast chart bars (REQ-DET-001) using a monochromatic blue scale in 20cm bands (0–20 / 20–40 / 40–60 / 60–80 / 80–100 / \>100 cm).  This scale represents raw depth magnitude only. Route and segment safety status (passable/pre-closure/impassable/draining) shall use the separate \--seg-\* tokens instead — the two scales must not be conflated. Data source: pre-sampled per-segment depth (PostGIS, per Phase 1 CEO plan) for routes/segments, and per-cycle raster tiles for the map layer — **not** flood\_timestamp.geojson from MinIO, which the backend has moved off of. Exact token values are defined in §8 Design Tokens — the previously circulated token file used a green→maroon severity gradient for `--depth-*`, which contradicted this requirement; §8 supersedes it. |
| **Acceptance Criteria** | Flood raster-tile fill uses only the seven defined blue/gray shades from §8, correctly banded by depth in cm.  No flood-magnitude UI element uses red, amber, or green. Route/segment status indicators (REQ-RTE-002) use \--seg-\* colors, verified as visually distinct from the depth scale. |

## **3.2. Search & Location Input**

### ***3.2.1. REQ-SRCH-001: Pick origin/destination by clicking the map***

| Requirement ID | REQ-SRCH-001 |
| :---- | :---- |
| **Requirement Title** | Pick origin/destination by clicking the map |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall allow a user to set an origin or destination point by clicking directly on the map, reusing the existing map-click point-picking behavior already implemented in floodmap-frontend.  This is the baseline input method and shall function independently of place-name search (REQ-SRCH-002). Map-click point-picking is a mouse/touch-only affordance for this release — it has no keyboard equivalent. Keyboard-only users complete origin/destination selection via place-name search (REQ-SRCH-002) instead; this is an accepted, documented limitation rather than a WCAG gap in REQ-USE-001, since the search path remains fully keyboard-operable. |
| **Acceptance Criteria** | Clicking the map sets the active origin/destination field. A marker appears at the selected point.  This method works even if place-name search is unavailable or fails. |

### ***3.2.2. REQ-SRCH-002: Search origin/destination by place name***

| Requirement ID | REQ-SRCH-002 |
| :---- | :---- |
| **Requirement Title** | Search origin/destination by place name |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall provide a pill-shaped search bar with the placeholder “Search a place or address” positioned in the top-left corner of the screen.  The search bar shall remain a compact pill at all times until the user clicks it.  On click (desktop/tablet, ≥768px viewport width), it shall expand into a panel with a **fixed 340px width** — matching the Route Results/Detail panel (REQ-RTE-001) so panel width is consistent across all left-panel states — with the search bar embedded at the top of that panel. Below 768px viewport width, the panel becomes full viewport width with the map revealed beneath it via the same expand/collapse interaction (see REQ-RES-001).  On focus plus input, the system shall call Photon (GET https://photon.komoot.io/api/?q={query}\&bbox={hanoi\_bbox}, or a self-hosted Photon instance) and render an autocomplete dropdown below the bar (see REQ-SRCH-004).  If the geocoding service is unavailable or slow, the field shall degrade gracefully to map-click picking (REQ-SRCH-001) without blocking the user. |
| **Acceptance Criteria** | The search bar renders as a pill in the top-left corner by default.  Clicking it opens a 340px-wide panel (full-width below 768px), with the search bar visible inside it.  Selecting a result sets the corresponding origin/destination field and map marker.  If the geocoding service fails, the user can still complete the task via map-click. |

### ***3.2.3. REQ-SRCH-003: Display data source and freshness status***

| Requirement ID | REQ-SRCH-003 |
| :---- | :---- |
| **Requirement Title** | Display data source and freshness status |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display "update: now or \_ minutes before" based on the time the newest file was injected into the frontend to display. Once staleness exceeds the pipeline's configured overdue threshold, the badge shall switch from its default neutral treatment to the `--stale-banner` token (brown) so overdue data is visually distinct from normal freshness, not just distinguishable by reading the minute count. |
| **Acceptance Criteria** | The badge shows a human-readable “data as of \[time\]” indicator, updating on each backend refresh cycle. Past the overdue threshold, the badge renders with `--stale-banner` styling; below it, the badge uses the default neutral style. |

### ***3.2.4. REQ-SRCH-004: Autocomplete search results***

| Requirement ID | REQ-SRCH-004 |
| :---- | :---- |
| **Requirement Title** | Autocomplete search results |
| **Priority** | Must |
| **Functional Requirement Description** | The autocomplete dropdown (REQ-SRCH-002) shall activate as soon as the user types a single character.  Each row shall show the place name and address. The dropdown shall show up to 5 results. While the Photon request for the current query is in flight, the search pill/panel shall show a small inline spinner (see §Interaction States) rather than an empty dropdown. |
| **Acceptance Criteria** | Typing 1 character triggers a Photon call and opens the dropdown.  Each visible row shows the name and address. No more than 5 results are shown at once. A spinner is visible for the duration of each in-flight request. |
| **PIC** | Alice |

### ***3.2.5. REQ-SRCH-005: Select a location via map pin, then route to it***

| Requirement ID | REQ-SRCH-005 |
| :---- | :---- |
| **Requirement Title** | Select a location via map pin, then route to it |
| **Priority** | Must |
| **Functional Requirement Description** | The user shall be able to choose any point on the map. Once chosen, the point shall be highlighted with a red pin, with a pop-up showing the current water depth at that point and a “Direction” button.  Tapping “Direction” shall transform the search bar into the Route Results panel (REQ-RTE-001) with the destination pre-filled to the chosen point, and the user shall then be able to search for or pick the origin. |
| **Acceptance Criteria** | Tapping any point on the map places a red pin.  The popup shows current water depth and a “Direction” button.  Tapping “Direction” opens the Route Results panel with the destination pre-filled; the origin field is empty and ready for input. |

### ***3.2.6. REQ-SRCH-006: Select a location via search, then route to it***

| Requirement ID | REQ-SRCH-006 |
| :---- | :---- |
| **Requirement Title** | Select a location via search, then route to it |
| **Priority** | Must |
| **Functional Requirement Description** | The user shall be able to search for a location using the search bar/panel (REQ-SRCH-002).  The resulting location's information shall be presented in the search panel, including current depth and a “Get directions” button.  Tapping “Get directions” shall transform the search bar into the Route Results panel (REQ-RTE-001) with the destination pre-filled, and the user shall then be able to search for or pick the origin. |
| **Acceptance Criteria** | Searching and selecting a place shows a detailed view with current depth and a “Get directions” button.  Tapping “Get directions” opens the Route Results panel with the destination pre-filled; the origin field is empty and ready for input. |

## **3.3. Vehicle Mode & Costing**

### ***3.3.1. REQ-VEH-001: Select vehicle mode (Car / Bike / Transit / Walk)***

| Requirement ID | REQ-VEH-001 |
| :---- | :---- |
| **Requirement Title** | Select vehicle type (Motorbike / Car / Truck) |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall present four top-level vehicle mode icons, horizontal row: Car, Bike, Transit, Walk. The selected mode icon shall display its travel time (e.g., “Car 13m”). Switching modes shall trigger a new routing request in the backend for the newly selected mode. The Car icon shall carry a ▾ affordance that opens the Car sub-profile dropdown (REQ-VEH-002). Bike shall reuse the existing motor scooter costing profile (20cm threshold). Transit and Walk have no existing costing profile or depth-cost logic in the backend today — see REQ-VEH-003. |
| **Acceptance Criteria** | All four mode icons are visible and selectable at all times. The selected icon shows its travel time once a route is computed. Switching modes updates route cards, map polylines, and ETA for the newly selected mode. The Car icon shows a ▾ indicator and opens the sub-profile dropdown on click. Bike mode returns flood-aware routes immediately (existing profile). Transit and Walk modes are functional once REQ-VEH-003 is complete. |

### ***3.3.2. REQ-VEH-002: Select a Car sub-profile (Sedan / SUV / Truck)***

| Requirement ID | REQ-VEH-002 |
| :---- | :---- |
| **Requirement Title** | Select a Car sub-profile (Sedan / SUV / Truck) |
| **Priority** | Should |
| **Functional Requirement Description** | The system shall present a dropdown under the Car icon (opened via REQ-VEH-001 item 4\) listing three sub-profiles: Sedan, SUV, Truck. Each sub-profile shall have its own depth threshold (sedan \= 25cm, SUV \= 30cm). Truck reuses the existing truck costing profile (50cm threshold). Selecting a sub-profile shall re-run the route request using that profile's threshold. The selected sub-profile shall persist while Car remains the active mode. |
| **Acceptance Criteria** | Clicking the Car icon ▾ opens a dropdown with exactly three options: Sedan, SUV, Truck. Selecting Truck re-runs the route request using the existing truck profile immediately. Selecting Sedan or SUV is only enabled once REQ-VEH-003 is complete. Selecting any sub-profile re-runs the route request using that profile's threshold. The selected sub-profile label is shown next to/under the Car icon and persists while Car remains active. |

### ***3.3.3. REQ-VEH-003: Extend routing cost model for Transit, Walk, Sedan, and SUV***

| Requirement ID | REQ-VEH-003 |
| :---- | :---- |
| **Requirement Title** | Extend the routing cost model with new vehicle sub-profiles |
| **Priority** | Should |
| **Functional Requirement Description** | The backend shall add Sedan and SUV as distinct Valhalla costing profiles (reusing auto costing with new depth thresholds), nested under Car per REQ-VEH-002. The backend shall add costing/depth-cost logic for Transit and Walk as new top-level modes per REQ-VEH-001, walk \= transit \= 40cm. UI repositioning (Truck moves from a top-level tab to the Car dropdown). This is backend work and is not part of the frontend build; it gates the Sedan/SUV portion of REQ-VEH-002 and all of Transit/Walk in REQ-VEH-001. |
| **Acceptance Criteria** | Sedan and SUV profiles are configured and return valid Valhalla routes. Transit and Walk have a defined costing/depth-cost approach, documented and reviewed before release. Bike and Truck continue to function unchanged (confirming no regression from the UI repositioning). Threshold values for all four new/moved profiles are documented and reviewed before release. Frontend (REQ-VEH-001, REQ-VEH-002) can successfully request and receive routes using all six profiles (Bike, Car→Sedan, Car→SUV, Car→Truck, Transit, Walk). |

## **3.4. Route Results**

### ***3.4.1. REQ-RTE-001: Display route alternatives with ETA, distance, and average depth***

| Requirement ID | REQ-RTE-001 |
| :---- | :---- |
| **Requirement Title** | Display route alternatives with ETA, distance, and average depth |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display a left panel (fixed 340px on desktop/tablet ≥768px; full viewport width below 768px, per REQ-RES-001) with origin/destination inputs and route cards, and a map on the right with color-coded route polylines and the bottom-right layer strip.  Route alternatives returned by GET /flood/route/forecast shall render as a list of cards, each showing route name (via street), ETA, distance, average depth, and status line, plus “See details ▸”.  The number of cards shall be dynamic (typically 1–3) — not hardcoded to a fixed count.  Card copy shall not imply independent route optimization for detour-variant alternatives.  While a route request is in flight, the panel shall show skeleton route cards (see §Interaction States) instead of a blank panel. |
| **Acceptance Criteria** | All returned routes render as cards, scaling correctly from 1 to N results, including the zero-route empty state (REQ-RTE-003).  Each card shows ETA, distance, and depth figures matching the API response. No card copy overstates route optimization quality. Skeleton cards are visible for the duration of the request and are replaced by real cards (or the empty/error state) once it resolves. |

### ***3.4.2. REQ-RTE-002: Color-code each route by safety status***

| Requirement ID | REQ-RTE-002 |
| :---- | :---- |
| **Requirement Title** | Color-code each route by safety status |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall color/border each route card and its corresponding map polyline (worst-segment depth bucket, per the four \--seg-\* states below). The passable/pre-closure/impassable classification is computed client-side by comparing each route's maximum depth against the active vehicle's unsafe threshold (returned by the route API response, per this requirement's threshold-source decision below — not hardcoded client-side). The backend does not hard-block dangerous routes by default (FLOOD\_USE\_HARD\_EXCLUDES=false), so this client-side classification is required. The draining state, by contrast, is computed backend-side: the backend compares each segment's consecutive forecast timesteps (per REQ-CALC-003's 5 time blocks) and returns a `draining: boolean` flag alongside each segment's depth value — the frontend reads this flag rather than re-deriving it, avoiding a second client/server drift risk on safety-critical classification (same reasoning as the threshold-source decision). The green/amber/red/blue route-status semantics described here use the separate \--seg-\* tokens; they must never be conflated with \--depth-\* (REQ-MAP-004). Green (--seg-passable): max depth \< 70% of vehicle threshold (threshold from API response). Amber (--seg-pre-closure): max depth 70%–100% of vehicle threshold. Red (--seg-impassable): max depth ≥ 100% of vehicle threshold (= backend's existing crosses\_threshold). Blue (--seg-draining): backend-returned `draining` flag is true — rendered instead of the depth-bucket color regardless of current bucket, signaling "improving, may clear soon" rather than a static safety verdict; the backend shall never set `draining: true` on a segment it also classifies impassable — draining only applies to passable/pre-closure segments (a currently-impassable segment stays red even if trending down). |
| **Acceptance Criteria** | Routes with max depth below the vehicle's safe threshold (from the API response) render green.  Routes exceeding the threshold are rendered red, with amber for an intermediate caution band, and blue for segments where the API returns `draining: true`. Colors match \--seg-\* values, not \--depth-\*. The frontend never independently computes the draining state from raw timesteps — it only reads the flag. |

### ***3.4.3. REQ-RTE-003: Display a no-safe-route state when applicable***

| Requirement ID | REQ-RTE-003 |
| :---- | :---- |
| **Requirement Title** | Display a no-safe-route state when applicable |
| **Priority** | Must |
| **Functional Requirement Description** | When the existing 6-hour departure scan finds no safe departure opportunity across all candidate routes, the system shall render a single explanatory card in place of route cards, stating that no safe route exists in the next 6 hours. Copy shall follow the non-alarmist register worked out in the journey storyboard (§User Journey): state the fact plainly, name the next check-in time, and avoid dramatized language ("danger", "warning" as a standalone headline) — e.g. "No safe route found in the next 6 hours. We'll keep checking — next update in 30 min." rather than an alarm-style banner. |
| **Acceptance Criteria** | The no-safe-route card appears only when the backend scan confirms no safe window exists. Standard route cards do not render alongside it.  Copy is clear and non-alarmist, consistent with existing localization conventions and the worked example above. |

### ***3.4.4. REQ-RTE-004: Open Route Detail from a route card or the map***

| Requirement ID | REQ-RTE-004 |
| :---- | :---- |
| **Requirement Title** | Open Route Detail from a route card or the map |
| **Priority** | Should |
| **Functional Requirement Description** | The system shall navigate to Route Detail (§3.5) when a user clicks a route card's “See details” affordance or taps the corresponding route polyline on the map.  Both entry points shall resolve to the same detail view for that route. |
| **Acceptance Criteria** | Clicking “See details” opens the Route Detail for that route. Tapping the matching polyline on the map does the same. Both paths produce an identical Route Detail state. |

### ***3.4.5. REQ-RTE-005: Return to Home from Route Results or Route Detail***

| Requirement ID | REQ-RTE-005 |
| :---- | :---- |
| **Requirement Title** | Return to Home from Route Results or Route Detail |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display a back/close affordance (← or ✕) in the header of the Route Results and Route Detail panels. Tapping it shall return the user to the Home screen (compact search pill, no route panel), clearing the current origin/destination and any computed route state. From Route Detail, the affordance returns to Route Results (one level back) rather than jumping straight to Home; a separate close action on Route Results returns to Home. This matches the wireframe's panel-swap pattern and gives every panel state an explicit, discoverable exit. |
| **Acceptance Criteria** | A back/close control is visible in the Route Results and Route Detail panel headers at all times those panels are shown. Tapping it from Route Detail returns to Route Results with that route's state intact. Tapping it (or a separate close action) from Route Results returns to Home with origin/destination and route state cleared. |

## **3.5. Route Detail**

### ***3.5.1. REQ-DET-001: Display a forward-looking depth forecast chart***

| Requirement ID | REQ-DET-001 |
| :---- | :---- |
| **Requirement Title** | Display a forward-looking depth forecast chart |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display the route's depth forecast as bars, bar height normalized to depth, bar color per the blue depth-magnitude scale (REQ-MAP-004, §8), with a dashed trend line overlaid and an interactive tooltip showing the exact depth value for the nearest bar on hover/tap-and-hold.  Window/bar count calls for 6 bars at \-30/now/+30/+60/+90/+120 (2-hour window, including a historical \-30 bar), if before now the model was not trigger than the \-30 will be 0. This endpoint lives on the existing `floodmap-backend` (port 8010), per the Phase 1 CEO plan's "no new FastAPI service" decision, querying the PostGIS pre-sampled per-segment depth table (overwritten transactionally each 1800s cycle, keyed by OSM way ID) directly, returning 6 bars (-30/now/+30/+60/+90/+120) — **not** flood\_road\_\<timestamp\>.geojson, which the backend has moved off of. Note: each model run generates 5 timesteps from now → \+120 (now/+30/+60/+90/+120); to obtain the \-30 bar, the endpoint must additionally query the timestep persisted immediately prior to now (TimescaleDB depth history, per the Phase 1 CEO plan) from the DB. Per REQ-DOC-001's start/stop hysteresis, a fully-stopped simulation (drainage confirmed) means some bars in the window may fall after the last real cycle — those bars reuse the last-known depth value and inherit the same staleness treatment as REQ-SRCH-003/REQ-REL-002 (`--stale-banner` styling on the chart), rather than a special missing-data state; this is expected to be rare, since the stop condition itself requires ~5 hours of confirmed drainage (10 cycles × 30min) before it fires. |
| **Acceptance Criteria** | The chart renders the agreed bar count and window with correct bar heights/colors for each bin, using the §8 blue scale.  Tooltip displays the correct depth value for the nearest bin on both mouse and touch input. Bars falling after a confirmed pipeline stop render the last-known value with `--stale-banner` styling instead of a false zero or a rendering error. |

### ***3.5.2. REQ-DET-003: Display turn-by-turn steps with per-step depth***

| Requirement ID | REQ-DET-003 |
| :---- | :---- |
| **Requirement Title** | Display turn-by-turn steps with per-step depth |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall display the selected route's maneuvers as an ordered step list, each showing the turn instruction, street name, distance, and depth for that step, with the left border colored by that step's depth bucket.  Start and end steps shall use a pin icon and a plain-language descriptor instead of a turn instruction. Per REQ-CALC-002, for a route A → B → C → D, the depth shown per step shall be the AVERAGE depth of that turn segment, and the route's overall average depth (A→D) shall also be calculated and displayed.  |
| **Acceptance Criteria** | Every maneuver in the route response is rendered as a step with the correct average depth and distance.  Start/end steps are visually distinct from turn steps. Step order matches the route's actual sequence. The route's whole-route average depth is visible on screen. |

### ***3.5.4. REQ-DET-004: Provide a “Start” call-to-action***

| Requirement ID | REQ-DET-004 |
| :---- | :---- |
| **Requirement Title** | Provide a “Start” call-to-action |
| **Priority** | Could |
| **Functional Requirement Description** | The system shall display a “Start” button at the bottom of Route Detail.  |
| **Acceptance Criteria** | The button is present and visually matches the wireframe's primary CTA styling.  Clicking it focuses/zooms the map to the first step.  No live navigation state is implied or attempted. |

## **3.6. Calculation**

### ***3.6.1. REQ-CALC-001: Set model output timestep to 1800s***

| Requirement ID | REQ-CALC-001 |
| :---- | :---- |
| **Requirement Title** | Set model output timestep to 1800s |
| **Priority** | Must |
| **Functional Requirement Description** | The simulation/model output timestep shall be 1800 seconds (30 minutes). |
| **Acceptance Criteria** | Model output timestep is confirmed as 1800 seconds in the simulation configuration. |
| **PIC** | Alice |

### ***3.6.2. REQ-CALC-002: Length-Weighted Average Depth Per Turn***

| Requirement ID | REQ-CALC-002 |
| :---- | :---- |
| **Requirement Title** | Length-Weighted Average Depth Per Turn |
| **Priority** | Must |
| **Functional Requirement Description** | For each maneuver (turn) on a route, the backend shall calculate a length-weighted average depth in centimeters. Method:  Identify all flood-affected road features from the flood GeoJSON that intersect the maneuver's route section;  for each intersecting feature, compute the length of overlap between that feature and the route section; Calculate the average depth as the sum of (feature depth\_cm × overlap length) divided by the sum of overlap lengths, i.e., avg\_depth\_cm \= Σ(depth\_cm\_i × overlap\_length\_i) / Σ(overlap\_length\_i).  This ensures a flood feature covering a longer portion of the turn contributes proportionally more to the average than a short, localized puddle. |
| **Acceptance Criteria** | Each maneuver's depth value is computed as a length-weighted average, not a maximum, across all intersecting flood-affected road features.  A flood feature's contribution to the average is proportional to its overlap length with the maneuver's route section.  The resulting average depth\_cm value is what feeds both the turn-by-turn step list (§3.5 / REQ-DET-003) and, after bucketing, the \--depth-\* display token — no color token (\--depth-\* or \--seg-\*) is itself averaged. Route-level average depth (origin → destination) is calculated the same way, aggregated across all maneuvers, weighted by maneuver length. |

### ***3.6.3. REQ-CALC-003: Calculate depth according to a time series***

| Requirement ID | REQ-CALC-003 |
| :---- | :---- |
| **Requirement Title** | Calculate depth according to a time series |
| **Priority** | Must |
| **Functional Requirement Description** | The system shall calculate the average depth from origin to destination across a forecast window of 2 hours at a 30-minute timestep — 5 time blocks: t0, t30, t60, t90, t120. Consecutive time-block deltas per segment feed the draining classification in REQ-RTE-002. |
| **Acceptance Criteria** | Average depth values are visualized on screen for each of the 5 time blocks. |
| **PIC** | Alice |

## **3.7. Recompose Docker**

### ***3.7.3. REQ-DOC-003: Gate simulation start/stop on forecast precipitation and drainage state***

| Requirement ID | REQ-DOC-001 |
| :---- | :---- |
| **Requirement Title** | Gate simulation start/stop on forecast precipitation and drainage state |
| **Priority** | Must |
| **Functional Requirement Description** | Call [tomorrow.io](http://tomorrow.io) API rainIntensity continuously, forecast hour is 2 hours, timestep 15 minutes (use AI to determine how frequently we should call the API while staying in the free tier). **Start:** while no simulation is running, trigger a new 3Di simulation the moment forecast rainIntensity exceeds 5 mm/h in any covered window (the "start engine"). **Continue-vs-stop (the "stop engine" depends on depth, not on rain, once a simulation is already running):** each cycle after a simulation has started, if forecast rainIntensity still exceeds 5 mm/h in any covered window, the simulation continues running regardless of current depth. If forecast rainIntensity has dropped below 5 mm/h, check the persisted per-segment depth history (PostGIS/TimescaleDB, per the Phase 1 CEO plan): only stop the simulation once **every** road segment's saved depth has read below 0.02 m for 10 consecutive cycles (drainage-confirmed hysteresis) — until that condition is met, the simulation keeps running even though rain is below threshold, to keep observing drainage. Once stopped, the pipeline does not publish new depth output until the next rain-triggered start; the most recently published output remains in place and continues to be reported per its existing age (REQ-SRCH-003 / REQ-REL-002). |
| **Acceptance Criteria** | A new simulation starts within one cycle of forecast rainIntensity crossing 5 mm/h while none is running. A running simulation continues every cycle rain stays at/above threshold, regardless of depth. A running simulation continues past a below-threshold rain reading until all segments have read below 0.02 m depth for 10 consecutive cycles; it stops only once that hysteresis condition is confirmed. After stopping, no new depth/GeoJSON/raster/upload artifact is produced until the next start, and the last-published output is served with its staleness age surfaced (REQ-SRCH-003/REQ-REL-002). Start/stop transitions complete as normal, successful DAG runs — never treated as task failures, no retries triggered. |

## **3.8. Navigation**

See REQ-RTE-005 (§3.4.5) for the Route Results / Route Detail → Home back-navigation requirement.

## **3.9. Responsive Layout**

### ***3.9.1. REQ-RES-001: Responsive panel behavior below 768px***

| Requirement ID | REQ-RES-001 |
| :---- | :---- |
| **Requirement Title** | Responsive panel behavior below 768px |
| **Priority** | Must |
| **Functional Requirement Description** | All left-panel states (search-expanded, Route Results, Vehicle Mode dropdown, Route Detail) shall use a fixed 340px width on viewports ≥768px. Below 768px, each panel shall become full viewport width, with the map revealed beneath it via the same expand/collapse interaction used to open the panel (search pill tap, Direction/Get Directions tap, See details tap). The bottom-right layer strip and back/close affordance (REQ-RTE-005) remain visible in both layouts. This applies uniformly instead of "stacked desktop columns" — panel width is the single responsive variable, not a full relayout per breakpoint. |
| **Acceptance Criteria** | On viewports ≥768px, all left panels render at a fixed 340px. Below 768px, the active panel renders at full viewport width and the map is not visible behind it until the panel is closed (REQ-RTE-005). No horizontal scroll occurs at any viewport width from 320px to desktop. |

## **3.10. Raster Tile Serving**

### ***3.10.1. REQ-MAP-005: Serve flood raster as an XYZ tile pyramid***

| Requirement ID | REQ-MAP-005 |
| :---- | :---- |
| **Requirement Title** | Serve flood raster as an XYZ tile pyramid |
| **Priority** | Must |
| **Functional Requirement Description** | `floodmap-backend` shall serve each cycle's flood-depth GeoTIFF as a standard XYZ tile endpoint (dynamic tiling via a library such as titiler/rio-tiler, or pre-cut tiles per cycle) rather than a single full-resolution image. The frontend flood layer (REQ-MAP-002/003/004) shall consume it via Leaflet's standard `L.tileLayer`, not a full-raster `L.imageOverlay`. This is backend scope, outside this URD's frontend-only boundary (§5 Constraints) — flagged here because it directly determines the frontend's rendering approach and was previously undecided in both this URD and the Phase 1 CEO plan. If the tile endpoint is unavailable or times out, it shall serve the last successfully-generated tile set instead of an error response, mirroring REQ-REL-001's graceful-degradation pattern for the rest of the pipeline. |
| **Acceptance Criteria** | The flood layer loads via tile requests scoped to the visible viewport/zoom, not one full-area image per refresh cycle. Pan/zoom performance does not visibly degrade as the 3Di model extent or output resolution grows. Tiles refresh on the existing 30s cadence (REQ-PER-002) without a full-layer reload. If the tile endpoint is down or times out, the map falls back to the last successfully-loaded tile set (matching REQ-REL-001's graceful-degradation pattern) rather than showing broken tile placeholders or blocking the base map. |

# **4\. List of Non-functional Requirements**

| Req. ID | Requirement Title | Requirement Description |
| :---- | :---- | :---- |
| **REQ-PER-000** | **Performance** |  |
| REQ-PER-001 | Route Response Time | Route calculation requests shall return within 2 seconds P95, consistent with the existing floodmap-backend's performance under the current Valhalla/MinIO setup. While in flight, the UI shows the loading treatment defined in §Interaction States (never a blank panel). |
| REQ-PER-002 | Data Refresh Cycle | The flood data cache shall refresh at its existing configured interval (default 30 seconds) without noticeably blocking UI interaction. |
| **REQ-USE-000** | **Usability** |  |
| REQ-USE-001 | Accessibility | The UI shall meet WCAG 2.1 AA: minimum 44px tap targets, 4.5:1 text contrast, all status information distinguishable by icon/pattern in addition to color, and keyboard navigability. Keyboard navigability covers all controls except arbitrary-point map-click (REQ-SRCH-001), whose keyboard-accessible equivalent is place-name search (REQ-SRCH-002) — see REQ-SRCH-001 for the documented rationale. Primary typeface: Helvetica, with Arial as the web fallback (both have solid Vietnamese diacritic coverage, relevant per REQ-USE-002). |
| REQ-USE-002 | Localization | All safety-critical and user-facing copy shall be available in Vietnamese, consistent with the existing copy register in FloodNav\_UIUX\_Spec\_v1\_0.md §9.1, and with the non-alarmist tone worked example in REQ-RTE-003. |
| **REQ-REL-000** | **Reliability** |  |
| REQ-REL-001 | Graceful Degradation | If MinIO or live flood data is unavailable, the system shall fall back to the existing bundled sample GeoJSON dataset (1,200 LineStrings, two time steps) rather than failing outright. |
| REQ-REL-002 | Stale Data Handling | The system shall never silently present flood data as current when it is stale — staleness must always be visually surfaced via the `--stale-banner` token once past the overdue threshold (REQ-SRCH-003, REQ-DET-002). |
| **REQ-SEC-000** | **Security** |  |
| REQ-SEC-001 | Deployment Exposure | No public-facing authentication is required for this release. The confirmed deployment model is an internally run instance shown to stakeholders on demand, with no public announcement. The instance should remain on a private network rather than have a publicly routable address as a light-touch mitigation, owned by whoever manages deployment — not a frontend requirement. |
| **REQ-COM-000** | **Compliance** |  |
| REQ-COM-001 | Design Token Consistency | All depth-magnitude visualizations shall use the single, shared \--depth-\* blue scale defined in §8 Design Tokens (superseding any prior FloodNav\_UIUX\_Spec\_v1\_0.md token values, which used a non-blue severity gradient in error), and all route/segment safety indicators shall use \--seg-\* (including \--seg-draining, REQ-RTE-002) — the two must never be visually conflated across any screen. `--alert-*` tokens are explicitly out of scope for this app (reserved for a future dashboard/alerting surface, per project history). `--storm-mode` and `--scenario-library` are wired into REQ-MAP-002/003; `--stale-banner` is wired into REQ-SRCH-003/REQ-REL-002. Dark-mode tokens (`--surface-*-dark`, `--text-*-dark`) are out of scope for this release — see §5 Constraints. |

## **Interaction States**

Loading, empty, error, success, and partial states for each stateful feature. Each row describes what the user SEES.

| FEATURE | LOADING | EMPTY | ERROR | SUCCESS | PARTIAL |
|---|---|---|---|---|---|
| Route calculation (REQ-RTE-001) | Skeleton route cards (card-shaped gray blocks, same count as the last known result or 2 if none yet) replace the panel content; origin/destination inputs disabled | No prior state — panel shows Home | No-safe-route card (REQ-RTE-003) or, on a hard API failure, "Couldn't calculate a route — try again" with a Retry button | Route cards render (REQ-RTE-001) | N/A — routes are all-or-nothing per request |
| Search autocomplete (REQ-SRCH-004) | Small inline spinner in the search pill/panel, dropdown stays closed until first result or error | Dropdown does not open (no query yet) | Field silently degrades to map-click (REQ-SRCH-002) — no error dialog, since map-click remains available | Dropdown shows up to 5 results | N/A |
| Flood layer activation (REQ-MAP-003) | Flood icon in layer strip pulses briefly while the new layer data loads | N/A — layer is either active or inactive | Falls back to bundled sample dataset (REQ-REL-001), no user-facing error | Flood icon shows solid active state, polygons render | N/A |
| Model trigger / storm-mode (REQ-MAP-003) | N/A | N/A | N/A | `--storm-mode` banner appears while active | N/A |

## **User Journey**

Emotional arc for the primary flow (citizen driver, Search → Get Directions → Route Detail → Start), applying REQ-RTE-003's non-alarmist tone throughout:

| STEP | USER DOES | USER FEELS | PLAN SPECIFIES? |
|---|---|---|---|
| 1. Land on Home | Opens the app, sees the map and search pill | Orientation — "what is this, where am I" | REQ-MAP-001 (base map centers on Hanoi), REQ-SRCH-002 (pill is the obvious, low-commitment entry point) |
| 2. Search / pick origin & destination | Types a place name or taps the map | Control — "I'm telling it exactly where I want to go" | REQ-SRCH-002/004 (autocomplete), REQ-SRCH-001 (map-click fallback), loading spinner (§Interaction States) keeps this step from feeling stalled |
| 3. See route colors (the critical trust moment) | Scans the route cards' green/amber/red/blue borders | This is where panic or confidence gets decided — must read as informative ("here's the safest option and why"), not alarming | REQ-RTE-002 (--seg-* semantics), REQ-RTE-003 (non-alarmist copy worked example), --seg-draining signals hope ("improving") rather than only danger |
| 4. Route Detail + Start | Opens details, scans turn-by-turn depths and the forecast chart, taps Start | Confidence to act — "I know what's ahead and when it gets worse" | REQ-DET-001 (forecast chart), REQ-DET-003 (per-step depth), REQ-DET-004 (Start CTA), REQ-RTE-005 (clear way back if they change their mind) |

# **5\. Constraints**

* Reuses the existing floodmap-backend (Valhalla 3.6.2 \+ MinIO, per ARCHITECTURE\_AND\_FEATURES.md §6) as-is — this document does not redefine backend API contracts.

* Scope is limited to wireframe 2a (Flood Routing Wireframes.dc.html, turn 2, option 2a) — 1a, 1b, and 1c are out of scope.

* Frontend framework decision (refactor the existing vanilla-JS app.js in place vs. a React rewrite) remains intentionally undecided in this document by request — noting for the record that a direct codebase read found no build tooling on the frontend at all (static index.html/app.js/styles.css served by nginx, no package.json), which favors refactor-in-place if/when this is revisited.

* No public-facing deployment is planned; the app runs continuously and is shown to stakeholders on demand.

* Geocoding (REQ-SRCH-002) depends on a third-party or self-hosted Photon instance not yet provisioned.

* Vehicle sub-profile work (REQ-VEH-002/003) depends on the backend costing design not yet finalized — exact thresholds and whether Bus/Walk are included remain open.

* QA is scoped against the existing bundled sample flood dataset (1,200 LineStrings, two time steps) rather than requiring new fixtures.

* Dark mode is explicitly out of scope for this release (light mode only), consistent with the internal-demo, not-public-facing framing above. The dark-mode tokens in §8 are reserved for a later phase.

* **Sequencing gate:** REQ-MAP-002/003/004, REQ-DET-001, REQ-MAP-005, and REQ-RTE-002's draining flag can be built against a mocked/stubbed API in parallel with backend work, but cannot be integration-tested end-to-end until the CEO plan's PR3 lands (T8 floodmap-backend rewrite, plus the newly-added T16 costing profiles, T17 tile serving, T18 draining flag). Do not treat this URD as fully parallel-buildable with the backend track — most of its acceptance criteria are unverifiable until PR3 ships.

# **6\. Deliverables**

* Working prototype of the routing map app implementing wireframe 2a's four screens (Home, Route Results, Vehicle Mode Dropdown, Route Detail) on top of the existing floodmap-backend.

* Updated design tokens: revised \--depth-\* blue scale merged into §8 below, with \--seg-\* (including \--seg-draining) usage clarified across all routing UI.

* Backend costing model extension for Sedan/SUV (and any confirmed additional) vehicle sub-profiles.

# **7\. Additional materials:** 

* The boundary of the routing engine: C:\\Users\\TECOTEC\\airflow\_new\\airflow\_tsm\\data\\inputs\\model-extend\\model-extend.shp 

* The wireframe: C:\\Users\\TECOTEC\\airflow\_new\\airflow\_tsm\\data\\inputs\\wireframe

# **8\. Design Tokens**

Canonical token values for this app. Supersedes any prior circulated token file (`FloodNav_UIUX_Spec_v1_0.md`, which did not exist in the repo and whose `--depth-*` values contradicted REQ-MAP-004/REQ-COM-001 — corrected below to the monochromatic blue scale those requirements specify).

```css
/* ── Flood Depth Magnitude Scale (monochromatic blue, REQ-MAP-004) ───────── */
--depth-0-20:        #E3F2FD;   /* 0–20 cm */
--depth-20-40:       #90CAF9;   /* 20–40 cm */
--depth-40-60:       #42A5F5;   /* 40–60 cm */
--depth-60-80:       #1E88E5;   /* 60–80 cm */
--depth-80-100:      #1565C0;   /* 80–100 cm */
--depth-100-plus:    #0D47A1;   /* >100 cm */
--depth-unknown:     #B0BEC5;   /* No data / stale */

/* ── Alert Level Colors (reserved — out of scope for this app, REQ-COM-001) */
--alert-watch:       #F9A825;   /* 🟡 Watch — future dashboard/alerting surface */
--alert-warning:     #E65100;   /* 🟠 Warning */
--alert-danger:      #B71C1C;   /* 🔴 Danger */
--alert-clear:       #1B5E20;   /* ✅ Cleared */

/* ── Segment State (REQ-RTE-002) ──────────────────────────────────────────── */
--seg-passable:      #4CAF50;
--seg-pre-closure:   #FFB300;   /* Amber — forecast impassable within 1h30 */
--seg-impassable:    #F44336;
--seg-draining:      #29B6F6;   /* Blue — depth falling, REQ-RTE-002/REQ-CALC-003 */

/* ── Surface / UI Chrome ───────────────────────────────────────────────────── */
/* Light mode (only mode in scope this release — see §5 Constraints) */
--surface-primary:   #FFFFFF;
--surface-secondary: #F5F5F5;
--surface-elevated:  #FAFAFA;
--border:             #E0E0E0;
--text-primary:      #212121;
--text-secondary:    #616161;
--text-disabled:     #9E9E9E;

/* Dark mode (reserved, not built this release) */
--surface-primary-dark:   #121212;
--surface-secondary-dark: #1E1E1E;
--surface-elevated-dark:  #242424;
--border-dark:            #303030;
--text-primary-dark:      #EEEEEE;
--text-secondary-dark:    #9E9E9E;

/* ── Status / Staleness ───────────────────────────────────────────────────── */
--stale-banner:      #795548;   /* Brown — pipeline overdue, REQ-SRCH-003/REQ-REL-002 */
--storm-mode:        #4A148C;   /* Purple — storm mode active, REQ-MAP-003 */
--scenario-library:  #0277BD;   /* Blue — data from scenario library, not live sim, REQ-MAP-002 */

/* ── Typography (REQ-USE-001) ─────────────────────────────────────────────── */
--font-primary: Helvetica, Arial, sans-serif;
```

## NOT in Scope

Design decisions considered during this review and explicitly deferred:

* **Dark mode** — tokens reserved in §8 but not built this release (light-only, matches internal-demo framing).
* **Keyboard-driven arbitrary-point map picking** — keyboard users route via place-name search (REQ-SRCH-002) instead; no crosshair/coordinate-entry fallback this release.
* **`--alert-*` tokens** — reserved for a future dashboard/alerting surface, not wired into this routing app.
* **Regenerating tone-of-copy for every safety-critical string** — only REQ-RTE-003's no-safe-route card got a worked copy example; the rest of REQ-USE-002's Vietnamese localization pass is existing scope, not new.

## What Already Exists

Existing UI patterns and behavior this plan reuses rather than rebuilding:

* Leaflet map instance, base layer, and pan/zoom (existing floodmap-frontend, REQ-MAP-001).
* Map-click point-picking behavior (existing floodmap-frontend, REQ-SRCH-001).
* Photon place-search integration (already implemented per git history — `b737beb Implement place search functionality with Photon API integration`).
* Existing motor-scooter (Bike) and truck costing profiles in the Valhalla backend (REQ-VEH-001/002).
* Existing bundled sample flood dataset (1,200 LineStrings, two time steps) used for graceful degradation (REQ-REL-001) and QA (§5 Constraints).

No DESIGN.md exists at the repo root. §8 Design Tokens in this document is now the closest thing to one for this app; recommend `/design-consultation` if a repo-wide DESIGN.md is wanted later.

## Implementation Tasks
Synthesized from this review's findings. Each task derives from a specific
finding above. Run with Claude Code or Codex; checkbox as you ship.

- [ ] **T1 (P1, human: ~10min / CC: ~2min)** — Navigation — Add back/close affordance to Route Results & Route Detail panel headers
  - Surfaced by: Pass 1 (Information Architecture) — no defined path back to Home
  - Files: `floodmap/valhalla-flood-road-test/frontend/app.js`, `frontend/index.html`, `frontend/styles.css`
  - Verify: manual check — tapping back from Route Detail returns to Route Results; from Route Results returns to Home with state cleared (REQ-RTE-005)
- [ ] **T2 (P1, human: ~20min / CC: ~5min)** — Interaction states — Add loading states for route calc, search, flood-layer activation
  - Surfaced by: Pass 2 (Interaction State Coverage) — no loading state anywhere
  - Files: `frontend/app.js`, `frontend/styles.css`
  - Verify: throttle network, confirm skeleton cards / spinner / icon pulse render per §Interaction States
- [ ] **T3 (P2, human: ~15min / CC: ~5min)** — Copy — Write non-alarmist no-safe-route copy per REQ-RTE-003 worked example
  - Surfaced by: Pass 3 (User Journey) — REQ-RTE-003 had no worked copy example
  - Files: `frontend/app.js` (or wherever route-card copy is generated), Vietnamese localization file
  - Verify: no-safe-route state renders the exact worked copy pattern, in Vietnamese per REQ-USE-002
- [ ] **T4 (P2, human: ~10min / CC: ~5min)** — Typography — Set `--font-primary: Helvetica, Arial, sans-serif` app-wide
  - Surfaced by: Pass 4 (AI Slop Risk) — no production typeface specified
  - Files: `frontend/styles.css`
  - Verify: visual check across Vietnamese diacritic strings (ư, ề, ữ)
- [ ] **T5 (P1, human: ~15min / CC: ~5min)** — Colors — Implement corrected `--depth-*` blue scale and `--seg-draining` from §8
  - Surfaced by: Pass 5 (Design System Alignment) — depth-scale contradiction, missing draining state
  - Files: `frontend/styles.css`, flood polygon rendering code, route-card/polyline coloring code
  - Verify: flood polygons render only blue/gray shades; route segments can render blue when depth is falling and not impassable
- [ ] **T6 (P2, human: ~20min / CC: ~5min)** — Status indicators — Wire `--stale-banner`, `--storm-mode`, `--scenario-library` into existing badges
  - Surfaced by: Pass 5 (Design System Alignment) — tokens existed but were unreferenced
  - Files: `frontend/app.js`, `frontend/styles.css`
  - Verify: staleness badge switches to brown past overdue threshold; storm-mode banner and scenario-library icon badge appear/disappear correctly
- [ ] **T7 (P1, human: ~20min / CC: ~5min)** — Responsive — Standardize panel width to 340px and add <768px full-width breakpoint
  - Surfaced by: Pass 6 (Responsive & Accessibility) — panel-width inconsistency, no mobile spec
  - Files: `frontend/styles.css`, `frontend/index.html`
  - Verify: resize to 375px and 1024px, confirm panel behavior matches REQ-RES-001

_No new tasks from Pass 7 (Unresolved Design Decisions) — the one open item (fixing the external token source) was explicitly skipped by the user, not deferred as a task._

**Added by `/plan-eng-review`:**

- [ ] **T8 (P1, human: ~1hr / CC: ~15min)** — Tests — Add `tests/depth_scale.test.js`, `tests/route_status.test.js`, `tests/staleness.test.js`, `tests/forecast_chart.test.js`
  - Surfaced by: Test Review — new safety-critical pure functions had zero test coverage
  - Files: `tests/depth_scale.test.js`, `tests/route_status.test.js`, `tests/staleness.test.js`, `tests/forecast_chart.test.js`, plus the `frontend/depth_scale.js`/`route_status.js`/`staleness.js` modules they test (new, mirroring `point_depth.js`'s pattern)
  - Verify: `node --test tests/` (matching existing `test_point_depth.js` convention) — all boundary-value cases pass
- [ ] **T9 (P1, human: ~10min / CC: ~5min)** — Architecture — Consume vehicle threshold from route API response, not hardcoded client-side
  - Surfaced by: Architecture Review — threshold-source ambiguity risked frontend/backend drift
  - Files: `frontend/app.js` (route response parsing), `frontend/route_status.js`
  - Verify: changing a threshold value backend-side (T16) changes frontend classification without a frontend code change
  - **Depends on:** T16 (backend must return threshold in response) — see CEO plan
- [ ] **T10 (P1, human: ~5min / CC: ~5min)** — Architecture — Read `draining` flag from API response instead of computing client-side
  - Surfaced by: Outside-voice cross-model tension — client-side trend computation duplicated backend logic
  - Files: `frontend/route_status.js`
  - Verify: `route_status.test.js`'s draining test cases pass reading the flag, not recomputing from raw timesteps
  - **Depends on:** T18 (backend must emit the flag) — see CEO plan
- [ ] **T11 (P2, human: ~15min / CC: ~5min)** — Reliability — Tile fallback to last-good tile set on endpoint failure
  - Surfaced by: Failure Modes review — no failure handling spec'd for the new tile endpoint
  - Files: `frontend/app.js` (Leaflet `L.tileLayer` error handling), depends on T17's backend fallback behavior
  - Verify: simulate tile-endpoint 5xx/timeout, confirm map shows last-good tiles instead of broken placeholders

## Test Plan

New pure-function logic surfaces, evaluated against the existing repo convention (`tests/test_point_depth.js` using Node's built-in `node:test` against pure exports from `frontend/point_depth.js`). DOM-heavy flows have no existing test harness in this repo (no jsdom/E2E framework) and this plan does not introduce one — they stay manual-QA per their own acceptance criteria (REQ-RES-001, REQ-RTE-005, §Interaction States).

```
CODE PATHS (new pure functions)                         COVERAGE
[+] frontend/depth_scale.js (new, mirrors point_depth.js pattern)
  └── bucketDepthCm(depthCm) → --depth-* token
      ├── [GAP] 0-20cm, 20-40cm, ..., >100cm (6 bands)   → depth_scale.test.js
      ├── [GAP] boundary values: exactly 20/40/60/80/100 → depth_scale.test.js
      └── [GAP] no-data/undefined → --depth-unknown       → depth_scale.test.js
[+] frontend/route_status.js (new)
  └── classifySegment(depthCm, thresholdCm, drainingFlag) → --seg-* token
      ├── [GAP] < 70% threshold → passable                → route_status.test.js
      ├── [GAP] 70-100% threshold → pre-closure            → route_status.test.js
      ├── [GAP] boundary: exactly 70%, exactly 100%        → route_status.test.js
      ├── [GAP] >= 100% threshold → impassable              → route_status.test.js
      ├── [GAP] drainingFlag=true + not impassable → draining (reads flag, does not re-derive from timesteps — draining trend detection moved backend-side per this review) → route_status.test.js
      └── [GAP] drainingFlag=true + impassable → stays impassable (backend contract: never sets draining on an impassable segment, but frontend still guards it) → route_status.test.js
[+] frontend/staleness.js (new)
  └── isStale(lastUpdateTs, now, overdueThresholdMs) → boolean
      ├── [GAP] below threshold → false (neutral badge)     → staleness.test.js
      ├── [GAP] at/above threshold → true (--stale-banner)  → staleness.test.js
      └── [GAP] boundary: exactly at threshold              → staleness.test.js

COVERAGE: 0/16 paths tested (0%) — all new this review, none implemented yet
QUALITY TARGET: ★★★ (behavior + boundary + edge) for all three modules — these are
safety-classification functions; boundary values are not edge cases here, they're
the primary risk (an off-by-one at the 70%/100% threshold silently mislabels a
route's safety).
```

**Test requirements added to the plan:**

1. `tests/depth_scale.test.js` — `node:test` against `frontend/depth_scale.js`'s `bucketDepthCm()`. Cases: one per band in §8's 7-token scale, plus the 5 exact boundary values (20/40/60/80/100cm) to pin which side of the boundary each band owns, plus undefined/null → `--depth-unknown`.
2. `tests/route_status.test.js` — `node:test` against `frontend/route_status.js`'s `classifySegment()`. Cases: passable/pre-closure/impassable happy paths (from API-supplied threshold), the 70%/100% boundary values, `drainingFlag=true` on a passable/pre-closure segment → draining, and the defensive case of `drainingFlag=true` alongside an impassable depth reading → stays impassable (frontend-side guard, even though the backend contract says this combination shouldn't occur).
3. `tests/staleness.test.js` — `node:test` against `frontend/staleness.js`'s `isStale()`. Cases: below/at/above the overdue threshold.
4. `tests/forecast_chart.test.js` — `node:test` against the forecast-chart bar-building logic (REQ-DET-001). Case: a requested timestep is missing from the endpoint response (simulated post-drainage-stop gap) → the bar reuses the last-known value and applies `--stale-banner` styling, rather than rendering a false zero or throwing on the missing row.

These are P1 — they gate the same safety-critical logic REQ-RTE-002 and REQ-MAP-004 depend on; see T8 in Implementation Tasks below.

## NOT in Scope (Eng Review)

* **Redesigning app.js's module structure** — the vanilla-JS, no-build-tooling architecture is an explicit, already-settled Constraints decision ("intentionally undecided... by request"); not relitigated here.
* **E2E/browser test framework adoption** — no jsdom/Playwright/Cypress exists in this repo; adding one is a separate infra decision, not bundled into this URD's test requirements.
* **PR2/PR3 backend implementation itself** — T16/T17/T18 are scheduled in the CEO plan, not built here; this URD only specifies what the frontend needs from them.
* **Strategic re-scoping** (outside voice finding 7: whether this much UI polish is warranted before the backend pipeline ships) — a CEO-review-level question, not an eng-review fix; flagged for the user's judgment, not acted on.

## What Already Exists (Eng Review)

* `tests/test_point_depth.js` + `frontend/point_depth.js` — the exact pure-function/`node:test` pattern this review's new test requirements (T-test files) follow.
* `scripts/run_route_tests.py` + `scripts/flood_utils.py` — existing Python route-testing harness against `requests/`/`responses/` fixtures; not touched by this URD's frontend-only scope, but the pattern backend engineers should extend for T16-T18's own tests.
* Existing Bike/Truck Valhalla costing profiles — reused as-is by REQ-VEH-001/002, not rebuilt.

## Diagrams

No new state machine or multi-step pipeline complex enough to warrant an inline ASCII diagram beyond what's already in §User Journey and the Test Plan's coverage diagram above. The panel-state transitions (Home ↔ Route Results ↔ Route Detail) are a simple 3-state linear flow, fully described by REQ-RTE-005's acceptance criteria — a diagram would restate the prose without adding clarity.

## Failure Modes

| New codepath | Realistic failure | Test? | Error handling? | User sees |
|---|---|---|---|---|
| Route calc request (REQ-RTE-001) | Backend timeout / 5xx | Covered by §Interaction States' error treatment | Yes — "Couldn't calculate a route — try again" + Retry | Clear, recoverable |
| Photon search (REQ-SRCH-002) | Geocoder down/slow | N/A (degrade path, not a code branch to unit-test) | Yes — degrades to map-click | Clear (silent fallback, no dead end) |
| Forecast chart -30 bar (REQ-DET-001) | Requested cycle missing (pipeline stopped, drainage-confirmed) | Yes — `tests/forecast_chart.test.js` (added this review) | Yes — reuse last-known + `--stale-banner` styling | Clear (stale, not silently wrong) |
| `draining` flag (T18, backend) | Backend sets `draining:true` on an impassable segment (contract violation) | Yes — `route_status.test.js`'s defensive case | Yes — frontend guards it (stays impassable) | Correct even if backend misbehaves |
| Tile endpoint (T17) | Tile server down/slow | Not covered by a frontend test (backend-side fallback, no frontend branch to test) | Yes — falls back to last-good tile set (added this review, mirrors REQ-REL-001) | Map stays usable, no broken tiles |

All failure modes identified in this review now have a test and/or explicit error handling — no critical gaps remain open.

## Worktree Parallelization Strategy

| Step | Modules touched | Depends on |
|------|----------------|------------|
| Frontend UI build (REQ-MAP/SRCH/VEH/RTE/DET/RES, T1-T7 in Implementation Tasks) | `frontend/` | Can start immediately against a mocked API |
| Backend costing (T16) | Valhalla config, `floodmap-backend` | Depends on PR2 (raster cutover, already in progress per CEO plan) |
| Backend tile serving (T17) | `floodmap-backend` (new endpoint) | Depends on T8 |
| Backend draining flag (T18) | `floodmap-backend` route response | Depends on T5/T6 |
| New frontend unit tests (T8 in this review's Implementation Tasks) | `tests/` | Independent of the above — pure functions, can be written and tested against mock inputs before backend lands |

Lane A: Frontend UI build + new unit tests (independent, no shared modules with backend work).
Lane B: Backend T16 → T17 → T18 (sequential, all touch `floodmap-backend`, and T17/T18 build on T8's PostGIS/raster foundation from T16's PR3).

Launch A and B in parallel worktrees. A can proceed fully against mocks; **integration testing of A against real data is blocked until B's T8/T16/T17/T18 land** (per the Sequencing Gate note in §5 Constraints). No merge-conflict risk — Lanes A and B touch disjoint module directories (`frontend/` vs `floodmap-backend`).

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 (parent doc reviewed separately) | — | See CEO plan `2026-08-07-floodnav-phase1-core-pipeline.md` |
| Codex Review | `/codex review` | Independent 2nd opinion | 1 | issues_found (claude fallback, Codex not installed) | 7 findings, 6 substantive points addressed |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | clean | 11 issues, 0 unresolved, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | issues_open | score: 6/10 → 8/10, 9 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**CODEX:** Not installed — outside voice ran as a Claude subagent (same model family, fresh context, not a true cross-model check).

**VERDICT:** DESIGN + ENG CLEARED — ready to implement, gated on the CEO plan's PR2/PR3 backend sequencing (T8, T16, T17, T18) per this review's Sequencing Gate note in §5 Constraints.

NO UNRESOLVED DECISIONS
