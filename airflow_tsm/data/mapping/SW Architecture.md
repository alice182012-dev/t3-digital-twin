# FloodNav — SW Architecture

> OCR'd/transcribed from `SW Architecture.png` (Fibery whiteboard). Structure follows the C4 model: System Context → Container → Component-level detail for each container.

---

## 1. System Context Diagram

**FloodNav** — Real-time flood navigation and warning platform for Hanoi. Runs a continuous hydrodynamic simulation pipeline to produce flood depth maps, vehicle-aware routing, forecast histograms, and push alerts — updated approximately every 30 minutes.

### Actors & External Systems

| Actor / System | Description | Relationship to FloodNav |
|---|---|---|
| **Hydraulic Engineer** | Domain expert who configures the simulation model | Configures hydrodynamic model and simulation templates (one-time manual setup) |
| **City council** | Government operations & response | Monitors city flood status and logs dispatch decisions |
| **Citizen** | Urban resident / driver | Views flood map, plans route |
| **3Di** | Cloud-based hydraulic simulation engine | FloodNav submits simulation jobs to 3Di, uploads rainfall and water level boundary conditions, and downloads depth results (NetCDF) after each completed run — via "Submit simulation jobs and input for model" |
| **Trung tâm dự báo KTTV Quốc Gia APIs** | Vietnamese National Centre for Hydro-Meteorological Forecasting | FloodNav polls this service each simulation cycle to retrieve the latest rainfall forecast, used as the rainfall boundary condition for the hydraulic model — "Deliver rainfall input" |
| **Gauge network APIs** | Real-time water level sensors deployed at key locations across the city | FloodNav reads current observed water levels from these sensors at the start of each cycle to hot-start the simulation from real observed conditions — "Deliver initial water input" |
| **FCM / APNs** | Firebase Cloud Messaging (Android) and Apple Push Notification service (iOS) | FloodNav dispatches Danger, Warning, and Watch push notifications to citizen devices via these services after each simulation cycle completes — "Send push alerts about flooding to" / "Dispatches flood push notifications to citizen devices via" |

Additional flows: "Deliver simulation results to be post-processed" (3Di → FloodNav).

### Rationale (sticky note — Mai Anh)

**1. Users:**
- Citizens: make **immediate** personal safety decisions: whether to travel, which route to take, whether to stay where they are.
- The city council: coordinate operational response across the city: dispatching traffic police, making public announcements, identifying which public services are inaccessible.
- Ride-hailing services: **data feed** to protect their drivers and manage fleet routing → they are not using the FloodNav UI, they are consuming the data programmatically.

**2. Community reports:**
- Live user feedback (at this phase): flow into the system from citizens but are isolated from the simulation output → cannot contaminate the hydrodynamic model results that emergency decisions are based on.
- Community data is stored separately and surfaced as an informational layer only, with its primary **long-term value** being post-event model calibration.

**3. The push notification services (FCM/APNs):**
- External systems that FloodNav calls, rather than as a channel to users, because the alert delivery contract is one-way and asynchronous — FloodNav dispatches a payload and has no guarantee or visibility into delivery. This architectural boundary means alert reliability depends on a third party, which is flagged as a risk requiring a fallback (in-app polling when the app is open).

### Extended context — Ride-hailing partner API (future / Phase 3)

Two **Ride-hailing service** actors (GrabBike, XanhSM, Be, etc.) shown with data flows:
- "Real-time flood data & forecast" (FloodNav → ride-hailing service)
- "GPS signal, fleet location" (ride-hailing service → FloodNav)

**Sticky note (Mai Anh):**

> For partner API, Phase 3 should be extended to include:
>
> A **partner API layer** added to the REST API container — two new endpoints:
> 1. `POST /partner/flood/points` for batch coordinate depth queries
> 2. `GET /flood/vtiles/{z}/{x}/{y}.mvt` for Mapbox Vector Tile serving with road segment flood attributes embedded.
>
> A **fifth postprocessing worker** — MVT tile generator — added to the simulation pipeline. It reads road segment depth data from PostGIS after each cycle and generates vector tile files alongside the existing PNG tiles, pushing them to the CDN.
>
> **Partner authentication** — B2B API keys with rate limiting per partner, separate from citizen-facing endpoints. This protects citizen app latency from high-volume fleet queries.
>
> **What this means for the container diagram in Phase 3**
>
> The REST API box subtitle changes from "all application endpoints" to "citizen + partner endpoints." The simulation pipeline box gains the MVT worker. A new external actor — **API partner (e.g. Grab, Xanh SM)** — appears in the system context with a single two-way arrow: they call the REST API, the REST API responds with flood data. No GPS posting from their side — purely a consumer relationship.

**Small note (bottom of frame):**
> + 15-min fast-track mode · fast-track triggered by: gauge rise >5 cm/15 min, NCHMF forecast >70 mm/hr within 2h, 3+ community flood reports in 30 min, or manual operator override · auto-reverts to default after 2 consecutive calm cycles ·

---

## 2. Container Diagram

**FloodNav System** boundary contains the following containers:

