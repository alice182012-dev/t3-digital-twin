import { profileTimesKey, requestProfileTimes } from '@/sidebar/search/routingProfiles/profileTimes'
import { Path, RoutingArgs, RoutingResult } from '@/api/graphhopper'
import DummyApi from '../DummyApi'

const ARGS: RoutingArgs = {
    points: [
        [105.85, 21.03],
        [105.86, 21.02],
    ],
    profile: 'car',
    maxAlternativeRoutes: 3,
    customModel: null,
}

const PROFILES = ['car', 'motorbike', 'foot', 'truck']

const FLOOD = {
    timesteps: [
        { valid_time: '2026-09-12T23:00:00+07:00', run: '2026-09-12T18:00:00Z' },
        { valid_time: '2026-09-12T23:30:00+07:00', run: '2026-09-12T18:00:00Z' },
    ],
    selectedIndex: 0,
    vehicleType: 'motorbike',
}

describe('profileTimesKey', () => {
    it('does not change when only the selected profile or the alternative count changes', () => {
        const switched = { ...ARGS, profile: 'foot', maxAlternativeRoutes: 1 }
        expect(profileTimesKey(switched, PROFILES, FLOOD)).toEqual(profileTimesKey(ARGS, PROFILES, FLOOD))
    })

    it('changes when the points change', () => {
        const moved: RoutingArgs = { ...ARGS, points: [ARGS.points[0], [105.9, 21.0]] }
        expect(profileTimesKey(moved, PROFILES, FLOOD)).not.toEqual(profileTimesKey(ARGS, PROFILES, FLOOD))
    })

    it('changes when the flood timestep changes', () => {
        const later = { ...FLOOD, selectedIndex: 1 }
        expect(profileTimesKey(ARGS, PROFILES, later)).not.toEqual(profileTimesKey(ARGS, PROFILES, FLOOD))
    })

    it('does not change when the same timesteps are refetched as new objects', () => {
        const refetched = { ...FLOOD, timesteps: FLOOD.timesteps.map(s => ({ ...s })) }
        expect(profileTimesKey(ARGS, PROFILES, refetched)).toEqual(profileTimesKey(ARGS, PROFILES, FLOOD))
    })
})

class TimedApi extends DummyApi {
    readonly sent: RoutingArgs[] = []

    constructor(private readonly times: Record<string, number>) {
        super()
    }

    route(args: RoutingArgs): Promise<RoutingResult> {
        this.sent.push(args)
        const time = this.times[args.profile]
        if (time === undefined) return Promise.reject(new Error('Cannot find point'))
        return Promise.resolve({
            info: { took: 0, road_data_timestamp: '', copyright: [] },
            paths: [{ time } as Path],
        })
    }
}

describe('requestProfileTimes', () => {
    it('sends one request per profile without alternatives and reports each time', async () => {
        const api = new TimedApi({ car: 240_000, motorbike: 250_000, foot: 840_000, truck: 300_000 })
        const times: Record<string, number> = {}
        requestProfileTimes(api, ARGS, PROFILES, (profile, ms) => (times[profile] = ms))
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(api.sent.map(a => [a.profile, a.maxAlternativeRoutes])).toEqual([
            ['car', 1],
            ['motorbike', 1],
            ['foot', 1],
            ['truck', 1],
        ])
        expect(times).toEqual({ car: 240_000, motorbike: 250_000, foot: 840_000, truck: 300_000 })
    })

    it('leaves out a profile whose request fails', async () => {
        const warn = jest.spyOn(console, 'warn').mockImplementation(() => {})
        const api = new TimedApi({ car: 240_000, motorbike: 250_000, truck: 300_000 })
        const times: Record<string, number> = {}
        requestProfileTimes(api, ARGS, PROFILES, (profile, ms) => (times[profile] = ms))
        await new Promise(resolve => setTimeout(resolve, 0))

        expect(times).toEqual({ car: 240_000, motorbike: 250_000, truck: 300_000 })
        warn.mockRestore()
    })
})
