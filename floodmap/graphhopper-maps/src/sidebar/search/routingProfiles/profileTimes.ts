import { useEffect, useState } from 'react'
import Api, { getApi } from '@/api/Api'
import { RoutingArgs } from '@/api/graphhopper'
import { QueryStoreState } from '@/stores/QueryStore'
import { FloodStoreState } from '@/floodmap/FloodStore'

/** Travel time in ms of each profile's fastest route for the current query, keyed by profile name.
 *  A missing entry means that profile's request is still in flight or failed. */
export type ProfileTimes = Readonly<Record<string, number>>

/**
 * Identifies the query the per-profile times answer. The selected profile and the alternative
 * count are left out on purpose: switching modes, or the follow-up request for alternatives,
 * must not re-request times that are already known. The flood timestep and vehicle are in,
 * because the routing interceptor in FloodStore routes around a different flood per timestep.
 */
export function profileTimesKey(
    args: RoutingArgs,
    profiles: readonly string[],
    flood: Pick<FloodStoreState, 'timesteps' | 'selectedIndex' | 'vehicleType'>,
): string {
    const step = flood.timesteps[flood.selectedIndex]
    return JSON.stringify([args.points, args.customModel, profiles, step, flood.vehicleType])
}

export function requestProfileTimes(
    api: Api,
    args: RoutingArgs,
    profiles: readonly string[],
    onTime: (profile: string, ms: number) => void,
): void {
    for (const profile of profiles)
        api.route({ ...args, profile, maxAlternativeRoutes: 1 })
            .then(result => {
                if (result.paths.length > 0) onTime(profile, result.paths[0].time)
            })
            .catch(error => console.warn(`travel time request for ${profile} failed:`, error))
}

/**
 * One route request per profile per query, reusing the args QueryStore built for the selected
 * route. Times are only returned while a route is on screen, but fetching doesn't wait for it, so
 * the extra requests run in parallel with the selected route's own request.
 */
export function useProfileTimes(query: QueryStoreState, flood: FloodStoreState, hasRoute: boolean): ProfileTimes {
    const args = query.currentRequest.subRequests[0]?.args
    const profiles = query.profiles.map(p => p.name)
    const key = args ? profileTimesKey(args, profiles, flood) : ''
    const [state, setState] = useState<{ key: string; times: ProfileTimes }>({ key: '', times: {} })

    useEffect(() => {
        if (!args) return
        let current = true
        requestProfileTimes(getApi(), args, profiles, (profile, ms) => {
            if (!current) return
            setState(s => ({ key, times: { ...(s.key === key ? s.times : {}), [profile]: ms } }))
        })
        return () => {
            current = false
        }
    }, [key])

    return hasRoute && state.key === key ? state.times : {}
}