| Container | Tech | Responsibility |
|---|---|---|
| **Mobile / web app** | React Native / Web | Citizen flood map, routing, alerts, histogram |
| **City council dashboard** | React Web App (SPA) | Operational flood map, pre-closure feed, dispatch log |
| **REST API** | FastAPI / Python | Single contractual surface for all clients |
| **Simulation pipeline** | Python / Airflow (server-side) | Runs constant_cycle (6h) + background_cycle (24h) simulations, ingests rainfall + gauge data, calls 3Di API, produces GeoTIFFs |
| **Postprocessing Service** | Python workers / Airflow tasks (server-side) | Consumes GeoTIFFs after simulation completes; runs Depth Calculator, Metric Extractor, Tile Generator, Segment Extractor, Histogram Builder, User Alert Engine, Segment Alert Engine, District Aggregator |
| **Flood Routing Engine** | Server-side app (Valhalla) | Flood-weighted graph routing → re-weighted by Postprocessing each cycle, queried by REST API at request time |
| **Map tile CDN** | S3 + CloudFront (blob store) | XYZ PNG flood tiles → written by Postprocessing, read by both clients directly |
| **Redis** | Database | Three logical roles: Task Queue (pipeline fan-out), Pub/Sub bus (cycle completion events), Short-TTL cache (API responses) |
| **TimescaleDB** | Database | Institution histograms (24h hourly bars), background_cycle forecast series, depth history |
| **User Location Store** | PostgreSQL | User GPS coordinates + consent mode → read by User Alert Engine |
| **PostGIS** | PostgreSQL + PostGIS | Segment depths, pre-closure flags, forecast intervals, district summary, institution data, dispatch log, community reports |

### Key data flows

- Hydraulic Engineer → uploads `gridadmin.h5`, simulation templates, node mapping (one-time manual) → **3Di**
- **Gauge network APIs** → "Reads current water levels at cycle start via HTTPS" → **Simulation pipeline**
- **Trung tâm dự báo KTTV Quốc Gia APIs** → "Polls rainfall forecast (GRIB2/NetCDF) every cycle via HTTPS" → **Simulation pipeline**
- **Simulation pipeline** → publishes simulation-complete event with GeoTIFF file paths via Redis pub/sub → **Redis**
- **Postprocessing Service** subscribes to simulation-complete event, receives Tier 1/2 worker task fan-out via Redis pub/sub + task queue
- **Postprocessing Service** writes: segment depths / pre-closure flags / forecast metrics / district summary (→ PostGIS), institution histogram bars (→ TimescaleDB), user GPS + consent mode reads (→ User Location Store), pushes rendered XYZ PNG flood tiles (→ Map tile CDN via S3 API), re-weights routing graph with per-segment depths each cycle (→ Flood Routing Engine via Valhalla API)
- **REST API** reads from Redis (pipeline status/last-completed timestamps), TimescaleDB (institution histograms, forecast series, depth history), User Location Store, PostGIS (segment depths, pre-closure flags, district summary, institution data, dispatch log), and requests flood-weighted routes from Flood Routing Engine (Valhalla HTTP API)
- **Mobile/web app** and **City council dashboard** → fetch XYZ PNG flood tiles directly via HTTPS from Map tile CDN (redirected via REST API HTTP 302); request flood data/routes/alerts/pipeline status (Mobile) and pre-closure feed/district summary/institution access/dispatch log (Dashboard) via JSON/HTTPS from REST API
- **REST API** → dispatches Danger 🔴 / Warning 🟠 / Watch 🟡 push notifications via HTTPS / FCM REST → **FCM/APNs** → sends push alerts to Citizen

---

## 3. Simulation Pipeline — Dual-Horizon Simulation

### Upstream inputs
- **Trung tâm dự báo KTTV Quốc Gia**: Rainfall forecast & weather forecast
- **Gauge network**: River sensors
- **City Council**: Hydrodynamic model input (DTM, drainage, structure)
- **OpenStreetMap**: Road networks

### One-time manual setup (expert, outside automated pipeline boundary)

| Step | Detail |
|---|---|
| **3Di model build** | Hydraulic engineer builds 3Di schematisation from DTM (1–2m LiDAR), building footprints, drainage network, land cover, control structures, Manning's n roughness coefficients. Output is a versioned model stored as geopackage → updated when source data changes significantly (annual review or post-major-survey). Not automated → requires domain expert judgement. |
| **Calculation node mapping** | Engineer defines the fixed list of 3Di calculation node IDs that correspond to gauge station locations. Stored as a static configuration file; each row maps a gauge station identifier to a 3Di calculation node ID. Used by gauge ingestion every cycle. Updated only when model is rebuilt. |
| **Rainfall spatial mapping** | Engineer defines the spatial interpolation grid mapping NCHMF forecast cells to 3Di mesh cells. Stored as a fixed raster lookup (NetCDF). Used by rainfall ingestion every cycle to project forecast rainfall onto the mesh. Updated only when model mesh or NCHMF grid resolution changes. |
| **Simulation templates** | Engineer creates two 3Di simulation templates: 1. **constant_cycle template**: duration = 21,600s (6h) / output_time_step = 900s (15 min) / produces 25 GeoTIFFs per run. 2. **background template**: duration = 86,400s (24h) / output_time_step = 3,600s (60 min) / produces 25 GeoTIFFs per run. Versioned alongside model — updated when model or simulation parameters change. |

Output: geopackage, `gridadmin.h5`, node mapping config (.csv), rainfall spatial mapping (NetCDF) → versioned + stored.

### Automated constant_cycle pipeline (6h simulation, runs continuously — next cycle starts immediately after completion — must complete within 18 min)

**Airflow orchestrator:**
1. Continuous-schedule DAG: next constant_cycle starts immediately after the previous one completes; each cycle must finish within 30-min SLA.
2. Monitors task health.
3. Triggers retry on failure.
4. Raises SLA alert if cycle exceeds 30-min budget.
5. Logs cycle start + current mode for staleness tracking.
6. Publishes mode state to `/pipeline/mode` API.

