import { Path } from '@/api/graphhopper'
import { RequestState, SubRequest } from '@/stores/QueryStore'
import { activeTabIndex, buildRouteTabs, selectRoutingResultsView } from '@/sidebar/routingResultsView'

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
