import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import NoSafeRouteMessage from '@/sidebar/NoSafeRouteMessage'
import { RoutingArgs } from '@/api/graphhopper'
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

const args: RoutingArgs = {
    points: [
        [105.755, 21.025],
        [105.762, 21.0255],
    ],
    profile: 'car',
    maxAlternativeRoutes: 1,
    customModel: null,
}
const BASE = 'No safe route available. Please consider getting to the safest location or stay where you are.'

function local(h: number, m: number): string {
    return new Date(2026, 9, 5, h, m).toISOString()
}

describe('NoSafeRouteMessage', () => {
    let container: HTMLDivElement
    let root: Root

    beforeEach(() => {
        container = document.createElement('div')
        document.body.appendChild(container)
        root = createRoot(container)
    })

    afterEach(() => {
        act(() => root.unmount())
        container.remove()
    })

    const answer = (extra: object) => ({
        ok: true,
        json: async () => ({
            status: 'ok',
            run: '20261005T170000',
            run_age_s: 60,
            generated_at: local(17, 10),
            candidates: [],
            earliest_clear: null,
            ...extra,
        }),
    })

    it('says only the old message and asks nothing when the failure was not a missing connection', async () => {
        const fetchImpl = jest.fn()
        await act(async () => root.render(<NoSafeRouteMessage target={null} fetchImpl={fetchImpl} />))
        expect(container.textContent).toBe(BASE)
        expect(fetchImpl).not.toHaveBeenCalled()
    })

    it('shows a loading line, then when the usual route is clear', async () => {
        let resolve: (v: unknown) => void = () => {}
        const fetchImpl = jest.fn().mockReturnValue(new Promise(r => (resolve = r)))
        await act(async () => root.render(<NoSafeRouteMessage target={args} fetchImpl={fetchImpl} />))
        expect(container.textContent).toContain(BASE)
        expect(container.textContent).toContain('Checking when a route opens…')

        const c = { departure: local(18, 15), leave_at: local(18, 15), arrival: local(18, 20), status: 'clear' }
        await act(async () => resolve(answer({ candidates: [c], earliest_clear: c })))

        expect(container.textContent).toContain(BASE)
        expect(container.textContent).toContain('The usual route is clear from 18:15 (forecast run 17:00)')
        expect(container.textContent).not.toContain('Checking')
    })

    it('says no route is clear in the next 2 hours', async () => {
        const c = { departure: local(18, 15), leave_at: local(18, 15), arrival: local(18, 20), status: 'blocked' }
        const fetchImpl = jest.fn().mockResolvedValue(answer({ candidates: [c] }))
        await act(async () => root.render(<NoSafeRouteMessage target={args} fetchImpl={fetchImpl} />))
        expect(container.textContent).toContain(
            'No safe route in the next 2 hours. Check again after the next forecast run.',
        )
    })

    it('says the timing check is unavailable when the table is, and when the request fails', async () => {
        await act(async () =>
            root.render(
                <NoSafeRouteMessage
                    target={args}
                    fetchImpl={jest.fn().mockResolvedValue(answer({ status: 'unavailable', reason: 'x' }))}
                />,
            ),
        )
        expect(container.textContent).toContain('Timing check unavailable')
        expect(container.textContent).toContain(BASE)

        await act(async () =>
            root.render(
                <NoSafeRouteMessage
                    target={{ ...args }}
                    fetchImpl={jest.fn().mockRejectedValue(new Error('offline'))}
                />,
            ),
        )
        expect(container.textContent).toContain('Timing check unavailable')
    })

    it('asks again for another pair of points and does not show the old answer', async () => {
        const c = { departure: local(18, 15), leave_at: local(18, 15), arrival: local(18, 20), status: 'clear' }
        const first = jest.fn().mockResolvedValue(answer({ candidates: [c], earliest_clear: c }))
        await act(async () => root.render(<NoSafeRouteMessage target={args} fetchImpl={first} />))
        expect(container.textContent).toContain('clear from 18:15')

        const never = jest.fn().mockReturnValue(new Promise(() => {}))
        await act(async () =>
            root.render(
                <NoSafeRouteMessage
                    target={{
                        ...args,
                        points: [
                            [105.7, 21.0],
                            [105.71, 21.01],
                        ],
                    }}
                    fetchImpl={never}
                />,
            ),
        )
        expect(container.textContent).toContain('Checking when a route opens…')
        expect(container.textContent).not.toContain('clear from 18:15')
    })
})