**Rainfall ingestion:** Polls NCHMF every cycle → parses NetCDF rainfall forecast → applies fixed spatial mapping to project forecast onto 3Di mesh cells → outputs rainfall boundary condition file for simulation engine.

**Gauge ingestion:** Reads current water level from each gauge station API at cycle start → this is a hot-start: each cycle begins fresh from observed state, not carried forward from previous cycle → looks up each gauge reading against the fixed calculation node mapping config → produces `initial_waterlevels.csv` with exactly two columns: `id,value` (e.g. `8548,0.43`) — id = 3Di calculation node ID (not connection node ID), value = current observed water level in metres. Any gauge station with a failed reading uses the previous cycle's value as fallback. CSV is passed directly to simulation engine as 1D initial water levels boundary condition.

↓ rainfall boundary (rain.nc, 6h) + `initial_waterlevels.csv` + `gridadmin.h5` (fixed)

**3Di Hydrodynamic calculation core API:**
1. Connect to 3Di API: Authenticates using personal API token via ThreediApi config → selects the fixed threedimodel by ID (set during manual model build) → retrieves `constant_cycle` template for this model.
2. Create simulation instance: Creates a new simulation from the **per-cycle template** → sets `start_datetime` to cycle start time → sets duration to simulation horizon → simulation is created but not yet started.
3. Upload `initial_waterlevels.csv` to threedimodel: Uploads gauge-derived CSV to 3Di → 3Di processes and validates the file server-side → polls until state = "valid" before proceeding → max 900 retries × 1s wait.
4. Assign initial water levels to simulation: Removes any existing 1D water level files or constant values from this simulation instance before assigning the new one → prevents conflict from previous cycle's assignments → then posts the new initial water level file to the simulation.
5. Upload `rain.nc` to simulation: Uploads rainfall timeseries as NetCDF directly to the simulation event → 3Di processes the file server-side → polls until file state = "processed" → max retries × 1s wait.
6. Start simulation: Sends start action to 3Di → simulation runs on 3Di compute infrastructure → must complete within ~18 min to stay within 30-min pipeline budget.
7. Download `results_3di.nc` and `gridadmin.h5`: Lists available result files for the finished simulation → downloads `results_3di.nc` → downloads `gridadmin.h5` from threedimodels API (model-specific, required by depth calculator) → saves to local working directory for depth calculator.

↓ outputs `results_3di.nc` + `gridadmin.h5` (25 timesteps over 6h)

### Background 24h simulation (runs every 3 hours)

**Background Airflow DAG:**
1. Separate DAG from constant_cycle pipeline: fixed 3-hour schedule.
2. Does not block or interfere with per-cycle pipeline.
3. Runs on same or separate compute, budget = 30–60 min.

**Background 3Di orchestrator:**
1. Creates simulation from **background_cycle template** (duration = 86,400s / 24h, output_time_step = 3,600s / 60 min).
2. Uses latest gauge readings for initial conditions.
3. Uses latest NCHMF 24h forecast for rainfall boundary.
4. Produces NetCDF.
5. Downloads results to working directory.

↓ outputs `results_3di.nc` + `gridadmin.h5` (25 timesteps over 24h)

**Outputs ready for depth calculator** (both pipelines converge here):
1. `results_3di.nc` + `gridadmin.h5` written to local working directory.
2. Airflow triggers depth calculator task.
3. `constant_cycle` results feed Tier 1 + Tier 2 workers.
4. `background_cycle` results feed background_cycle histogram writer.

↓ `results_3di.nc` + `gridadmin.h5` → depth calculator (25 timesteps)

Supporting reference boxes: **3Di API** (`api.3di.live` · all simulation control), **Airflow** (Orchestrates steps · passes run_type · monitors SLA), **Local working dir** (Staging: `results_3di.nc` + `gridadmin.h5`), **Run type** (Passed by Airflow DAG: `constant_cycle` (6h) / `background_cycle` (24h)).

### 3Di API orchestrator — internal step sequence (reference diagram)

Inputs feeding the orchestrator:
- **From gauge ingestion**: `initial_waterlevels.csv` — id (calc node ID), value (water level m)
- **From rainfall ingestion**: `rain.nc` = timeseries NetCDF spatially interpolated onto mesh, covers 6h (constant_cycle) or 24h (background)
- **Fixed (manual setup)**: `gridadmin.h5` = versioned 3Di model referenced via threedimodel_id
- **Run type**: Passed by Airflow DAG — `constant_cycle` / `background_cycle`

(Steps detailed above under "3Di Hydrodynamic calculation core API" — same 7-step sequence: Connect → Create simulation instance → Upload initial_waterlevels.csv → Assign initial water levels → Upload rain.nc → Start simulation → Download results.)

---

## 4. Post-Processing Pipeline

### Constant_cycle pipeline

**Depth calculator**
Runs `threedidepth.calculate_waterdepth()` per timestep using `results_3di.nc` + `gridadmin.h5` + DEM → outputs a sequence of GeoTIFF files (one per timestep) → renames each file with Vietnam-time timestamp → runs with parallel workers to stay within cycle time budget.

↓ outputs 25 × `depth_YYYYMMDD_HHMMSS.tif` (T+0, T+15m, T+30m, ... T+6h)

