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
}

/** Data is fresh enough to default into Flood mode when the newest timestep's valid_time is
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
 * Where selectedIndex should land after a new timestep list arrives.
 *
 * If the currently selected (valid_time, run) pair still exists in the new list, follow it to its
 * new position: a refetch must not move the map out from under someone mid-inspection. Otherwise
 * re-anchor to the now step. Identity, not ordinal position, is what the user selected, so this
 * needs no separate "has the user picked a step" flag.
 */
export function reanchorTimestepIndex(prev: FloodStoreState, next: readonly FloodTimestep[], now: number): number {
    const current = prev.timesteps[prev.selectedIndex]
    if (current) {
        const i = next.findIndex(s => s.valid_time === current.valid_time && s.run === current.run)
        if (i >= 0) return i
    }
    return findNowTimestepIndex(next, now)
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
