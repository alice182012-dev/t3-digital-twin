import { useEffect, useState } from 'react'
import { BACKEND_BASE, FloodTimestep } from '@/floodmap/FloodStore'
import { DepthSample } from '@/floodmap/depthBadges'

/**
 * The depth at evenly spaced samples along a route for one timestep (POST /flood/profile), or
 * null until the answer arrives and when the request fails. `coordinates` are the route's
 * [lng, lat] vertices. Nothing is requested without a timestep or a route.
 */
export function useDepthProfile(
    coordinates: readonly number[][],
    timestep: FloodTimestep | undefined,
): DepthSample[] | null {
    const [samples, setSamples] = useState<DepthSample[] | null>(null)
    const key =
        timestep && coordinates.length > 1
            ? `${timestep.valid_time}|${timestep.run}|${coordinates.length}|${coordinates[0]}|${coordinates[coordinates.length - 1]}`
            : null

    useEffect(() => {
        setSamples(null)
        if (!timestep || coordinates.length < 2) return
        const controller = new AbortController()
        fetch(new URL(`${BACKEND_BASE}flood/profile`, window.location.href), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                points: coordinates.map(([lng, lat]) => [lng, lat]),
                valid_time: timestep.valid_time,
                run: timestep.run,
            }),
            signal: controller.signal,
        })
            .then(res => (res.ok ? res.json() : null))
            .catch(() => null)
            .then(body => controller.signal.aborted || setSamples(body?.samples ?? null))
        return () => controller.abort()
    }, [key])

    return samples
}
