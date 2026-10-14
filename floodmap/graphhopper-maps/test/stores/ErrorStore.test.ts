import ErrorStore from '@/stores/ErrorStore'
import Dispatcher from '@/stores/Dispatcher'
import { DismissLastError, ErrorAction, RouteRequestFailed } from '@/actions/Actions'
import { RoutingArgs } from '@/api/graphhopper'

const request = {} as RoutingArgs

function createStore() {
    const store = new ErrorStore()
    Dispatcher.register(store)
    return store
}

describe('ErrorStore', () => {
    afterEach(() => {
        Dispatcher.clear()
    })

    it('shows the message of an error', () => {
        const store = createStore()

        Dispatcher.dispatch(new ErrorAction('Something failed'))

        expect(store.state).toEqual({ lastError: 'Something failed', isDismissed: false })
    })

    it('shows the message of a failed route request', () => {
        const store = createStore()

        Dispatcher.dispatch(new RouteRequestFailed(request, 'Cannot find point 0', false))

        expect(store.state).toEqual({ lastError: 'Cannot find point 0', isDismissed: false })
    })

    it('shows no error bar when the route failed for want of a connection', () => {
        const store = createStore()
        const initial = store.state

        Dispatcher.dispatch(new RouteRequestFailed(request, 'Connection between locations not found', true))

        expect(store.state).toEqual(initial)
    })

    it('shows no error bar when the route timed out, because the panel says so', () => {
        const store = createStore()
        const initial = store.state

        Dispatcher.dispatch(new RouteRequestFailed(request, 'Route request timed out', false, true))

        expect(store.state).toEqual(initial)
    })

    it('hides an earlier error when a route then fails for want of a connection', () => {
        const store = createStore()
        Dispatcher.dispatch(new ErrorAction('Cannot find point 0'))
        expect(store.state.isDismissed).toBe(false)

        Dispatcher.dispatch(new RouteRequestFailed(request, 'Connection between locations not found', true))

        expect(store.state.isDismissed).toBe(true)
    })

    it('can be dismissed', () => {
        const store = createStore()
        Dispatcher.dispatch(new ErrorAction('Something failed'))

        Dispatcher.dispatch(new DismissLastError())

        expect(store.state.isDismissed).toBe(true)
    })
})