**Flood metric extractor**
Scans full GeoTIFF series across all timesteps to compute time-series metrics per grid cell and road segment → convert to **centimeters**:
1. **Time to peak flood**: timestep where depth is maximum.
2. **Time when water depth decreases**: first timestep where depth consistently decreases after peak.
3. **When is road passable again**: first timestep where depth drops below vehicle threshold (computed per vehicle type: xe máy 20cm / sedan 40cm / SUV 55cm / truck 70cm).
4. **Forecast water depth in the next 60min/120min**: depth at T+1h and T+2h forecast timestep per segment.
5. **Pre-closure time per segment per vehicle type**: Scans T+1h forecast depth at each timestep → flags the first timestep where T+1h forecast depth ≥ hard block threshold → writes `pre_closure_time` and `minutes_until_hard_block` per segment per vehicle type to PostGIS — this is the trigger for proactive routing closure and government dispatch alerts.

Writes all metrics to PostGIS · must complete before workers begin.

↓ metrics written to PostGIS · signals Redis

**Redis message queue**
Receives metric-extraction-complete signal → fans out to Tier 1 workers in parallel → on Tier 1 completion, signals Tier 2 workers → segment extractor completion is the gate for Tier 2.

#### Tier 1: Parallel workers

| Worker | Responsibility |
|---|---|
| **Tile generator** | Reads current-timestep GeoTIFF → applies depth colour ramp → generates XYZ PNG tiles via gdal2tiles → pushes to CDN. |
| **Segment extractor** | Samples current depth (T0) at all road network nodes → calculates per-segment average depth → writes to PostGIS: độ sâu hiện tại, độ sâu trung bình tuyến đường, pre-closure flag per vehicle type (boolean, set when pre_closure_time has been reached) → re-weights Valhalla routing graph → segment cost = infinity if pre-closure flag is set, regardless of current depth. **Gate for Tier 2**: alert engine + district aggregator cannot start until this completes. |
| **Institution histogram builder** | 1. Samples depth at each registered institution lat/lng from GeoTIFF series. 2. Produces hourly bars for T+0 → T+6h (6 bars per-cycle data). 3. Overwrites first 6 bars of existing 24 bars in TimescaleDB (background sim provides bars 7–24). 4. Also aggregates per-district depth statistics. 5. Does NOT compute route histograms — those are query-time (see route controller). 6. Reads GeoTIFFs directly / no PostGIS dependency. |
| **User alert engine** | 1. Samples depth at user locations directly from T+0 and forecast GeoTIFFs — Danger 🔴 = current or T+1h depth > vehicle threshold at user location; Warning 🟠 = T+2h depth > vehicle threshold at user location. 2. Dispatches push notifications via FCM/APNs — highest priority: gets alerts to users as fast as possible. 3. Reads GeoTIFFs + metric extractor output → no segment extractor dependency. |

↓ waits for segment extractor to complete writing to PostGIS + Valhalla

#### Tier 2: dependent workers (blocked until segment extractor finishes)

| Worker | Responsibility |
|---|---|
| **Segment alert engine** | 1. Reads per-segment current_depth + pre-closure flags from PostGIS (written by segment extractor). 2. Generates segment-level alerts: Pre-closure Warning — segment forecast impassable within 1h per vehicle type / khuyến cáo lưu thông per segment per vehicle type / writes dashboard pre-closure feed records for city council dashboard. **Depends on**: segment extractor (current_depth, pre-closure boolean flags). |
| **District aggregator** | 1. Spatial join: road segments + district polygons. 2. Reads per-segment current_depth + flags from PostGIS (written by segment extractor): counts impassable segments per district per vehicle type, counts segments in pre-closure state per district, counts inaccessible institutions per district per type. Writes district summary table to PostGIS — source for `/dashboard/districts/summary`. **Depends on**: segment extractor (current_depth, pre-closure boolean flags). |

↓ all tiers complete · cycle done

**Cycle completion**
1. Checks all Tier 1 + Tier 2 workers completed or timed out.
2. Updates staleness timestamp (relative to current pipeline mode, not fixed).
3. Publishes cycle duration + worker timing to Prometheus.
4. Logs cycle completion.

↓ writes to: **PostGIS** (segment depths, metrics, passability classifications), **TimescaleDB** (forecast histograms, depth history), **Tile CDN** (XYZ PNG flood tiles), **Routing engine** (Valhalla re-weighted graph), **FCM/APNs** (alert payloads)

### Background_cycle pipeline

**Background depth calculator**
1. Same `threedidepth.calculate_waterdepth()` process as per-cycle → 25 files.
2. Parallelized → outputs `depth_YYYYMMDD_HHMMSS.tif` series (hourly).

↓ outputs 25 × depth GeoTIFFs (hourly over 24h)

**background_cycle histogram writer**
1. Samples depth at each registered institution lat/lng from 24h GeoTIFF series.
2. Writes full 24-bar hourly histogram to TimescaleDB.
3. Constant_cycle histogram builder later overwrites first 6 bars with fresher data.
4. Generates Watch 🟡 alerts (forecast depth exceeds vehicle threshold within 24h).
5. Writes to alert API.

↓ writes to: **TimescaleDB** (full 24h institution histograms, watch alerts, background forecast data for dashboard scrub), **FCM/APNs** (watch alert payloads, 24h horizon)

### Histogram specifications — how simulation data feeds each histogram type

**Institution histogram (like Google "popular times")**
- **Visual**: 24 hourly bars showing predicted water depth at a registered institution / day selector / "live" bar highlighted / vehicle threshold line / nước rút estimate.
- **Resolution**: 1 bar = 1 hour · 24h horizon.
- **Data source**: pre-computed by institution histogram builder (Tier 1) + background histogram writer — bars 1–6: per-cycle 6h sim (overwritten with fresh data); bars 7–24: background 24h sim (refreshed every 3–6 hours).
- **Storage**: TimescaleDB → served by `GET /places/flood`.
- **Audience**: public institution place detail sheet.

