import Store from '@/stores/Store'
import Dispatcher, { Action } from '@/stores/Dispatcher'
import { getApi } from '@/api/Api'
import { getQueryStore } from '@/stores/Stores'
import * as config from 'config'

export interface FloodTimestep {
    valid_time: string
    run: string
}

export type MapMode = 'map' | 'flood'

/**
 * INVARIANTS held by the reducer and relied on by every reader:
 *  I1. selectedIndex === -1 when timesteps is empty, otherwise in [0, timesteps.length - 1].
 *      TimeSlider's <input max=...> used to be the only thing holding this; now the reducer does.
 *  I2. every timestep carries the same `run` (the backend pins list_timesteps to one run), so
 *      "latest timestep" and "N steps behind latest" are well defined.
 *  I3. mapMode is concrete state, never recomputed from the clock at render time.
 *  I4. userChoseMapMode, once true, is never cleared by arriving data.
 */
export interface FloodStoreState {
    timesteps: FloodTimestep[]
    selectedIndex: number
    vehicleType: string
    /** Dev-only override for the raster tile layer, toggled from TimeSlider (local testing tool).
     *  Effective layer visibility is `mapMode === 'flood' && tilesVisible` — MapModeToggle is the
     *  product-facing control, this is a secondary local-dev escape hatch. */
    tilesVisible: boolean
    mapMode: MapMode
    /** True once the user has operated MapModeToggle. Suppresses the recency-derived default
     *  on every later FloodTimestepsReceived. This is user intent, not a cached derivation. */
    userChoseMapMode: boolean
    /** Every distinct ingestion run the backend has data for, newest first (GET /flood/runs). */
    availableRuns: string[]
    /** null means "latest" — the backend's own default when no `run` query param is sent.
     *  Explicit once the user picks a run from TimeSlider's dev-only run picker. */
    selectedRun: string | null
}

/** Data is fresh enough to default into Flood mode when the newest timestep's valid_time is
 *  within this window of now. */
export const FRESH_DATA_WINDOW_MS = 45 * 60 * 1000

/** `receivedAt` is the clock read, taken once at the fetch boundary, so the reducer stays pure
 *  and every time-dependent decision in this store is reproducible in a test. */
export class FloodTimestepsReceived implements Action {
    constructor(
        readonly timesteps: FloodTimestep[],
        readonly receivedAt: number,
    ) {}
}

/** Explicit user toggle of the map/flood switch. Sets userChoseMapMode. */
export class SetMapMode implements Action {
    constructor(readonly mode: MapMode) {}
}

export class SelectFloodTimestep implements Action {
    constructor(readonly index: number) {}
}

export class SelectFloodVehicle implements Action {
    constructor(readonly vehicleType: string) {}
}

export class ToggleFloodTiles implements Action {
    constructor(readonly visible: boolean) {}
}

export class FloodRunsReceived implements Action {
    constructor(readonly runs: string[]) {}
}

/** `null` re-selects "latest". Explicit user action from TimeSlider's run picker. */
export class SelectFloodRun implements Action {
    constructor(readonly run: string | null) {}
}

// '/flood/*', '/tiles/*' and '/route' live behind the same backend — see
// backend/server.py, backend/flood_areas.py and backend/tiles.py in
// floodmap-backend.
export const BACKEND_BASE: string = (config as any).floodBackend || (config as any).routingApi || '/api/gh/'

/** XYZ template for the depth-raster tile layer. run and valid_time go in
 * raw: server.py routes on urlparse(path).path and never unquotes, so a
 * literal colon in the timestamp reaches it verbatim where '%3A' would not. */
export function floodTileUrl(step: FloodTimestep): string {
    return `${BACKEND_BASE}tiles/${step.run}/${step.valid_time}/{z}/{x}/{y}.png`
}

/**
 * Index of the timestep whose valid_time is closest to `now`, in either direction.
 *
 * Returns -1 for an empty list. Entries whose valid_time does not parse are skipped; if every
 * entry is unparseable the result is -1.
 *
 * Tie-break: an exact tie resolves to the LATER valid_time, so the product leans towards the
 * step you are heading into rather than the one you just left. The `<=` scan only yields the
 * later entry because the backend returns the list ascending by forecast_time (invariant I2);
 * that precondition is what makes the last minimum also the latest one.
 */
export function findNearestTimestepIndex(timesteps: readonly FloodTimestep[], now: number): number {
    let best = -1
    let bestDelta = Infinity
    for (let i = 0; i < timesteps.length; i++) {
        const t = Date.parse(timesteps[i].valid_time)
        if (Number.isNaN(t)) continue
        const delta = Math.abs(t - now)
        if (delta <= bestDelta) {
            bestDelta = delta
            best = i
        }
    }
    return best
}

/** Clamps `index` into the range invariant I1 permits for `timesteps`. */
export function clampTimestepIndex(index: number, timesteps: readonly FloodTimestep[]): number {
    if (timesteps.length === 0) return -1
    if (!Number.isInteger(index)) return -1
    return Math.min(Math.max(index, 0), timesteps.length - 1)
}

/**
 * Where selectedIndex should land after a new timestep list arrives.
 *
 * If the currently selected (valid_time, run) pair still exists in the new list, follow it to its
 * new position: a refetch must not move the map out from under someone mid-inspection. Otherwise
 * re-anchor to nearest-to-now. Identity, not ordinal position, is what the user selected, so this
 * needs no separate "has the user picked a step" flag.
 */
export function reanchorTimestepIndex(prev: FloodStoreState, next: readonly FloodTimestep[], now: number): number {
    const current = prev.timesteps[prev.selectedIndex]
    if (current) {
        const i = next.findIndex(s => s.valid_time === current.valid_time && s.run === current.run)
        if (i >= 0) return i
    }
    return findNearestTimestepIndex(next, now)
}

