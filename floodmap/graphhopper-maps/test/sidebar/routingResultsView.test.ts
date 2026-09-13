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
        expect(buildRouteTabs([path('via A1'), path('via B2')]).map(t => t.label)).toEqual(['via A1', 'via B2'])
    })

    it('falls back to Route N for the whole colliding group', () => {
        const tabs = buildRouteTabs([path('via A1'), path('via A1'), path('via B2')])
        expect(tabs.map(t => t.label)).toEqual(['Route 1', 'Route 2', 'via B2'])
    })

    it('falls back to Route N for empty and whitespace-only descriptions', () => {
        expect(buildRouteTabs([path(''), path('   ')]).map(t => t.label)).toEqual(['Route 1', 'Route 2'])
    })

    it('mixes unique, colliding and empty descriptions', () => {
        const tabs = buildRouteTabs([path('via A1'), path(''), path('via B2'), path('via B2')])
        expect(tabs.map(t => t.label)).toEqual(['via A1', 'Route 2', 'Route 3', 'Route 4'])
    })

    it('keeps the index and the path on each tab', () => {
        const paths = [path('via A1'), path('via B2')]
        const tabs = buildRouteTabs(paths)
        expect(tabs.map(t => t.index)).toEqual([0, 1])
        expect(tabs[1].path).toBe(paths[1])
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
            currentRequest: { subRequests: [] },
        })
        expect(view.kind).toEqual('idle')
    })

    it('is loading while a request is pending with no paths yet', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            currentRequest: { subRequests: [sent()] },
        })
        expect(view.kind).toEqual('loading')
    })

    it('is empty once a request settled with zero paths', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            currentRequest: { subRequests: [done()] },
        })
        expect(view.kind).toEqual('empty')
    })

    it('is routes, with the selected tab active', () => {
        const paths = [path('via A1'), path('via B2')]
        const view = selectRoutingResultsView({
            paths,
            selectedPath: paths[1],
            currentRequest: { subRequests: [done()] },
        })
        expect(view).toEqual({
            kind: 'routes',
            tabs: buildRouteTabs(paths),
            activeIndex: 1,
        })
    })

    it('keeps showing routes while further alternatives are still pending', () => {
        const paths = [path('via A1')]
        const view = selectRoutingResultsView({
            paths,
            selectedPath: paths[0],
            currentRequest: { subRequests: [done(), sent()] },
        })
        expect(view.kind).toEqual('routes')
    })

    it('prefers loading over empty when a settled and a pending request coexist', () => {
        const view = selectRoutingResultsView({
            paths: [],
            selectedPath: path(),
            currentRequest: { subRequests: [done(), sent()] },
        })
        expect(view.kind).toEqual('loading')
    })
})
