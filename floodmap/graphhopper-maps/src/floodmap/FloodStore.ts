import Store from '@/stores/Store'
import Dispatcher, { Action } from '@/stores/Dispatcher'
import { getApi } from '@/api/Api'
import { getQueryStore } from '@/stores/Stores'
import * as config from 'config'
import { FloodMode, parseFloodMode } from '@/floodmap/floodMode'

export interface FloodTimestep {
    valid_time: string
    run: string
}

export type MapMode = 'map' | 'flood'

/**
 * INVARIANTS held by the reducer and relied on by every reader:
 *  I1. selectedIndex === -1 when timesteps is empty, otherwise in [0, timesteps.length - 1].
 *      The reducer holds it, so a consumer never reads a stale or out-of-range index.
 *  I2. timesteps are ascending by valid_time with one entry per valid_time, each from the newest
 *      run that published it (backend GET /flood/timesteps). Entries may carry different `run`
 *      values, so a step's identity is its (valid_time, run) pair, never its position.
 *  I3. mapMode is concrete state, never recomputed from the clock at render time.
 *  I4. userChoseMapMode, once true, is never cleared by arriving data.
 */
export interface FloodStoreState {
    timesteps: FloodTimestep[]
    selectedIndex: number
    vehicleType: string
    mapMode: MapMode
    /** True once the user has operated MapModeToggle. Suppresses the recency-derived default
     *  on every later FloodTimestepsReceived. This is user intent, not a cached derivation. */
    userChoseMapMode: boolean
    /** From GET /flood/mode. In DEMO with a pinned step, `timesteps` holds that step alone. */
    mode: FloodMode
}

/** Data is fresh enough to default into Flood mode when the selected timestep's valid_time is
 *  within this window of now. */
export const FRESH_DATA_WINDOW_MS = 45 * 60 * 1000

/** How often useFloodBootstrap re-fetches timesteps. Well under FRESH_DATA_WINDOW_MS, so a
 *  session left open re-anchors selectedIndex to the clock long before data goes stale, instead
 *  of freezing on whatever was now at page load. */
export const TIMESTEP_REFRESH_INTERVAL_MS = 5 * 60 * 1000

/** `receivedAt` is the clock read, taken once at the fetch boundary, so the reducer stays pure
 *  and every time-dependent decision in this store is reproducible in a test. */
export class FloodTimestepsReceived implements Action {
    constructor(
        readonly timesteps: FloodTimestep[],
        readonly receivedAt: number,
    ) {}
}

export class FloodModeReceived implements Action {
    constructor(readonly mode: FloodMode) {}
}

/** Explicit user toggle of the map/flood switch. Sets userChoseMapMode. */
export class SetMapMode implements Action {
    constructor(readonly mode: MapMode) {}
}

export class SelectFloodVehicle implements Action {
    constructor(readonly vehicleType: string) {}
}

// '/flood/*' and '/route' live behind the same backend — see
// backend/server.py and backend/flood_areas.py in floodmap-backend.
export const BACKEND_BASE: string = (config as any).floodBackend || (config as any).routingApi || '/api/gh/'

/**
 * Index of the timestep the map shows as now: the latest valid_time at or before `now`, never a
 * nearer one in the future, so the map never shows a forecast as the present.
 *
 * When every step is after `now`, falls back to the earliest step (index 0 of the ascending
 * list) rather than a blank map. That happens before the first run has published its first step,
 * or when the viewer's clock runs behind the server's.
 *
 * Returns -1 for an empty list. Entries whose valid_time does not parse are skipped; if every
 * entry is unparseable the result is -1.
 */
export function findNowTimestepIndex(timesteps: readonly FloodTimestep[], now: number): number {
    let latest = -1
    let latestTime = -Infinity
    let earliest = -1
    for (let i = 0; i < timesteps.length; i++) {
        const t = Date.parse(timesteps[i].valid_time)
        if (Number.isNaN(t)) continue
        if (earliest < 0) earliest = i
        if (t <= now && t >= latestTime) {
            latestTime = t
            latest = i
        }
    }
    return latest >= 0 ? latest : earliest
}

