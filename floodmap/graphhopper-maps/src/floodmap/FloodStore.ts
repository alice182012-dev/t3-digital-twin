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
    areas: GeoJSON.FeatureCollection | null
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

export class FloodAreasReceived implements Action {
    constructor(
        readonly areas: GeoJSON.FeatureCollection,
        readonly index: number,
        readonly vehicleType: string,
    ) {}
}

// '/flood/*' and '/route' live behind the same backend — see
// backend/server.py and backend/flood_areas.py in floodmap-backend.
const BACKEND_BASE: string = (config as any).floodBackend || (config as any).routingApi || '/api/gh/'

class FloodStore extends Store<FloodStoreState> {
    constructor() {
        super({ timesteps: [], selectedIndex: -1, vehicleType: 'motorbike', areas: null })
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
            return { ...state, vehicleType: action.vehicleType, areas: null }
        } else if (action instanceof FloodAreasReceived) {
            if (action.index !== state.selectedIndex || action.vehicleType !== state.vehicleType) return state
            return { ...state, areas: action.areas }
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

export async function loadFloodAreas(index: number, vehicleType: string) {
    const step = floodStore.state.timesteps[index]
    if (!step) return
    const url = new URL(`${BACKEND_BASE}flood/areas`, window.location.href)
    url.searchParams.set('valid_time', step.valid_time)
    url.searchParams.set('run', step.run)
    url.searchParams.set('vehicle_type', vehicleType)
    const res = await fetch(url.toString())
    if (!res.ok) return
    const areas = await res.json()
    Dispatcher.dispatch(new FloodAreasReceived(areas, index, vehicleType))
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
