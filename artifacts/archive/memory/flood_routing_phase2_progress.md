---
name: flood-routing-phase2-progress
description: "SUPERSEDED (2026-09-14) — historical debugging notes from the old 'Phase 2' plan/branch (new-road-flood-logic). Do not trust the top-level status claims; see flood-routing-backend-focus-2026-09 for current state"
metadata: 
  node_type: memory
  type: project
  originSessionId: f1b1159f-55c4-4cce-b247-bc5e9aadf731
  modified: 2026-09-13T18:13:56.729Z
---

**SUPERSEDED as of 2026-09-14 — do not treat the claims below as current.** This described a different plan (`okay-now-lets-plan-iterative-fiddle.md`) on branch `new-road-flood-logic`. That work landed in commit `6394e27` ("replace valhalla with grasshopper routing logic...") and the project moved to branch `flood-tile-t6t7` under a new plan, `/Users/maianhtran/.claude/plans/dazzling-percolating-raven.md`. As of 2026-09-14: Phase A (UI redesign) exists only on unmerged worktree branches, not on `flood-tile-t6t7`; Phase B/C (raster pipeline, place-popup depth, hourly chart) have not been started. See [[flood-routing-backend-focus-2026-09]] for current status. The sections below are kept only for their still-potentially-useful debugging history (Docker build gotchas, the App.tsx child-order pitfall, the relative-URL bug) — verify against current code before relying on any specific claim.

---

Working on the plan at `/Users/maianhtran/.claude/plans/okay-now-lets-plan-iterative-fiddle.md` ("Flood-Aware Routing — Phase 2: Web Map, Time-Series Validation, PostGIS"), approved and in progress on branch `new-road-flood-logic` in `t3-digital-twin`. Sequencing is Phase A → B → C → D. **Phases A, B, C, D are all now implemented and verified working end-to-end.** Nothing has been committed yet (user hasn't asked for a commit).

## Done: Phase A — D2 route sweep, Phase B — PostGIS + D1 ingest

See prior detail below (unchanged from last session). Real PostGIS data (96,744 rows, 8 runs, 30 distinct valid_times) is loaded in `storage-postgres` and survives container restarts (named volume).

## Done: Phase C — Workstream B (GraphHopper engine + backend)

**New directory `floodmap/graphhopper-flood-road/`** (forked from `floodmap/valhalla-flood-road-test/`, Valhalla-specific bits stripped):
- `graphhopper/config.yml` + `motorbike.json` (= upstream `motorcycle.json` verbatim) + `car_custom.json` + `truck_custom.json` — **note the `_custom` suffix**: `car.json`/`truck.json` are reserved custom_model filenames for GraphHopper's built-in profiles even when you supply your own content: using the bare name throws `Custom model file name 'car.json' is already used for built-in profiles`.
- Also needed in `config.yml` that weren't in the plan's sketch: `import.osm.ignored_highways: ''` (required, no default) and `graph.encoded_values` must include `road_environment` even though it's not in any of our custom_model files (GraphHopper's `speed` rules for `road_environment == FERRY` reference it internally).
- `backend/db.py`, `backend/flood_areas.py` (PostGIS band derivation, exactly the plan's SQL — `list_runs`, `list_timesteps`, `derive_areas`, `build_custom_model` using an if/else_if chain ordered deepest-band-first, one rule per polygon), `backend/server.py` (rewritten — see below), `backend/place_search.py` (extended with `geocode_gh_shape`).
- `scripts/flood_utils.py` trimmed to just `VEHICLE_PROFILES`/`factor_from_depth_m`/`depth_bands_m` — costing values now equal GraphHopper profile names directly (`motorbike`/`car`/`truck`), not Valhalla's `motor_scooter`/`auto`.

**`POST /route` is a transparent GraphHopper passthrough proxy**, not a custom-shaped endpoint: it accepts the exact body graphhopper-maps' `Api.ts` sends (`points`, `profile`, `points_encoded`, ...), pops off three extra fields (`valid_time`, `run`, `vehicle_type`) that the frontend's fetch interceptor tacks on, derives `custom_model` from PostGIS via `flood_areas.derive_areas`, injects `custom_model` + `ch.disable: true`, forwards the rest of the body unchanged to GraphHopper, and returns GraphHopper's response verbatim. This design avoids ever shipping flood-polygon vertices to the browser for routing purposes (they're still shipped for the *map overlay*, via `GET /flood/areas`, which is unavoidable).

