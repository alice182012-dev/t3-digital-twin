import Store from '@/stores/Store'
import Dispatcher, { Action } from '@/stores/Dispatcher'
import { getApi } from '@/api/Api'
import { getQueryStore } from '@/stores/Stores'
import * as config from 'config'

export interface FloodTimestep {
    valid_time: string
    run: string
}

export interface FloodStoreState {
    timesteps: FloodTimestep[]
    selectedIndex: number
    vehicleType: string
    tilesVisible: boolean
}

export class FloodTimestepsReceived implements Action {
    constructor(readonly timesteps: FloodTimestep[]) {}
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

class FloodStore extends Store<FloodStoreState> {
    constructor() {
        super({ timesteps: [], selectedIndex: -1, vehicleType: 'motorbike', tilesVisible: true })
    }

    reduce(state: FloodStoreState, action: Action): FloodStoreState {
        if (action instanceof FloodTimestepsReceived) {
            return {
                ...state,
                timesteps: action.timesteps,
                selectedIndex: state.selectedIndex >= 0 ? state.selectedIndex : action.timesteps.length - 1,
            }
        } else if (action instanceof SelectFloodTimestep) {
            return { ...state, selectedIndex: action.index }
        } else if (action instanceof SelectFloodVehicle) {
            return { ...state, vehicleType: action.vehicleType }
        } else if (action instanceof ToggleFloodTiles) {
            return { ...state, tilesVisible: action.visible }
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
    const res = await fetch(`${BACKEND_BASE}flood/timesteps`)
    if (!res.ok) return
    const data = await res.json()
    Dispatcher.dispatch(new FloodTimestepsReceived(data.timesteps || []))
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
    const realFetch = window.fetch.bind(window)
    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
        try {
            const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
            const method = (init?.method || (typeof input !== 'string' && !(input instanceof URL) ? input.method : 'GET')) as string
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
