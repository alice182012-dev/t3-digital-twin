import {
    adviceFromAnswer,
    adviceText,
    DeparturesAnswer,
    departuresRequestBody,
    formatClockTime,
    loadAdvice,
    noConnectionTarget,
    runLabel,
} from '@/floodmap/departureAdvice'
import { RoutingArgs } from '@/api/graphhopper'
import { RequestState, SubRequest } from '@/stores/QueryStore'

const args: RoutingArgs = {
    points: [
        [105.755, 21.025],
        [105.762, 21.0255],
    ],
    profile: 'car',
    maxAlternativeRoutes: 1,
    customModel: null,
}

function local(h: number, m: number): string {
    return new Date(2026, 9, 5, h, m).toISOString()
}

function candidate(h: number, m: number, status: 'clear' | 'blocked' | 'unknown') {
    return { departure: local(h, m), leave_at: local(h, m), arrival: local(h, m + 5), status }
}

function answer(over: Partial<DeparturesAnswer>): DeparturesAnswer {
    return {
        status: 'ok',
        run: '20261005T170000',
        run_age_s: 600,
        generated_at: local(17, 10),
        candidates: [],
        earliest_clear: null,
        ...over,
    }
}

describe('noConnectionTarget', () => {
    const failed = (noConnection?: boolean): SubRequest => ({ args, state: RequestState.FAILED, noConnection })

    it('is the request that failed with no connection', () => {
        expect(noConnectionTarget([failed(true)])).toBe(args)
    })

    it('is null for another failure, a pending request, or no request', () => {
        expect(noConnectionTarget([failed(false)])).toBeNull()
        expect(noConnectionTarget([failed(undefined)])).toBeNull()
        expect(noConnectionTarget([{ args, state: RequestState.SENT }])).toBeNull()
        expect(noConnectionTarget([])).toBeNull()
    })

    it('is null while another request is still pending or when one succeeded', () => {
        expect(noConnectionTarget([failed(true), { args, state: RequestState.SENT }])).toBeNull()
        expect(noConnectionTarget([failed(true), { args, state: RequestState.SUCCESS }])).toBeNull()
    })
})

describe('departuresRequestBody', () => {
    it('carries the points and the profile and nothing the server decides', () => {
        expect(departuresRequestBody(args)).toEqual({
            points: [
                [105.755, 21.025],
                [105.762, 21.0255],
            ],
            profile: 'car',
        })
    })
})

describe('formatClockTime and runLabel', () => {
    it('reads HH:MM in the local zone', () => {
        expect(formatClockTime(local(18, 5))).toBe('18:05')
        expect(formatClockTime('not a time')).toBeNull()
    })

    it('reads the HH:MM of a run name', () => {
        expect(runLabel('20261005T170000')).toBe('17:00')
        expect(runLabel('latest')).toBeNull()
        expect(runLabel('')).toBeNull()
    })
})

describe('adviceFromAnswer', () => {
    it('names the earliest clear departure and the run', () => {
        const c = candidate(18, 15, 'clear')
        const advice = adviceFromAnswer(answer({ candidates: [candidate(17, 15, 'blocked'), c], earliest_clear: c }))
        expect(advice).toEqual({ kind: 'clear_from', time: '18:15', run: '17:00' })
    })

    it('says no clear departure appears when every step is blocked', () => {
        const advice = adviceFromAnswer(
            answer({ candidates: [candidate(17, 15, 'blocked'), candidate(17, 30, 'blocked')] }),
        )
        expect(advice).toEqual({ kind: 'none', run: '17:00' })
    })

    it('says no clear departure appears when some steps are blocked and the rest cannot be judged', () => {
        const advice = adviceFromAnswer(
            answer({ candidates: [candidate(17, 15, 'blocked'), candidate(17, 30, 'unknown')] }),
        )
        expect(advice.kind).toBe('none')
    })

    it('does not claim a verdict when nothing could be judged', () => {
        expect(adviceFromAnswer(answer({ candidates: [candidate(17, 15, 'unknown')] })).kind).toBe('unavailable')
        expect(adviceFromAnswer(answer({ candidates: [] })).kind).toBe('unavailable')
    })

    it('says the timing check is unavailable when the server says so', () => {
        expect(adviceFromAnswer(answer({ status: 'unavailable', reason: 'no table' }))).toEqual({ kind: 'unavailable' })
    })
})

describe('adviceText', () => {
    it('says clear in the forecast and names the run', () => {
        expect(adviceText({ kind: 'clear_from', time: '18:15', run: '17:00' })).toBe(
            'The usual route is clear from 18:15 (forecast run 17:00)',
        )
    })

    it('leaves the run out when it has no readable time', () => {
        expect(adviceText({ kind: 'clear_from', time: '18:15', run: null })).toBe('The usual route is clear from 18:15')
    })

    it('says no route is clear in the next 2 hours and to check after the next run', () => {
        expect(adviceText({ kind: 'none', run: '17:00' })).toBe(
            'No safe route in the next 2 hours. Check again after the next forecast run.',
        )
    })

    it('says the timing check is unavailable', () => {
        expect(adviceText({ kind: 'unavailable' })).toBe('Timing check unavailable')
    })

    it('says it is loading', () => {
        expect(adviceText({ kind: 'loading' })).toBe('Checking when a route opens…')
    })
})

describe('loadAdvice', () => {
    const ok = (body: unknown) => ({ ok: true, json: async () => body }) as Response

    it('posts the points and the profile to route/departures and reads the answer', async () => {
        const c = candidate(18, 15, 'clear')
        const fetchImpl = jest.fn().mockResolvedValue(ok(answer({ candidates: [c], earliest_clear: c })))

        const advice = await loadAdvice(fetchImpl, '/api/gh/', args)

        expect(advice).toEqual({ kind: 'clear_from', time: '18:15', run: '17:00' })
        const [url, init] = fetchImpl.mock.calls[0]
        expect(String(url)).toMatch(/\/api\/gh\/route\/departures$/)
        expect(init.method).toBe('POST')
        expect(JSON.parse(init.body)).toEqual(departuresRequestBody(args))
    })

    it('is unavailable on an HTTP error, a network error, or a body that is not an answer', async () => {
        expect(await loadAdvice(jest.fn().mockResolvedValue({ ok: false, status: 500 }), '/api/gh/', args)).toEqual({
            kind: 'unavailable',
        })
        expect(await loadAdvice(jest.fn().mockRejectedValue(new Error('offline')), '/api/gh/', args)).toEqual({
            kind: 'unavailable',
        })
        expect(await loadAdvice(jest.fn().mockResolvedValue(ok({ nope: 1 })), '/api/gh/', args)).toEqual({
            kind: 'unavailable',
        })
    })

    it('passes the abort signal through and lets an abort stand', async () => {
        const controller = new AbortController()
        const fetchImpl = jest.fn().mockRejectedValue(Object.assign(new Error('aborted'), { name: 'AbortError' }))
        controller.abort()
        await expect(loadAdvice(fetchImpl, '/api/gh/', args, controller.signal)).rejects.toMatchObject({
            name: 'AbortError',
        })
        expect(fetchImpl.mock.calls[0][1].signal).toBe(controller.signal)
    })
})