/**
 * Data-recency default: Flood mode when the step the map shows sits within FRESH_DATA_WINDOW_MS
 * of now. It measures the selected step, not the newest one, because the newest step is a
 * forecast and says nothing about whether the map's picture of now is stale. The measure is
 * |t - now| so the future step of findNowTimestepIndex's fallback also counts as fresh.
 */
export function defaultMapMode(selected: FloodTimestep | undefined, now: number): MapMode {
    if (!selected) return 'map'
    const t = Date.parse(selected.valid_time)
    if (Number.isNaN(t)) return 'map'
    return Math.abs(t - now) <= FRESH_DATA_WINDOW_MS ? 'flood' : 'map'
}

class FloodStore extends Store<FloodStoreState> {
    constructor() {
        super({
            timesteps: [],
            selectedIndex: -1,
            vehicleType: 'motorbike',
            // Demo default: open straight into Flood mode rather than the recency-derived
            // default (see defaultMapMode/I3-I4). userChoseMapMode: true so the first
            // FloodTimestepsReceived doesn't immediately recompute it away.
            mapMode: 'flood',
            userChoseMapMode: true,
            mode: { kind: 'LIVE' },
        })
    }

    reduce(state: FloodStoreState, action: Action): FloodStoreState {
        if (action instanceof FloodModeReceived) {
            const pinned = action.mode.kind === 'DEMO' ? action.mode.pinned : null
            return pinned
                ? { ...state, mode: action.mode, timesteps: [pinned], selectedIndex: 0 }
                : { ...state, mode: action.mode }
        } else if (action instanceof FloodTimestepsReceived) {
            if (state.mode.kind === 'DEMO' && state.mode.pinned) return state
            // Every refetch re-picks from the clock. Following the previous (valid_time, run) would
            // freeze the map: a run's first step stays the newest publisher of its valid_time, so
            // it stays listed long after it stops being now. No UI selects a step by hand.
            const selectedIndex = findNowTimestepIndex(action.timesteps, action.receivedAt)
            return {
                ...state,
                timesteps: action.timesteps,
                selectedIndex,
                mapMode: state.userChoseMapMode
                    ? state.mapMode
                    : defaultMapMode(action.timesteps[selectedIndex], action.receivedAt),
            }
        } else if (action instanceof SetMapMode) {
            if (action.mode === state.mapMode && state.userChoseMapMode) return state
            return { ...state, mapMode: action.mode, userChoseMapMode: true }
        } else if (action instanceof SelectFloodVehicle) {
            return { ...state, vehicleType: action.vehicleType }
        }
        return state
    }
}

const floodStore = new FloodStore()
Dispatcher.register(floodStore)

export function getFloodStore() {
    return floodStore
}

export async function loadFloodTimesteps() {
    // The mode goes first so that a pinned step is already in place when the newest run's steps arrive.
    const modeRes = await fetch(new URL(`${BACKEND_BASE}flood/mode`, window.location.href))
    if (modeRes.ok) Dispatcher.dispatch(new FloodModeReceived(parseFloodMode(await modeRes.json())))
    const res = await fetch(new URL(`${BACKEND_BASE}flood/timesteps`, window.location.href))
    if (!res.ok) return
    const data = await res.json()
    // Read the clock after the await: the now step should be now at the moment the user sees the
    // result, not at the moment the request left.
    Dispatcher.dispatch(new FloodTimestepsReceived(data.timesteps || [], Date.now()))
}

/** Re-sends the current route request unchanged; the fetch interceptor
 * below is what actually attaches the flood parameters, so this is the
 * only bit of app.tsx-side plumbing needed to make the map re-plan when
 * the timestep changes. */
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
                        // Not body.vehicle_type = state.vehicleType: that field is never set by
                        // dispatching SelectFloodVehicle (nothing does), so every request carried
                        // the initial 'motorbike' regardless of the selected routing profile.
                        // backend/server.py:_handle_route falls back to body.profile when
                        // vehicle_type is absent, and profile names (motorbike/car/truck/foot)
                        // match VEHICLE_PROFILES one to one, so omitting this lets each request
                        // — including the separate per-mode travel-time requests — use its own
                        // profile's flood depth limit instead of always the strictest one.
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