**Route histogram (like Google "traffic" on route)**
- **Visual**: 4 time blocks × 2 columns = 8 bars (30-min each) → 4h lookahead window from departure time → "now" column highlighted → vehicle threshold line → "best departure" label.
- **Resolution**: 1 bar = 30 min · 4h visible window (full 6h computed internally for "best departure").
- **Data source**: computed at query time by route controller — NOT pre-computed by any pipeline worker. Route controller reads per-segment forecast depths from PostGIS (metric extractor output), runs Valhalla for each 30-min departure window, returns max depth along optimal route at each window. Each 30-min bar = max of two consecutive 15-min simulation timesteps.
- **Storage**: none (ephemeral, computed per request) → served by `GET /flood/route/forecast`.
- **Audience**: route planner bottom sheet.

---

## 5. REST API (`[Citizen-facing endpoints]`)

| Endpoint | Method | Description |
|---|---|---|
| **Flood tile controller** | `GET /flood/tiles/{z}/{x}/{y}` | Validates zoom level → redirects to CDN → appends staleness header if pipeline cycle exceeded SLA. |
| **Flood point controller** | `GET /flood/points` | Queries PostGIS for depth + forecast metadata at lat/lng with radius filter → returns pre-closure flag and T+1h forecast depth per point. |
| **Community report controller** | `POST /community/report` | Accepts photo + depth estimate + passability vote + vehicle type → writes to PostGIS community table → data isolated from routing and official depth values → requires user auth token. |
| **User location controller** | `POST /user/location` | Accepts lat/lng + location sharing consent mode (always / app-open) → writes to user location store → used by pipeline alert engine to target out-of-app push notifications → requires user auth token. |
| **Alert controller** | `GET /flood/alerts` | Returns active alerts for area or user location · aggregates from three sources: 1. Danger 🔴 + Warning 🟠: from user alert engine (pipeline Tier 1) — sampled directly at user location → refreshed every pipeline cycle. 2. Pre-closure Warning 🟠: from segment alert engine (pipeline Tier 2) — per-segment "forecast impassable within 1h" — reads PostGIS. 3. Watch 🟡: from background 24h simulation — "forecast depth exceeds threshold within 24h" — refreshed every 3h. 4. Primary source for in-app alert poller → each alert includes `source_timestamp` for freshness. |
| **Forecast controller** | `GET /flood/forecast` | Returns depth time-series at lat/lng up to 24h ahead → stitches two data sources: 1. T+0 → T+6h: from per-cycle 6h simulation at 15-min resolution (PostGIS, refreshed every constant_cycle). 2. T+6h → T+24h: from background 24h simulation at 60-min resolution (TimescaleDB, refreshed every 3h). 3. Includes pre-closure threshold crossing timestamps / response indicates data freshness per segment (constant_cycle timestamp vs background_cycle timestamp). |
| **Route controller** | `GET /flood/route` | Accepts vehicle type + optional departure_time. Calls Valhalla with flood-weighted graph — pre-closure segments treated as cost = infinity — returns per-step depth badges, passability state (passable / pre-closed / impassable), earliest safe departure window. Computes độ sâu trung bình route A→B at query time. Reads per-segment forecast depths from PostGIS (written by metric extractor). If departure_time is in future, uses forecast depth at that timestep for routing. |
| **Pipeline status controller** | `GET /pipeline/status` | Returns latest completion status for both simulation types: 1. constant_cycle (6h sim, 15-min timestep, runs every 30 min) — last_completed / next_expected ISO timestamps, duration_seconds. 2. background_cycle (24h sim, 60-min timestep, runs every 3h) — same fields. Used by mobile app for data freshness display / used by dashboard for staleness indicator / read-only / no auth required. |
| **Route forecast controller** | `GET /flood/route/forecast` | Returns route flood depth histogram (like Google "popular times") → computed at query time, not pre-computed: accepts vehicle type + origin + destination, runs Valhalla for each 30-min departure window across 6h constant_cycle data, each 30-min bar = max depth along optimal route (max of two consecutive 15-min timesteps), returns 12 bars total (6h + 30 min) — client displays first 8 as 4 blocks × 2 columns. Includes "best_departure" field: first 30-min window where max route depth < vehicle threshold. If no safe window in 6h → best_departure = null. Response time target: < 2 seconds (same as /flood/route). |
| **Places flood controller** | `GET /places/flood` | Returns institution flood depth histogram (like Google "popular times") for registered institution — 24 hourly bars from TimescaleDB = full day forecast — bars 1–6: per-cycle 6h sim (overwritten every 30 min with fresher data); bars 7–24: from background 24h sim (refreshed every 3h). Full 24-bar series returned in one response. Returns: current depth at institution + forecast accessibility state (accessible / pre-closing within 1h / inaccessible) + recommendation defaults to 20cm (xe máy) + best_access_window: first hour where depth < vehicle threshold. Threshold line rendered client-side → vehicle switch does NOT trigger new API call. |

### `[City council dashboard endpoints]`

