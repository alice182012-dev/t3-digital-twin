import Store from '@/stores/Store'
import { Action } from '@/stores/Dispatcher'
import { DismissLastError, ErrorAction, RouteRequestFailed, RouteRequestSuccess } from '@/actions/Actions'

export interface ErrorStoreState {
    lastError: string
    isDismissed: boolean
}

export default class ErrorStore extends Store<ErrorStoreState> {
    constructor() {
        super(ErrorStore.getInitialState())
    }

    private static getInitialState(): ErrorStoreState {
        return {
            isDismissed: true,
            lastError: '',
        }
    }

    reduce(state: ErrorStoreState, action: Action): ErrorStoreState {
        if (action instanceof RouteRequestFailed && (action.noConnection || action.timedOut)) {
            // The panel's box carries these cases, and an earlier error is out of date.
            return state.isDismissed ? state : { ...state, isDismissed: true }
        } else if (action instanceof ErrorAction) {
            return {
                lastError: action.message,
                isDismissed: false,
            }
        } else if (action instanceof DismissLastError || action instanceof RouteRequestSuccess) {
            if (state.isDismissed) return state
            return {
                ...state,
                isDismissed: true,
            }
        }
        return state
    }
}
