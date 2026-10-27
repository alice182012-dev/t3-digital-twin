import { Path } from '@/api/graphhopper'
import { RequestState, SubRequest } from '@/stores/QueryStore'
import { activeTabIndex, buildRouteTabs, parseRouteKinds, selectRoutingResultsView } from '@/sidebar/routingResultsView'

function path(description: string = ''): Path {
    return { description } as Path
}

function sent(): SubRequest {
    return { args: {} as any, state: RequestState.SENT }
}

function done(): SubRequest {
    return { args: {} as any, state: RequestState.SUCCESS }
}

describe('buildRouteTabs', () => {
    it('uses unique descriptions as labels', () => {
        expect(buildRouteTabs([path('A1'), path('B2')]).map(t => t.label)).toEqual(['Via A1', 'Via B2'])
    })

    it('falls back to Route N for the whole colliding group', () => {
        const tabs = buildRouteTabs([path('A1'), path('A1'), path('B2')])
        expect(tabs.map(t => t.label)).toEqual(['Route 1', 'Route 2', 'Via B2'])
    })

    it('falls back to Route N for empty and whitespace-only descriptions', () => {
        expect(buildRouteTabs([path(''), path('   ')]).map(t => t.label)).toEqual(['Route 1', 'Route 2'])
    })

    it('mixes unique, colliding and empty descriptions', () => {
        const tabs = buildRouteTabs([path('A1'), path(''), path('B2'), path('B2')])
        expect(tabs.map(t => t.label)).toEqual(['Via A1', 'Route 2', 'Route 3', 'Route 4'])
    })

    it('keeps the index and the path on each tab', () => {
        const paths = [path('A1'), path('B2')]
        const tabs = buildRouteTabs(paths)
        expect(tabs.map(t => t.index)).toEqual([0, 1])
        expect(tabs[1].path).toBe(paths[1])
    })
})

describe('buildRouteTabs detail', () => {
    const timed = (description: string, time: number): Path => ({ description, time }) as Path

    it('reads the travel time and the maximum depth in centimetres', () => {
        const tabs = buildRouteTabs([timed('A1', 14 * 60000), timed('B2', 65 * 60000)], [22, 0])
        expect(tabs.map(t => [t.label, t.detail])).toEqual([
            ['Via A1', '14 min \u00b7 22 cm'],
            ['Via B2', '1 h 5 min \u00b7 0 cm'],
        ])
    })

    it('shows the time alone while the depth is unknown, for a missing or a failed answer', () => {
        const tabs = buildRouteTabs([timed('A1', 14 * 60000), timed('B2', 14 * 60000), timed('C3', 14 * 60000)], [null])
        expect(tabs.map(t => t.detail)).toEqual(['14 min', '14 min', '14 min'])
    })

    it('keeps Route N when the description is missing', () => {
        const [tab] = buildRouteTabs([timed('', 5 * 60000)], [7])
        expect([tab.label, tab.detail]).toEqual(['Route 1', '5 min \u00b7 7 cm'])
    })
})

describe('buildRouteTabs with a description the backend sends as a list', () => {
    // GraphHopper answers `"description": ["Đường Hoàng Tùng"]`. Reading that as a string threw
    // "trim is not a function" and blanked the whole app.
    const listPath = (description: unknown): Path => ({ description }) as Path

    it('labels the tab with the text of the list', () => {
        expect(buildRouteTabs([listPath(['Đường Hoàng Tùng'])]).map(t => t.label)).toEqual(['Via Đường Hoàng Tùng'])
    })

    it('joins a list of several names', () => {
        expect(buildRouteTabs([listPath(['Phố A', 'Phố B'])]).map(t => t.label)).toEqual(['Via Phố A, Phố B'])
    })

    it('falls back to Route N for an empty list and for a value that is not text', () => {
        const tabs = buildRouteTabs([listPath([]), listPath(42), listPath({}), listPath(null)])
        expect(tabs.map(t => t.label)).toEqual(['Route 1', 'Route 2', 'Route 3', 'Route 4'])
    })

    it('still gives a colliding pair of lists Route N', () => {
        const tabs = buildRouteTabs([listPath(['via A1']), listPath(['via A1'])])
        expect(tabs.map(t => t.label)).toEqual(['Route 1', 'Route 2'])
    })
})

describe('activeTabIndex', () => {
    it('finds the selected path by reference', () => {
        const paths = [path('a'), path('b')]
        expect(activeTabIndex(paths, paths[1])).toEqual(1)
    })

    it('falls back to 0 for a stale reference', () => {
        expect(activeTabIndex([path('a')], path('a'))).toEqual(0)
    })
})