| Endpoint | Method | Description |
|---|---|---|
| **Pre-closure feed controller** | `GET /dashboard/preclosure` | Returns all road segments currently in pre-closure state → per segment: name, current depth, T+1h forecast depth, hard block threshold, vehicle types affected, estimated minutes until hard block → ordered by operational severity (arterial roads, proximity to hospitals and schools first) · updates every pipeline cycle → includes staleness timestamp. |
| **Institution access controller** | `GET /dashboard/institutions/access` | Returns forecast accessibility for all registered institutions → per institution: current status, T+1h and T+2h accessibility forecast → reads current depth from PostGIS → reads forecast histogram from TimescaleDB (same dual-source 24-bar series as /places/flood) → reads pre_closure_time from PostGIS → filterable by type: hospital / school / evacuation point / government office → hospitals never shown as "do not approach" = always shows current status. |
| **Dispatch log controller** | `POST /dashboard/dispatch` | Accepts segment ID + team identifier + action type (traffic coordination / emergency access / evacuation corridor) → writes deployment record to PostGIS → allows council operators to mark a segment as actioned → prevents duplicate dispatch to the same location → requires council auth token. `GET /dashboard/dispatch/log` → returns chronological deployment log, exportable as CSV. |
| **District summary controller** | `GET /dashboard/districts/summary` | Reads precomputed district summary table from PostGIS = written each cycle by district aggregator (pipeline Tier 2) → returns per district: count of impassable road segments per vehicle type, count of road segments in pre-closure state per vehicle type, count of inaccessible institutions by type, count of institutions in pre-closing state within 1h, dominant flood severity level for the district. Read-only / no query-time computation · response is fast → staleness timestamp included. |

↓ reads from / writes to: **PostGIS** (segment depths (constant_cycle), pre-closure flags, district summary, alerts, community reports, institutions, dispatch log), **Tile CDN** (PNG tile redirect target), **TimescaleDB** (institution histograms (24h hourly), background_cycle forecast series, depth history), **Flood routing engine** (Valhalla — route + flood cost per departure window), **Pipeline state** (last-completed timestamps for constant_cycle + background, from Airflow), **User location store** (GPS per user, consent mode).

---

## 6. Mobile / Web App

### Map view
Flood heatmap base overlay: layer toggles (depth, rainfall, air quality, satellite, community pins) · search bar / zoom / pan · vehicle mode selector · renders XYZ tiles from CDN via API.

### Route planner
Vehicle type selector (xe máy/sedan/SUV/truck) · route card with total time, distance, average depth · per-step depth badges with three states: passable / pre-closed / impassable · depth forecast histogram with vehicle threshold line · departure time picker: đi ngay / đợi đến lúc smart suggestion.

**Route flood depth histogram** (like Google "traffic" on route)
- **Layout**: 4 time blocks × 2 columns = 8 bars (30-min each) / 4h visible window starting from current time or user-selected departure time.
- **Visual**: "now" column highlighted in pink / remaining bars colour-coded by depth severity (green <10cm, yellow 10–20cm, orange 20–30cm, red >30cm) / vehicle threshold dashed line overlaid (moves instantly on vehicle type switch — no new API call).
- **Data source**: computed at query time by route controller via `GET /flood/route/forecast`. Each 30-min bar = max depth along optimal route, derived from two consecutive 15-min simulation timesteps.
- **Best departure**: "đi ngay / đợi đến lúc" label — route controller scans full 6h per-cycle data for first 30-min window where max route depth < vehicle threshold. If safe window is beyond visible 4h, label shows time only (e.g. "đợi đến 10:00 PM"). If entire 6h above threshold → "không có khung giờ an toàn trong 6h tới".

**Histogram data pipeline**: User requests route → route controller reads per-segment forecast depths from PostGIS (written by metric extractor per cycle) → runs Valhalla with flood costing for each 30-min departure window → returns max depth along optimal route at each window → client renders 4-block chart → vehicle threshold line rendered client-side from selected vehicle type.

**Live navigation monitor**: Re-queries route controller every pipeline cycle while navigation active (after each constant_cycle completion) · if segment ahead has crossed vehicle threshold or entered pre-closure since navigation started → surfaces flood-ahead warning with depth and reroute option · if no safe route exists → warns user to stop and wait · queries `GET /pipeline/mode` to determine re-query interval.

### Flood status bottom sheet
Current depth badge at user location with colour-coded status: alert horizon summary (now / 1h / 2h / 24h) · area depth forecast histogram · estimated recession time · estimated return-to-normal circulation time.

### Place detail sheet — shown when user taps a registered institution
1. Current depth at location.
2. 3h forecast depth histogram.
3. Accessible / difficult / do not approach recommendation.
4. Best access window today.
5. Emergency hospital override routing.

**Institution flood depth histogram** (like Google "popular times")
- **Layout**: 24 hourly bars showing predicted water depth at institution location / day selector (today default) / "live" bar highlighted in pink / time axis labels every 3 hours (6a, 9a, 12p, 3p, 6p, 9p, 12a).
- **Visual**: bars colour-coded by depth severity (same ramp as route histogram) / vehicle threshold dashed line overlaid / estimated nước rút time shown below chart / "best access window today" label: earliest hour where depth is forecast below vehicle threshold.
- **Data source**: pre-computed by pipeline workers, stored in TimescaleDB, served by `GET /places/flood` — bars 1–6 (T+0 → T+6h): from per-cycle 6h simulation → overwritten every 30 min with fresh data; bars 7–24 (T+7h → T+24h): from background 24h simulation → refreshed every 3–6 hours. Client receives full 24-bar series in one response.

**Threshold logic**: Default threshold is 20 cm (xe máy) = the primary vehicle type in Vietnam. Recommendation recalculated client-side instantly when user switches vehicle type — no new API call needed as full histogram data is already loaded. Threshold line on histogram updates in place.

### Alert manager

