import {
    defaultMapMode,
    findNowTimestepIndex,
    FloodModeReceived,
    FloodStoreState,
    FloodTimestep,
    FloodTimestepsReceived,
    getFloodStore,
} from '@/floodmap/FloodStore'

const RUN = '2026-05-22T06:00:00Z'

function step(validTime: string, run: string = RUN): FloodTimestep {
    return { valid_time: validTime, run }
}

const HOURLY: FloodTimestep[] = [
    step('2026-05-22T10:00:00Z'),
    step('2026-05-22T11:00:00Z'),
    step('2026-05-22T12:00:00Z'),
]

function at(iso: string): number {
    return Date.parse(iso)
}

// Per valid_time, the newest run that published it: 10:15 from the 10:00 run, then the 10:15 run's
// steps 1 and 2.
const CROSS_RUN: FloodTimestep[] = [
    step('2026-05-22T10:15:00Z', '2026-05-22T10:00:00Z'),
    step('2026-05-22T10:30:00Z', '2026-05-22T10:15:00Z'),
    step('2026-05-22T10:45:00Z', '2026-05-22T10:15:00Z'),
]

describe('findNowTimestepIndex', () => {
    it('picks the latest step at or before now, not a nearer one in the future', () => {
        expect(findNowTimestepIndex(CROSS_RUN, at('2026-05-22T10:44:00Z'))).toEqual(1)
    })

    it('picks a step whose valid_time equals now', () => {
        expect(findNowTimestepIndex(CROSS_RUN, at('2026-05-22T10:30:00Z'))).toEqual(1)
    })

    it('picks the last step when every step is in the past', () => {
        expect(findNowTimestepIndex(HOURLY, at('2026-05-22T23:00:00Z'))).toEqual(2)
    })

    it('falls back to the earliest step when every step is in the future', () => {
        expect(findNowTimestepIndex(CROSS_RUN, at('2026-05-22T10:14:59Z'))).toEqual(0)
    })

    it('returns -1 for an empty list', () => {
        expect(findNowTimestepIndex([], at('2026-05-22T10:00:00Z'))).toEqual(-1)
    })

    it('skips unparseable valid_times', () => {
        const steps = [step('not-a-date'), step('2026-05-22T11:00:00Z'), step('2026-05-22T12:00:00Z')]
        expect(findNowTimestepIndex(steps, at('2026-05-22T11:05:00Z'))).toEqual(1)
        expect(findNowTimestepIndex(steps, at('2026-05-22T10:00:00Z'))).toEqual(1)
    })

    it('returns -1 when every valid_time is unparseable', () => {
        expect(findNowTimestepIndex([step('nope'), step('also nope')], at('2026-05-22T11:00:00Z'))).toEqual(-1)
    })
})

describe('defaultMapMode', () => {
    it('is map mode when no step is selected', () => {
        expect(defaultMapMode(undefined, at('2026-05-22T10:00:00Z'))).toEqual('map')
    })

    it('is flood mode when the selected step is inside the fresh window, in either direction', () => {
        expect(defaultMapMode(step('2026-05-22T10:00:00Z'), at('2026-05-22T10:40:00Z'))).toEqual('flood')
        expect(defaultMapMode(step('2026-05-22T10:00:00Z'), at('2026-05-22T09:20:00Z'))).toEqual('flood')
    })

    it('is map mode when the selected step is outside the fresh window', () => {
        expect(defaultMapMode(step('2026-05-22T10:00:00Z'), at('2026-05-22T10:50:00Z'))).toEqual('map')
    })

    it('is map mode when the selected valid_time is unparseable', () => {
        expect(defaultMapMode(step('bad'), at('2026-05-22T12:00:00Z'))).toEqual('map')
    })
})

describe('FloodTimestepsReceived', () => {
    function receive(timesteps: FloodTimestep[], now: string): FloodStoreState {
        const store = getFloodStore()
        return store.reduce({ ...store.state, userChoseMapMode: false }, new FloodTimestepsReceived(timesteps, at(now)))
    }

    it('defaults to map mode when the step shown as now is stale, even if a newer forecast is fresh', () => {
        const steps = [step('2026-05-22T09:00:00Z', '2026-05-22T08:45:00Z'), step('2026-05-22T10:45:00Z')]
        const state = receive(steps, '2026-05-22T10:30:00Z')
        expect(state.selectedIndex).toEqual(0)
        expect(state.mapMode).toEqual('map')
    })

    it('moves to the newer now step on a refetch, although the old step is still listed', () => {
        const store = getFloodStore()
        const first = store.reduce(store.state, new FloodTimestepsReceived(CROSS_RUN, at('2026-05-22T10:16:00Z')))
        expect(first.timesteps[first.selectedIndex]).toEqual(step('2026-05-22T10:15:00Z', '2026-05-22T10:00:00Z'))
        const next = store.reduce(first, new FloodTimestepsReceived(CROSS_RUN, at('2026-05-22T10:31:00Z')))
        expect(next.timesteps[next.selectedIndex]).toEqual(step('2026-05-22T10:30:00Z', '2026-05-22T10:15:00Z'))
    })
})

describe('FloodModeReceived', () => {
    const pinned = step('2026-10-11T02:00:00+07:00', '20261011T001500')

    it('shows the pinned step alone in DEMO and ignores the steps of the newest run', () => {
        const store = getFloodStore()
        const demo = store.reduce(store.state, new FloodModeReceived({ kind: 'DEMO', pinned }))
        const refetched = store.reduce(demo, new FloodTimestepsReceived(HOURLY, at('2026-05-22T11:05:00Z')))
        expect(refetched.timesteps).toEqual([pinned])
        expect(refetched.selectedIndex).toEqual(0)
    })

    it('follows the steps of the newest run again in LIVE', () => {
        const store = getFloodStore()
        const demo = store.reduce(store.state, new FloodModeReceived({ kind: 'DEMO', pinned }))
        const live = store.reduce(demo, new FloodModeReceived({ kind: 'LIVE' }))
        const refetched = store.reduce(live, new FloodTimestepsReceived(HOURLY, at('2026-05-22T11:05:00Z')))
        expect(refetched.timesteps).toEqual(HOURLY)
        expect(refetched.selectedIndex).toEqual(1)
    })
})
