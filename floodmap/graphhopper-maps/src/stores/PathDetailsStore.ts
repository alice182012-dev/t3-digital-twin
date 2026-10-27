import Store from '@/stores/Store'
import { Action } from '@/stores/Dispatcher'
import { ClearPoints, ClearRoute, PathDetailsElevationSelected } from '@/actions/Actions'
import { Coordinate } from '@/utils'

export interface PathDetailsStoreState {
    pathDetailsHighlightedSegments: Coordinate[][]
}

export default class PathDetailsStore extends Store<PathDetailsStoreState> {
    constructor() {
        super(PathDetailsStore.getInitialState())
    }

    private static getInitialState(): PathDetailsStoreState {
        return {
            pathDetailsHighlightedSegments: [],
        }
    }

    reduce(state: PathDetailsStoreState, action: Action): PathDetailsStoreState {
        if (action instanceof PathDetailsElevationSelected) {
            return {
                // todo: we probably should keep the highlighted segments and elevation when we change the
                //       selected details?! -> need to fix in heightgraph
                ...state,
                pathDetailsHighlightedSegments: action.segments,
            }
        } else if (action instanceof ClearRoute || action instanceof ClearPoints) {
            return PathDetailsStore.getInitialState()
        }
        return state
    }
}