**Mode 1: out-of-app push receiver — FCM/APNs listener**
1. Receives push from user alert engine (pipeline Tier 1) — Danger and Warning alerts sampled directly from GeoTIFFs at user location — two sub-cases: **Always share location**: pipeline targets current location every cycle; **Share when app open**: last known location used, accuracy degrades over time.
2. Renders Watch / Warning / Danger notification in system tray when app is closed.
3. Receives Watch alerts from background_cycle 24h simulation (forecast depth exceeds threshold within 24h).

**Mode 2: in-app poller (primary reliable channel) — Alert endpoint poller**
1. Polls `/flood/alerts` while app is open: no FCM/APNs dependency — renders Watch (yellow subtle banner) / Warning (orange prominent banner) / Danger (full-screen red banner) over whatever screen is active — not subject to third-party delivery risk — poll interval: re-polls after each constant_cycle completion.

### Community reporter
1. Photo upload at current GPS location.
2. Depth estimate input · passability vote per vehicle type (can pass / difficult / cannot pass).
3. Submits to REST API community endpoint.
4. Displays community pins as toggleable layer on map.
5. Pins expire after 2h unless confirmed by subsequent reports at same location.
6. Community data is informational only → does not affect routing or official depth values.

↓ reads from / writes to: **REST API** (all flood data, routing, alerts, community report write), **Google Maps** (place search & geocoding), **FCM/APNs** (incoming push, mode 1 only).

---

## 7. City Council Dashboard

### `[Situational awareness layer, always visible]`

**Operational flood map** — Full-city flood depth heatmap using same XYZ PNG tiles as citizen app → 4 segment states rendered distinctly on map: Red = impassable now · Amber = pre-closure within 1h · Yellow = passable, watch · Blue = draining.

**Staleness indicator** — Prominent banner if constant_cycle did not complete within 30-min SLA · reads `last_completed` from `GET /pipeline/status` · shows time since last valid data · operators must acknowledge before making dispatch decisions on stale data.

**City-wide depth summary** — Reads precomputed district summary from `GET /dashboard/districts/summary`: count of impassable road segments per vehicle type, count of segments in pre-closure state per vehicle type, count of inaccessible institutions by type (hospital / school / evacuation / government), count of institutions pre-closing within 1h, dominant severity level for the district. Auto-refreshes every constant_cycle completion → all values precomputed by district aggregator (Tier 2) → no query-time spatial joins.

### `[Pre-closure alert feed, primary dispatch trigger]`

**Pre-closure segment feed** — List of segments in pre-closure state from latest constant_cycle → polls `GET /dashboard/preclosure` every cycle completion → per segment: segment name and district, current depth and T+1h forecast depth, hard block threshold for each vehicle type, estimated minutes until hard block → ordered by operational severity → arterial roads and roads near critical institutions surfaced first → new entries since last cycle highlighted.

**Institution access panel** — Polls `GET /dashboard/institutions/access` every cycle · filterable by institution type · per institution entry shows: current accessibility (accessible / pre-closing within 1h / inaccessible), T+1h and T+2h forecast accessibility, recommended public announcement text (auto-generated), hospitals never shown as "do not approach" — always shows current status regardless of depth.

### `[Dispatch workflow layer, operational response tracking]`

**Dispatch action panel** — Operator selects a segment or institution from the alert feed · assigns an action type: traffic coordination deployment, emergency vehicle access route activation, evacuation corridor opening, heavy vehicle diversion. Assigns a team identifier → adds optional notes → submits via `POST /dashboard/dispatch` → prevents duplicate dispatch: if a segment already has an active team assigned, panel shows existing assignment and prompts confirmation before overwriting.

**Deployment log** — Chronological log of all dispatch actions taken this flood event: per entry — segment or institution name, action type, team identifier, dispatch timestamp, operator name, current segment status (still pre-closure / now impassable / resolved) — allows supervisors to audit response timeline — exportable as CSV for post-event debrief — log persists after flood event ends for calibration and response review.

**Announcement composer** — Generates draft public announcements from institution access panel data: pre-fills with affected institution name, current status, best access route, and estimated resolution time — operator reviews and edits before publishing — does not publish directly → output is draft text for copy into official communication channels (Zalo OA, city website, broadcast) — Vietnamese language output only.

### `[Forecast and planning layer]`

**24h flood forecast panel** — Hourly depth forecast histogram per district — data source: background_cycle 24h simulation (refreshed every 3h) with first 6 bars overwritten by constant_cycle data — timestep selector: operator scrubs forward in 1h increments to see projected flood extent — map overlay updates to show projected segment states at selected forecast time — useful for pre-positioning emergency teams before flood peak arrives.

**Flood peak and recession timeline** — City-wide summary of: Thời gian đến đỉnh ngập per district, Dự kiến nước bắt đầu rút, Dự kiến lúc nào lưu thông lại được — displayed as a timeline bar chart per district → allows operators to plan resource redeployment as flood recedes across the city in sequence.

**Pipeline health monitor** — Reads `GET /pipeline/status` · shows both pipelines: constant_cycle (6h sim, 15-min timestep): runs continuously — last completed timestamp vs runtime vs 30-min SLA, current cycle stage (ingestion → 3Di API → depth calc → metric extractor → Tier 1 → Tier 2); background_cycle (24h sim, 60-min timestep): runs every 3h — last completed timestamp, next expected. Component failures this session. Grafana / Prometheus feed. Visible to technical operators → enables rapid identification of data quality issues before they affect dispatch decisions.

