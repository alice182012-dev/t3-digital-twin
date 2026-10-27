import { RoutingArgs } from '@/api/graphhopper'
import { RequestState, SubRequest } from '@/stores/QueryStore'

/**
 * The "wait until" advice of the no-route alert (US-054). When a route request fails with no connection, the client asks
 * POST /route/departures (backend/departures.py) when the usual route clears, and the alert says so. The server owns the
 * clock, the margin, and the depth limit, so the request carries only the points and the profile.
 */

export interface DepartureCandidate {
    departure: string
    leave_at: string
    arrival: string
    status: 'clear' | 'blocked' | 'unknown'
}

export interface DeparturesAnswer {
    status: 'ok' | 'unavailable'
    run?: string
    run_age_s?: number
    generated_at: string
    reason?: string
    candidates: DepartureCandidate[]
    earliest_clear: DepartureCandidate | null
}

export type Advice =
    | { kind: 'loading' }
    | { kind: 'clear_from'; time: string; run: string | null }
    | { kind: 'none'; run: string | null }
    | { kind: 'unavailable' }

/**
 * The request that failed because no connection exists, or null. Other failures (a timeout, a server error) give no
 * advice, and neither does a request that is still pending or has succeeded.
 */
export function noConnectionTarget(subRequests: readonly SubRequest[]): RoutingArgs | null {
    if (subRequests.some(r => r.state === RequestState.SENT || r.state === RequestState.SUCCESS)) return null
    return subRequests.find(r => r.state === RequestState.FAILED && r.noConnection === true)?.args ?? null
}

export function departuresRequestBody(args: RoutingArgs): { points: [number, number][]; profile: string } {
    return { points: args.points.map(([lng, lat]) => [lng, lat]), profile: args.profile }
}

/** `HH:MM` in the viewer's local time zone, or null when the text is not a time. */
export function formatClockTime(iso: string): string | null {
    const t = Date.parse(iso)
    if (Number.isNaN(t)) return null
    const d = new Date(t)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** The `HH:MM` of a run name such as `20261005T170000`, or null for any other text. */
export function runLabel(run: string | undefined): string | null {
    const match = /^\d{8}T(\d{2})(\d{2})\d{2}$/.exec(run ?? '')
    return match ? `${match[1]}:${match[2]}` : null
}

export function adviceFromAnswer(answer: DeparturesAnswer): Advice {
    if (answer.status !== 'ok') return { kind: 'unavailable' }
    const run = runLabel(answer.run)
    const earliest = answer.earliest_clear
    if (earliest) {
        const time = formatClockTime(earliest.leave_at)
        return time ? { kind: 'clear_from', time, run } : { kind: 'unavailable' }
    }
    // Nothing is clear. Say so only when the forecast showed the route closed. A forecast that could not judge any step
    // gives no verdict.
    return answer.candidates.some(c => c.status === 'blocked') ? { kind: 'none', run } : { kind: 'unavailable' }
}

export function adviceText(advice: Advice): string {
    switch (advice.kind) {
        case 'loading':
            return 'Checking when a route opens…'
        case 'clear_from':
            return advice.run
                ? `The usual route is clear from ${advice.time} (forecast run ${advice.run})`
                : `The usual route is clear from ${advice.time}`
        case 'none':
            return 'No safe route in the next 2 hours. Check again after the next forecast run.'
        case 'unavailable':
            return 'Timing check unavailable'
    }
}

function isAnswer(body: unknown): body is DeparturesAnswer {
    const b = body as DeparturesAnswer
    return !!b && (b.status === 'ok' || b.status === 'unavailable') && Array.isArray(b.candidates)
}

/**
 * Asks the backend and turns the answer into advice. A failed request, a server error, or a body that is not an answer is
 * `unavailable`, so a problem with the advice never hides the alert. An abort is not swallowed: the caller dropped the
 * request and wants no advice.
 */
export async function loadAdvice(
    fetchImpl: typeof fetch,
    baseUrl: string,
    args: RoutingArgs,
    signal?: AbortSignal,
): Promise<Advice> {
    try {
        const response = await fetchImpl(new URL(`${baseUrl}route/departures`, window.location.href), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(departuresRequestBody(args)),
            signal,
        })
        if (!response.ok) return { kind: 'unavailable' }
        const body = await response.json()
        return isAnswer(body) ? adviceFromAnswer(body) : { kind: 'unavailable' }
    } catch (error) {
        if ((error as { name?: string })?.name === 'AbortError') throw error
        return { kind: 'unavailable' }
    }
}
