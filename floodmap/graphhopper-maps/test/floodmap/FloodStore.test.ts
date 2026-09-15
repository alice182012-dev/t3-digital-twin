import {
    clampTimestepIndex,
    defaultMapMode,
    findNearestTimestepIndex,
    FloodStoreState,
    FloodTimestep,
    reanchorTimestepIndex,
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

describe('findNearestTimestepIndex', () => {
    it('picks the closest step', () => {
        expect(findNearestTimestepIndex(HOURLY, at('2026-05-22T10:40:00Z'))).toEqual(1)
    })

    it('returns -1 for an empty list', () => {
        expect(findNearestTimestepIndex([], at('2026-05-22T10:00:00Z'))).toEqual(-1)
    })

    it('returns the only index for a single element', () => {
        expect(findNearestTimestepIndex([step('2026-05-22T10:00:00Z')], at('2030-01-01T00:00:00Z'))).toEqual(0)
    })

    it('resolves an exact tie to the later valid_time', () => {
        expect(findNearestTimestepIndex(HOURLY, at('2026-05-22T10:30:00Z'))).toEqual(1)
    })

    it('picks the last step when every step is in the past', () => {
        expect(findNearestTimestepIndex(HOURLY, at('2026-05-22T23:00:00Z'))).toEqual(2)
    })

    it('picks the first step when every step is in the future', () => {
        expect(findNearestTimestepIndex(HOURLY, at('2026-05-22T00:00:00Z'))).toEqual(0)
    })

    it('skips unparseable valid_times', () => {
        const steps = [step('not-a-date'), step('2026-05-22T11:00:00Z')]
        expect(findNearestTimestepIndex(steps, at('2026-05-22T11:05:00Z'))).toEqual(1)
    })

    it('returns -1 when every valid_time is unparseable', () => {
        expect(findNearestTimestepIndex([step('nope'), step('also nope')], at('2026-05-22T11:00:00Z'))).toEqual(-1)
    })
})

describe('clampTimestepIndex', () => {
    it('returns -1 for an empty list', () => {
        expect(clampTimestepIndex(0, [])).toEqual(-1)
    })

    it('keeps an in-range index', () => {
        expect(clampTimestepIndex(1, HOURLY)).toEqual(1)
    })

    it('clamps below and above the range', () => {
        expect(clampTimestepIndex(-5, HOURLY)).toEqual(0)
        expect(clampTimestepIndex(99, HOURLY)).toEqual(2)
    })

    it('rejects a non-integer index', () => {
        expect(clampTimestepIndex(1.5, HOURLY)).toEqual(-1)
        expect(clampTimestepIndex(NaN, HOURLY)).toEqual(-1)
    })
})

describe('reanchorTimestepIndex', () => {
    function stateWith(timesteps: FloodTimestep[], selectedIndex: number): FloodStoreState {
        return {
            timesteps,
            selectedIndex,
            vehicleType: 'motorbike',
            tilesVisible: true,
            mapMode: 'map',
            userChoseMapMode: false,
            availableRuns: [],
            selectedRun: null,
        }
    }

    it('follows the selected step to its new position when the identity survives', () => {
        const prev = stateWith(HOURLY, 2)
        const next = [step('2026-05-22T09:00:00Z'), ...HOURLY]
        expect(reanchorTimestepIndex(prev, next, at('2026-05-22T09:00:00Z'))).toEqual(3)
    })

    it('falls back to nearest-to-now when the identity is gone', () => {
        const prev = stateWith(HOURLY, 0)
        const next = [step('2026-05-22T13:00:00Z'), step('2026-05-22T14:00:00Z')]
        expect(reanchorTimestepIndex(prev, next, at('2026-05-22T13:50:00Z'))).toEqual(1)
    })

    it('treats a same valid_time from a different run as a different step', () => {
        const prev = stateWith(HOURLY, 0)
        const next = [step('2026-05-22T10:00:00Z', '2026-05-22T09:00:00Z')]
        expect(reanchorTimestepIndex(prev, next, at('2026-05-22T10:00:00Z'))).toEqual(0)
    })

    it('re-anchors from an empty previous selection', () => {
        const prev = stateWith([], -1)
        expect(reanchorTimestepIndex(prev, HOURLY, at('2026-05-22T11:10:00Z'))).toEqual(1)
    })
})

describe('defaultMapMode', () => {
    it('is map mode for an empty list', () => {
        expect(defaultMapMode([], at('2026-05-22T10:00:00Z'))).toEqual('map')
    })

    it('is flood mode when the newest step is inside the fresh window, in either direction', () => {
        expect(defaultMapMode(HOURLY, at('2026-05-22T11:30:00Z'))).toEqual('flood')
        expect(defaultMapMode(HOURLY, at('2026-05-22T12:30:00Z'))).toEqual('flood')
    })

    it('is map mode when the newest step is outside the fresh window', () => {
        expect(defaultMapMode(HOURLY, at('2026-05-22T14:00:00Z'))).toEqual('map')
    })

    it('is map mode when the newest valid_time is unparseable', () => {
        expect(defaultMapMode([step('2026-05-22T12:00:00Z'), step('bad')], at('2026-05-22T12:00:00Z'))).toEqual('map')
    })
})
