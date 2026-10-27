import { useEffect, useState } from 'react'
import { BACKEND_BASE, FloodTimestep } from '@/floodmap/FloodStore'
import { DepthReading, depthQuery, readingFromResponse } from '@/floodmap/placeDepth'
import { Coordinate } from '@/utils'

/**
 * The depth at each point for one flood timestep, in the order of `points`. An entry is
 * `undefined` until its request answers, and `unavailable` when the request fails, so a failure
 * never reads as dry. Without a timestep nothing is requested and every entry stays `undefined`.
 * Each point is one GET /flood/points. The backend pools its connections and answered 30
 * concurrent requests without an error, so a route's steps are requested together.
 */
export function useStepDepths(
    points: readonly Coordinate[],
    timestep: FloodTimestep | undefined,
): (DepthReading | undefined)[] {
    const [readings, setReadings] = useState<(DepthReading | undefined)[]>([])
    const key = timestep && `${timestep.valid_time}|${timestep.run}|${points.map(p => `${p.lat},${p.lng}`).join(';')}`

    useEffect(() => {
        setReadings(points.map(() => undefined))
        if (!timestep) return
        const controller = new AbortController()
        points.forEach((point, i) => {
            fetch(new URL(`${BACKEND_BASE}flood/points?${depthQuery(point, timestep)}`, window.location.href), {
                signal: controller.signal,
            })
                .then(res => (res.ok ? res.json() : null))
                .catch(() => null)
                .then(body => {
                    if (controller.signal.aborted) return
                    setReadings(current => current.map((r, j) => (j === i ? readingFromResponse(body) : r)))
                })
        })
        return () => controller.abort()
    }, [key])

    return readings
}