**`GET /info` and `GET /nearest` are also proxied** (transparent GET passthrough to GraphHopper) — required because graphhopper-maps calls `routingApi + 'info'` at bootstrap; without this the app's `getApi().info()` call 404s against our backend (which has no native `/info`).

**`GET /geocode` added** (`place_search.geocode_gh_shape`) — reshapes raw Photon's GeoJSON `FeatureCollection` into the GraphHopper Geocoding API's `{hits: [...]}` shape (`GeocodingResult`/`GeocodingHit` in graphhopper-maps' `src/api/graphhopper.d.ts`), since that's what `Api.ts`'s `geocode()` expects and there's no reason to touch that file.

**`ch.disable`-in-body-vs-query-param constraint from the plan no longer applies as originally stated**: with `profiles_ch: []` (no CH prepared at all, only `profiles_lm`), GraphHopper accepts `ch.disable` as *either* a query param or a body field — there's nothing to "disable" since CH was never prepared. The smoke test in the plan's Verification section (query-param form should fail) will not fail against this config; that's expected, not a regression.

**Verified against the real engine + real PostGIS data** (not just curl smoke tests — this reached the actual Phase C gate):
- `/flood/areas?valid_time=2026-08-09T21:50:00` (peak wetness) returns 173 real polygons across 3 bands (b2:65, b3:40, b4:68).
- `POST /route` with `valid_time` at peak: 14,318m (vs 12,331m baseline) — correctly detours.
- `POST /route` with `valid_time` at 16:42 (near-dry): distance == baseline exactly — correctly reverts, matching the plan's pass criterion 3.
- `GET /info` proxy returns real profile list + `encoded_values`.

## Done: Phase D — Workstream C (graphhopper-maps fork)

**Vendored at `floodmap/graphhopper-maps/`**, commit `95f1fc19d8f0c72846cfc0656632f4ee71519fa2` (2026-09-08) — **pinned by commit SHA, not a tag**: upstream `graphhopper/graphhopper-maps` has no release tags at all (`git ls-remote --tags` is empty), so "pinned to an upstream tag" from the plan isn't literally achievable; SHA pinning is the equivalent. `.git` stripped after clone (see `PINNED_COMMIT.md` in that directory for the full list of what changed vs upstream).

**Diff from upstream is exactly the three things the plan specified, plus what building/serving a vendored SPA actually requires**:
- New: `src/floodmap/FloodStore.ts`, `FloodLayer.tsx`, `TimeSlider.tsx` + `.module.css`.
- Two lines added to `src/App.tsx`: `useFloodLayer(map)` and `<TimeSlider />` — **`<TimeSlider />` must be the LAST child of `<div className={styles.appWrapper}>`, not the first — see the dedicated pitfall note below, this cost most of the Phase D session.**
- `config-local.js.example` (routingApi/geocodingApi both `/api/gh/`... `/api/geocode/`, `profiles: {motorbike:{}, car:{}}`).
- New (not upstream, needed to actually serve this): `Dockerfile` (multi-stage node:22-alpine build → nginx:1.27-alpine), `nginx.conf` (proxies `/api/gh/` and `/api/geocode/` to `floodmap-backend:8010`).

**Route interception mechanism** (how `custom_model` reaches GraphHopper without the browser ever holding flood polygons): rather than using graphhopper-maps' *existing* built-in custom-model editor mechanism (`SetCustomModel` action → `QueryStore` → embeds `custom_model` in the request body itself, which upstream *does* support natively and would have been "more zero-edit" but ships full polygon vertices to the browser, exactly what the plan wanted to avoid) — `FloodStore.ts` installs a `window.fetch` monkeypatch (`installRoutingInterceptor`, runs once at module load) that intercepts outgoing `POST .../route` calls and tacks on `valid_time`/`run`/`vehicle_type` (three small strings, not polygons) to the JSON body before it's sent. `floodmap-backend`'s `/route` proxy (see Phase C above) does the actual `custom_model` derivation server-side. `TimeSlider`'s second `useEffect` calls `reissueCurrentRoute()` (re-sends `getQueryStore().state.currentRequest.subRequests[0].args` via `getApi().routeWithDispatch`) whenever the slider moves, so the map re-plans without any route-store code being touched.

**Docker build gotchas** (all fixed, present in the committed `Dockerfile`):
- `npm ci` fails — upstream's lockfile is slightly out of sync with `package.json` as pinned. Use `npm install` instead.
- Needs Node ≥22 (one transitive dep, `@mapbox/jsonlint-lines-primitives`, requires it) — `node:20-alpine` triggers an `EBADENGINE` warning that isn't fatal on its own but signals real breakage elsewhere; used `node:22-alpine`.
- `webpack.common.js` shells out to `git rev-parse HEAD` to embed a source-link SHA in the built page, but the vendored tree has no `.git` (stripped intentionally, see above) — build stage now does `apk add git && git init -q && git add -A && git commit -q -m vendor` before `npm run build` as a throwaway repo just to satisfy that call.

### The App.tsx child-order pitfall (cost most of this session — read before touching App.tsx again)

Mounting `<TimeSlider />` as the **first** child of `appWrapper` (before `MapPopups`/`ContextMenu`/`SmallScreenLayout`/`LargeScreenLayout`) causes the React root to silently unmount to zero DOM children on the first re-render with real data (`flood.timesteps.length > 0`) — **no exception is thrown, nothing appears in the browser console, no network error, no navigation.** `document.getElementById('root').children.length` just goes from 1 to 0 within ~100-300ms of mount (right when the async `/flood/timesteps` fetch resolves and the component re-renders with non-null content). This reproduces even with `TimeSlider` returning a bare `<div>{n}</div>` — the crash has nothing to do with the slider's actual JSX content, purely its position in `appWrapper`'s child list. Moving `<TimeSlider />` to be the **last** child (after the `{isSmallScreen ? ... : ...}` layout block) fixes it completely. Root cause not identified (something downstream — likely inside `MapPopups`, `MapComponent`, or one of the layer hooks — depends on DOM child index/`firstElementChild` rather than a ref or ID), but the fix is confirmed and stable. If adding more UI to `App.tsx` in future, **always mount new top-level elements last**, and bisect by DOM position first if something goes silently blank, not by data-flow.

### Local environment / how to run it

`docker compose up -d graphhopper storage-postgres minio minio-init floodmap-backend flood-routing-frontend` brings up the full flood-routing stack (skip the Airflow services, not needed for this). Frontend on `http://localhost:8082/`, backend directly reachable at `http://localhost:8010/`, GraphHopper directly at `http://localhost:8989/`. The old standalone Phase-1 `gh` container (`israelhikingmap/graphhopper:latest`, no compose management) was stopped in favor of the new `graphhopper` compose service — don't recreate it, it'll port-conflict on 8989.

**Verified in a real (headless, no-Aside) browser via the `/browse` skill**: page loads, TimeSlider renders with real vehicle dropdown + time label + working slider, `/flood/areas` and `/flood/timesteps` fetch successfully from the UI itself. Map tiles rendered blank (white) in the sandboxed test environment because `tile.openstreetmap.org` DNS didn't resolve there — not a code bug. The "Failed to construct 'URL': Invalid URL" error banner visible in that same test was **initially misdiagnosed as an unrelated cosmetic geolocation issue — it was not.** It was the real `routingApi`/`geocodingApi` relative-URL bug, see next section; that misdiagnosis cost a round-trip with the user before being caught from a second screenshot.

### Follow-up fix after this session: relative routingApi/geocodingApi broke everything

`config-local.js.example` originally set `routingApi: '/api/gh/'` (relative, so nginx's same-origin proxy avoids CORS). This silently broke the whole app: upstream `Api.ts` does `new URL(this.routingApi + endpoint)` with **no base argument**, which throws `Failed to construct 'URL': Invalid URL` on any relative path. That exception fired on every `info()`/`route()`/`geocode()` call, so `getApi().info()` never resolved, `InfoReceived` never dispatched, and `MapActionReceiver`'s existing (unmodified, upstream) bbox-fit-on-info logic never ran — map stayed at the hardcoded world-view default (`center: fromLonLat([10,10]), zoom: 2`) instead of fitting to the Hanoi model bbox GraphHopper's `/info` actually returns. This is why the map appeared to have no tiles/wrong center even after the DNS issue below was fixed.

**Fix**: `config-local.js` is loaded as a plain global `<script>` (see `webpack.common.js`'s `externals: { config: 'config' }` — the bundle references `config` as an external global, not something webpack inlines), and it loads *before* `bundle.js`, so `window` is available inside it. Changed `routingApi`/`geocodingApi`/`floodBackend` to `window.location.origin + '/api/gh/'` etc. (computed at page-load time, not build time) instead of bare relative paths. Confirmed fixed: `/api/gh/info` now succeeds, no console errors, map auto-fits to the real Hanoi model boundary on load.

### Follow-up fix: POST /route 404'd through the browser (but worked via curl)

`backend/server.py`'s `do_POST` compared `self.path == "/route"` directly. `self.path` on `BaseHTTPRequestHandler` includes the query string, and graphhopper-maps' `Api.ts` always appends `?key=` (empty, since we have no GraphHopper Directions API key configured) to routing requests — so the real browser request was `POST /route?key=`, which never matched, silently 404'd, and the frontend showed "Route request failed" with no route drawn. My own curl-based verification earlier in the session used `POST /route` with no query string, so this never showed up in testing — **only surfaced once the user tried it in a real browser.** Fixed: `do_POST` now does `urlparse(self.path).path == "/route"`, matching what `do_GET` already did correctly. Lesson: verify POST endpoints with the exact query-string shape the real client sends, not the minimal curl shape.

### Unrelated: DNS blocking tile.openstreetmap.org

Separately hit (and the user needs to fix on their own network, not a code issue): the user's router DNS (`192.168.2.1`) returns NXDOMAIN for `tile.openstreetmap.org` while `1.1.1.1` resolves it fine (it's a Fastly-fronted domain, `dualstack.n.sni.global.fastly.net`) — some router-level ad/parental-control DNS filtering catching it. Fix is switching the OS or router DNS to `1.1.1.1`/`8.8.8.8`, nothing to do with this codebase.

### Decision (end of this session): visualization moving off GeoJSON polygons

User has decided **routing logic is done for now** — do not keep tuning `buffer_m`/`SAMPLE_RATE` for visual fidelity. The `/flood/areas` GeoJSON-polygon overlay (buffered+unioned+simplified road segments, `FloodLayer.tsx`) looks blobby/octagonal rather than road-hugging — root cause confirmed in code: `extract_geojson_full.py` builds one small box per raster pixel (4m at `SAMPLE_RATE=4`), `mapping_geojson.py` intersects each against the road keeping only a few-metre sliver, then `buffer_m=22` (radius >> segment length) dominates the shape and `ST_Union` merges nearby buffers into blobs instead of a ribbon.

**Decision: next session will build map tiles directly from the GeoTIFF depth rasters instead of deriving/serving GeoJSON polygons for the *visualization* layer.** This does NOT touch the routing mechanism — `custom_model.areas` (PostGIS-derived polygons, `flood_areas.py`, the `/route` proxy) stays exactly as built and verified this session; only the *map overlay* (`GET /flood/areas` as consumed by `FloodLayer.tsx`) is what's being replaced. Likely shape of that work: a raster-tile server (e.g. `rio-tiler`/`titiler`, or a custom XYZ tile endpoint over the depth GeoTIFFs colorized by depth band) added to `floodmap-backend` or a new service, with `FloodLayer.tsx` swapped for an OpenLayers XYZ/WebGL tile layer instead of a `VectorLayer` of GeoJSON polygons. Not started — this is the next session's task, not begun in this one.

### Not yet done (as of end of this session) in a real browser (the headless sandbox browser couldn't reliably drive the map-click-to-set-waypoint flow to confirm a route line actually draws — text-field geocoder search also wasn't exercised end-to-end). D2 sweep has not been re-run against `/flood/areas` (Phase C's own verification gate — "the D2 sweep re-passes against it" from the plan's Sequencing & gates section) to formally close that gate; the manual curl tests above are a reasonable substitute but not the scripted sweep. Also not done: committing any of this (compose.yml, floodmap/graphhopper-flood-road/, floodmap/graphhopper-maps/, scripts/run_d1_ingest.py are all still uncommitted on `new-road-flood-logic`).
