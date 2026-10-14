import { useEffect, useState } from 'react'
import { BACKEND_BASE, FloodTimestep } from '@/floodmap/FloodStore'
import { DepthSample, maxDepthCm } from '@/floodmap/depthBadges'

type Coordinates = readonly number[][]

const profiles = new Map<string, Promise<DepthSample[] | null>>()
const MAX_CACHED = 50

function profileKey(coordinates: Coordinates, timestep: FloodTimestep): string {
    return `${timestep.valid_time}|${timestep.run}|${coordinates.length}|${coordinates[0]}|${coordinates[coordinates.length - 1]}`
}

/**
 * POST /flood/profile, once per route and timestep: the badges of the selected route and the
 * tab of every alternative ask for the same profile, and a tab switch asks again.
 */
function fetchDepthProfile(coordinates: Coordinates, timestep: FloodTimestep): Promise<DepthSample[] | null> {
    const key = profileKey(coordinates, timestep)
    const cached = profiles.get(key)
    if (cached) return cached
    const request = fetch(new URL(`${BACKEND_BASE}flood/profile`, window.location.href), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            points: coordinates.map(([lng, lat]) => [lng, lat]),
            valid_time: timestep.valid_time,
            run: timestep.run,
        }),
    })
        .then(res => (res.ok ? res.json() : null))
        .catch(() => null)
        .then(body => {
            const samples: DepthSample[] | null = body?.samples ?? null
            // A failure is not remembered, so the next render retries it.
            if (samples === null) profiles.delete(key)
            return samples
        })
    if (profiles.size >= MAX_CACHED) profiles.clear()
    profiles.set(key, request)
    return request
}

/**
 * The depth at evenly spaced samples along a route for one timestep (POST /flood/profile), or
 * null until the answer arrives and when the request fails. `coordinates` are the route's
 * [lng, lat] vertices. Nothing is requested without a timestep or a route.
 */
export function useDepthProfile(coordinates: Coordinates, timestep: FloodTimestep | undefined): DepthSample[] | null {
    return useDepthProfiles([coordinates], timestep)[0]
}

/** The maximum depth in cm along each route, in parallel. An entry is null until its answer arrives. */
export function useMaxDepthsCm(routes: readonly Coordinates[], timestep: FloodTimestep | undefined): (number | null)[] {
    return useDepthProfiles(routes, timestep).map(samples => (samples ? maxDepthCm(samples) : null))
}

function useDepthProfiles(routes: readonly Coordinates[], timestep: FloodTimestep | undefined) {
    const [answers, setAnswers] = useState<{ key: string; samples: (DepthSample[] | null)[] }>({ key: '', samples: [] })
    const key = timestep ? routes.map(r => (r.length > 1 ? profileKey(r, timestep) : '')).join('\n') : ''

    useEffect(() => {
        if (!timestep) return
        let stale = false
        Promise.all(routes.map(r => (r.length > 1 ? fetchDepthProfile(r, timestep) : null))).then(
            samples => stale || setAnswers({ key, samples }),
        )
        return () => {
            stale = true
        }
    }, [key])

    // An answer for another route or timestep reads as unknown, never as a stale depth.
    return routes.map((_, i) => (answers.key === key ? (answers.samples[i] ?? null) : null))
}