/**
 * Data-recency default: Flood mode when the newest timestep sits within FRESH_DATA_WINDOW_MS of
 * now. The measure is |t - now|, not now - t, because timesteps are forecasts and the newest one
 * is normally in the future; signed age would default to Map mode almost always.
 */
export function defaultMapMode(timesteps: readonly FloodTimestep[], now: number): MapMode {
    const last = timesteps[timesteps.length - 1]
    if (!last) return 'map'
    const t = Date.parse(last.valid_time)
    if (Number.isNaN(t)) return 'map'
    return Math.abs(t - now) <= FRESH_DATA_WINDOW_MS ? 'flood' : 'map'
}

class FloodStore extends Store<FloodStoreState> {
    constructor() {
        super({
            timesteps: [],
            selectedIndex: -1,
            vehicleType: 'motorbike',
            tilesVisible: true,
            mapMode: 'map',
            userChoseMapMode: false,
            availableRuns: [],
            selectedRun: null,
        })
    }

    reduce(state: FloodStoreState, action: Action): FloodStoreState {
        if (action instanceof FloodTimestepsReceived) {
            return {
                ...state,
                timesteps: action.timesteps,
                selectedIndex: reanchorTimestepIndex(state, action.timesteps, action.receivedAt),
                mapMode: state.userChoseMapMode ? state.mapMode : defaultMapMode(action.timesteps, action.receivedAt),
            }
        } else if (action instanceof SelectFloodTimestep) {
            const next = clampTimestepIndex(action.index, state.timesteps)
            // Returning the identical object makes Store.receive() skip the notify, so a no-op
            // select costs no re-render and no areas refetch.
            return next === state.selectedIndex ? state : { ...state, selectedIndex: next }
        } else if (action instanceof SetMapMode) {
            if (action.mode === state.mapMode && state.userChoseMapMode) return state
            return { ...state, mapMode: action.mode, userChoseMapMode: true }
        } else if (action instanceof SelectFloodVehicle) {
            return { ...state, vehicleType: action.vehicleType }
        } else if (action instanceof ToggleFloodTiles) {
            return { ...state, tilesVisible: action.visible }
        } else if (action instanceof FloodRunsReceived) {
            return { ...state, availableRuns: action.runs }
        } else if (action instanceof SelectFloodRun) {
            if (action.run === state.selectedRun) return state
            // Old run's timesteps don't apply to the new run; clear them so the map doesn't
            // keep showing a stale selection until the refetch lands.
            return { ...state, selectedRun: action.run, timesteps: [], selectedIndex: -1 }
        }
        return state
    }
}

const floodStore = new FloodStore()
Dispatcher.register(floodStore)

export function getFloodStore() {
    return floodStore
}

/** Reads `state.selectedRun` at call time rather than taking it as a parameter, so every call
 *  site (mount, TimeSlider's run picker, a future refresh timer) stays in sync with the store
 *  without threading the value through each one. */
export async function loadFloodTimesteps() {
    const run = floodStore.state.selectedRun
    const url = new URL(`${BACKEND_BASE}flood/timesteps`, window.location.href)
    if (run) url.searchParams.set('run', run)
    const res = await fetch(url)
    if (!res.ok) return
    const data = await res.json()
    // Read the clock after the await: "nearest to now" should be nearest to the moment the user
    // sees the result, not to the moment the request left.
    Dispatcher.dispatch(new FloodTimestepsReceived(data.timesteps || [], Date.now()))
}

export async function loadFloodRuns() {
    const res = await fetch(`${BACKEND_BASE}flood/runs`)
    if (!res.ok) return
    const data = await res.json()
    Dispatcher.dispatch(new FloodRunsReceived(data.runs || []))
}

/** Re-sends the current route request unchanged; the fetch interceptor
 * below is what actually attaches the flood parameters, so this is the
 * only bit of app.tsx-side plumbing needed to make the map re-plan when
 * the slider moves. */
export function reissueCurrentRoute() {
    const last = getQueryStore().state.currentRequest.subRequests[0]?.args
    if (last) getApi().routeWithDispatch(last, false)
}

/**
 * The one place the flood timestep/vehicle reaches GraphHopper. Rather than
 * building a custom_model client-side (which would mean shipping every
 * flood polygon's vertices to the browser just to route with them — the
 * thing Workstream B's server-side derivation was built to avoid), this
 * tags the outgoing /route request with plain (valid_time, run,
 * vehicle_type) fields. floodmap-backend (backend/server.py:_handle_route)
 * strips them back off, derives custom_model from PostGIS itself, and
 * forwards the rest of the request to GraphHopper unchanged.
 */
function installRoutingInterceptor() {
    // Nothing to wrap where there is no fetch, e.g. a test environment importing this module for
    // its pure helpers.
    if (typeof window === 'undefined' || typeof window.fetch !== 'function') return
    const realFetch = window.fetch.bind(window)
    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
        try {
            const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
            const method = (init?.method ||
                (typeof input !== 'string' && !(input instanceof URL) ? input.method : 'GET')) as string
            if (method.toUpperCase() === 'POST' && url.includes('/route') && typeof init?.body === 'string') {
                const state = floodStore.state
                const step = state.timesteps[state.selectedIndex]
                if (step) {
                    const body = JSON.parse(init.body)
                    if (!body.custom_model) {
                        body.valid_time = step.valid_time
                        body.run = step.run
                        body.vehicle_type = state.vehicleType
                        init = { ...init, body: JSON.stringify(body) }
                    }
                }
            }
        } catch (e) {
            console.warn('flood routing interceptor skipped a request:', e)
        }
        return realFetch(input, init)
    }
}

installRoutingInterceptor()