↓ reads from / writes to: **PostGIS** (segment states, pre-closure flags, district summary, dispatch log), **TimescaleDB** (district forecast histograms, peak & recession timelines), **Tile CDN** (XYZ PNG flood tiles for operational map), **REST API** (`/dashboard/preclosure`, `/dashboard/institutions/access`, `/dashboard/districts/summary`, `/dashboard/dispatch`, `/flood/forecast`, `/pipeline/status`), **Grafana/Prometheus** (pipeline health metrics).

---

## 8. Flood Routing Engine — `[Valhalla routing engine]`

Marked as a **BLACK BOX** on the whiteboard — no internal detail specified. Referenced elsewhere as: Valhalla flood-weighted graph routing, re-weighted by Postprocessing (segment extractor) each cycle, queried by REST API (route controller, route forecast controller) at request time via HTTP API. Pre-closure segments are treated as cost = infinity.

---

## 9. Cross-Cutting Design Rationale (sticky notes — Mai Anh)

### 1. Simulation pipeline
- The hydrodynamic simulation cannot start until boundary conditions are set, the depth calculator cannot run until the NetCDF exists, and the flood metric extractor cannot run until the full GeoTIFF series is complete, because peak time and recession onset can only be identified by scanning across all timesteps together. No worker can be safely parallelized before that point.
- The simulation duration is 24h, timestep is 30 minute → the average duration of severe flood impact in Vietnam typically lasts 3 days ([global-flood-database.cloudtostreet.ai](https://global-flood-database.cloudtostreet.ai/)) so 24 hour is critical so that user can plan for the next day; the 30 minute timestep is TBD, we would want to benchmark how long does it take for flood to reach general threshold (20cm) — we want to have timestep smaller than this window to reflect the water depth correctly.
- Similarly, the desired duration of the entire workflow also depends on how long does it take for flood to reach general threshold (20cm); for now, we are assuming it is 30 minute, so the entire flow has to finish in <= 30 minutes:
  - simulation allocated 15 minutes for 3000 km² of Hanoi
  - post processing + visualization allocated for 15 minutes (might need to add more workers if 4 is not fast enough)
- The depth calculator is separated from the tile generator because it serves all four downstream workers, not just the tile generator.
- The flood metric extractor exists because it is necessary for user to make the decision themselves without relying on the routing engine, give them their own agency to make the decision.
  - Pre-closure time per segment per vehicle type: the depth at which a segment is proactively closed to routing, defined as the forecast depth 1 hour ahead reaching the hard block threshold. It is distinct from the hard block threshold, which remains the physical safety limit. The pre-closure threshold is a routing policy decision sitting on top of the physical limit → safety buffer so that we do not lead people into road that potentially will be flooded should the water rise faster than expected.
  - Eg: for a motorbike → close the segment to routing when the T+1h forecast depth is ≥ 20cm, even if current depth is only 12cm. The hard block at 20cm current depth remains as a final backstop.
  - Pre-closure time also useful for the city council to dispatch emergency team to navigate the traffic or evacuate.
- The passability restoration time is computed per vehicle type, because their height is different (the height = distance between road surface and exhaust pipe).
- Storing all four values in PostGIS means the route controller and alert engine can serve any vehicle type at query time without recomputation.
- The four parallel workers are deliberately isolated from each other with no inter-worker dependencies: less failure.
- The static data loader is on a completely separate cadence from the live ingestion components. DTM, land cover, and drainage network change rarely — treating them as cycle-frequency inputs would add unnecessary preprocessing load every 15 minutes. Separating them makes the boundary explicit: only rainfall forecast and gauge readings trigger the full pipeline. Everything else is configuration.

### 2. REST API
- Keeping the API stateless means it can be scaled horizontally behind a load balancer without any session or state coordination between instances. If the pipeline is delayed, the API continues serving the last valid data from PostGIS and TimescaleDB with a staleness timestamp.
- Exception is the route controller: call to Valhalla and assembles the per-step response: query-time assembly of data that cannot be precomputed because it depends on a specific origin-destination pair requested by a user. The **độ sâu trung bình của route A→B** is calculated here rather than in the pipeline = path-specific and cannot be precomputed for all possible routes.
- The alert controller is separated from the alert engine in the pipeline:
  - The pipeline alert engine writes alert records and dispatches push notifications.
  - The alert controller in the API serves those pre-written records to the mobile app's in-app poller.
  - Keeping them separate means in-app alert display does not depend on FCM/APNs delivery working correctly.
- The places flood controller defaults to the 20cm motorbike threshold when serving institution histogram data, as users use motorbike mostly.
- Recommendation recalculation when a user switches vehicle type happens client-side in the mobile app, not via a new API call: the full histogram is already loaded, and recalculating a threshold comparison in JavaScript is instantaneous. Making a new API call for each vehicle type switch would add unnecessary latency to what should feel like an immediate UI response.

### 3. Mobile app
- The in-app poller is the primary reliable channel: no third-party dependency and works as long as the app is open and the API is reachable.
- FCM/APNs is the out-of-app delivery mechanism and is subject to platform-level delivery guarantees that FloodNav does not control.
- Treating them as two distinct modes makes the reliability boundary explicit and ensures the architecture does not accidentally rely on push delivery for safety-critical situations where the app is open.
- The location-sharing sub-cases in the push receiver → affect how accurately the pipeline can target alerts.
  - A user who has granted always-on location permission gets alerts targeted to their actual current location every cycle.

---

*Note: OCR performed by cropping the native 25000×6162px whiteboard image into per-frame sections and transcribing via vision model. Minor transcription artifacts (e.g. exact Vietnamese diacritics, arrow directions) may exist — cross-check against the original image/Fibery whiteboard for anything safety-critical.*
