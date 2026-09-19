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
 *      The reducer holds it, so a consumer never reads a stale or out-of-range index.
 *  I2. every timestep carries the same `run` (the backend pins list_timesteps to one run), so
 *      "latest timestep" is well defined.
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

export class SelectFloodVehicle implements Action {
    constructor(readonly vehicleType: string) {}
}

// '/flood/*' and '/route' live behind the same backend — see
// backend/server.py and backend/flood_areas.py in floodmap-backend.
export const BACKEND_BASE: string = (config as any).floodBackend || (config as any).routingApi || '/api/gh/'

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
            // Demo default: open straight into Flood mode rather than the recency-derived
            // default (see defaultMapMode/I3-I4). userChoseMapMode: true so the first
            // FloodTimestepsReceived doesn't immediately recompute it away.
            mapMode: 'flood',
            userChoseMapMode: true,
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
    const res = await fetch(new URL(`${BACKEND_BASE}flood/timesteps`, window.location.href))
    if (!res.ok) return
    const data = await res.json()
    // Read the clock after the await: "nearest to now" should be nearest to the moment the user
    // sees the result, not to the moment the request left.
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
