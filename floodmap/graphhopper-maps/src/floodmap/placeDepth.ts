import { FloodTimestep, FRESH_DATA_WINDOW_MS } from '@/floodmap/FloodStore'
import { formatTimestepTime } from '@/floodmap/timestepLabel'
import { Coordinate } from '@/utils'

/**
 * What the popup knows about the water at one point. `unavailable` covers a failed request and a
 * missing timestep, so a failure never reads as a dry point.
 */
export type DepthReading =
    | { kind: 'wet'; depthCm: number }
    | { kind: 'dry' }
    | { kind: 'no_data' }
    | { kind: 'unavailable' }

export interface Place {
    name: string
    address: string
}

/** A body of GET /flood/points (backend/flood_points.py). */
export function readingFromResponse(body: unknown): DepthReading {
    const { status, depth_m } = (body ?? {}) as { status?: unknown; depth_m?: unknown }
    if (status === 'dry') return { kind: 'dry' }
    if (status === 'no_data') return { kind: 'no_data' }
    if (status === 'wet' && typeof depth_m === 'number' && Number.isFinite(depth_m)) {
        return { kind: 'wet', depthCm: Math.round(depth_m * 100) }
    }
    return { kind: 'unavailable' }
}

/** A body of GET /places/reverse (backend/place_search.py's reverse_place). */
export function placeFromResponse(body: unknown): Place | null {
    const result = (body as { result?: { name?: unknown; address?: unknown } | null } | null)?.result
    if (!result || typeof result.name !== 'string' || !result.name) return null
    return { name: result.name, address: typeof result.address === 'string' ? result.address : '' }
}

/** `lat, lng` with six decimals, the format of the mockup's card ("20.992987, 105.773723"). */
export function coordinatesText(coordinate: Coordinate): string {
    return `${coordinate.lat.toFixed(6)}, ${coordinate.lng.toFixed(6)}`
}

/**
 * The card's depth line. "now" only when the step is at or before now and recent. A step older
 * than FRESH_DATA_WINDOW_MS is labeled with its time, and a step in the future as a forecast, so
 * the card never calls a stale or forecast depth the present.
 */
export function depthLine(reading: DepthReading, timestep: FloodTimestep | undefined, now: number): string {
    if (reading.kind === 'unavailable') return 'Water depth unavailable'
    if (reading.kind === 'no_data') return 'No flood data at this point'
    const value = reading.kind === 'dry' ? '0 cm' : reading.depthCm < 1 ? '< 1 cm' : `${reading.depthCm} cm`
    return `${depthLabel(timestep, now)}: ${value}`
}

function depthLabel(timestep: FloodTimestep | undefined, now: number): string {
    const t = timestep ? Date.parse(timestep.valid_time) : NaN
    const time = timestep ? formatTimestepTime(timestep.valid_time) : null
    if (Number.isNaN(t) || !time) return 'Water depth'
    if (t > now) return `Forecast water depth for ${time}`
    if (now - t > FRESH_DATA_WINDOW_MS) return `Water depth as of ${time}`
    return 'Water depth now'
}