describe('selectRoutingResultsView', () => {
    it('is idle before any request', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [] },
        })
        expect(view.kind).toEqual('idle')
    })

    it('is loading while a request is pending with no paths yet', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [sent()] },
        })
        expect(view.kind).toEqual('loading')
    })

    it('is timedOut once every request settled and one of them timed out', () => {
        const timedOut: SubRequest = { args: {} as any, state: RequestState.FAILED, timedOut: true }
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [timedOut, timedOut] },
        })
        expect(view.kind).toEqual('timedOut')
    })

    it('stays loading while the other request of a pair is still pending', () => {
        const timedOut: SubRequest = { args: {} as any, state: RequestState.FAILED, timedOut: true }
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [timedOut, sent()] },
        })
        expect(view.kind).toEqual('loading')
    })

    it('prefers the no-connection answer over a timeout of the other request', () => {
        const noConnection: SubRequest = { args: {} as any, state: RequestState.FAILED, noConnection: true }
        const timedOut: SubRequest = { args: {} as any, state: RequestState.FAILED, timedOut: true }
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [noConnection, timedOut] },
        })
        expect(view.kind).toEqual('empty')
    })

    it('is empty once a request settled with zero paths', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [done()] },
        })
        expect(view.kind).toEqual('empty')
    })

    it('is routes, with the selected tab active', () => {
        const paths = [path('A1'), path('B2')]
        const view = selectRoutingResultsView({
            paths,
            selectedPath: paths[1],
            allPointsSet: true,
            currentRequest: { subRequests: [done()] },
        })
        expect(view).toEqual({
            kind: 'routes',
            tabs: buildRouteTabs(paths),
            activeIndex: 1,
        })
    })

    it('keeps showing routes while further alternatives are still pending', () => {
        const paths = [path('A1')]
        const view = selectRoutingResultsView({
            paths,
            selectedPath: paths[0],
            allPointsSet: true,
            currentRequest: { subRequests: [done(), sent()] },
        })
        expect(view.kind).toEqual('routes')
    })

    it('prefers loading over empty when a settled and a pending request coexist', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: true,
            currentRequest: { subRequests: [done(), sent()] },
        })
        expect(view.kind).toEqual('loading')
    })

    it('is idle when a point is empty, although sub requests from an earlier route remain', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            allPointsSet: false,
            currentRequest: { subRequests: [done()] },
        })
        expect(view.kind).toEqual('idle')
    })
})

describe('parseRouteKinds', () => {
    it('reads one kind per path in path order', () => {
        expect(parseRouteKinds('recommended,through_water', 2)).toEqual(['recommended', 'through_water'])
        expect(parseRouteKinds('through_water', 1)).toEqual(['through_water'])
    })

    it('reads nothing when the hint is missing, unknown, or does not match the number of paths', () => {
        expect(parseRouteKinds(undefined, 1)).toBeNull()
        expect(parseRouteKinds('recommended', 2)).toBeNull()
        expect(parseRouteKinds('recommended,fastest', 2)).toBeNull()
        expect(parseRouteKinds('', 1)).toBeNull()
    })
})

describe('buildRouteTabs with the kinds of the backend answer', () => {
    const timed = (minutes: number): Path =>
        ({ description: ['Phố Nguyễn Văn Giáp'], time: minutes * 60000 }) as unknown as Path
    const hints = { 'td.limit_cm': 35, 'td.precaution_cm': 18, 'td.kinds': 'recommended,through_water' }

    it('puts the recommended route first and the through-water route second, with its label and its deepest road', () => {
        const tabs = buildRouteTabs([timed(14), timed(9)], [3, 22], hints)
        expect(tabs.map(t => [t.label, t.detail, t.kind])).toEqual([
            ['Recommended', '14 min \u00b7 3 cm', 'recommended'],
            ['Through water', '9 min \u00b7 22 cm', 'through_water'],
        ])
        expect(tabs.map(t => t.note)).toEqual([
            null,
            'Passes through water between 18 cm and 35 cm deep. Deepest road 22 cm.',
        ])
    })

    it('leaves out the deepest road while the depth is unknown', () => {
        const tabs = buildRouteTabs([timed(14), timed(9)], [], hints)
        expect(tabs[1].note).toBe('Passes through water between 18 cm and 35 cm deep.')
    })

    it('keeps the old labels for one recommended route', () => {
        const [tab] = buildRouteTabs([timed(14)], [], { ...hints, 'td.kinds': 'recommended' })
        expect([tab.label, tab.note]).toEqual(['Via Phố Nguyễn Văn Giáp', null])
    })

    it('labels a single limit route as through water', () => {
        const [tab] = buildRouteTabs([timed(14)], [20], { ...hints, 'td.kinds': 'through_water' })
        expect([tab.label, tab.note]).toEqual([
            'Through water',
            'Passes through water between 18 cm and 35 cm deep. Deepest road 20 cm.',
        ])
    })

    it('keeps the old labels when the answer has no kinds', () => {
        const tabs = buildRouteTabs([timed(14), timed(9)], [], { 'td.limit_cm': 35 })
        expect(tabs.map(t => [t.label, t.kind, t.note])).toEqual([
            ['Route 1', null, null],
            ['Route 2', null, null],
        ])
    })
})
