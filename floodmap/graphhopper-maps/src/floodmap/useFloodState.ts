import { useEffect, useState } from 'react'
import {
    FloodStoreState,
    getFloodStore,
    loadFloodTimesteps,
    reissueCurrentRoute,
} from '@/floodmap/FloodStore'

/**
 * The single App-level subscription to FloodStore. It returns the whole state; the view-model
 * derivations live in floodSelectors and are called where they are needed, so this hook holds no
 * policy and has nothing to keep in sync.
 */
export function useFloodState(): FloodStoreState {
    const [state, setState] = useState(getFloodStore().state)
    useEffect(() => {
        const onChange = () => setState(getFloodStore().state)
        getFloodStore().register(onChange)
        onChange()
        return () => getFloodStore().deregister(onChange)
    }, [])
    return state
}

/**
 * Owns the flood data lifecycle: loads the timesteps routing derives its flood costs from, and
 * re-issues the current route when the timestep or vehicle changes. The map's flood layer does not
 * use these timesteps (see FloodExtentLayer).
 */
export function useFloodBootstrap(): void {
    const { selectedIndex, vehicleType, timesteps } = useFloodState()

    useEffect(() => {
        loadFloodTimesteps()
    }, [])

    useEffect(() => {
        if (selectedIndex < 0 || timesteps.length === 0) return
        reissueCurrentRoute()
    }, [selectedIndex, vehicleType, timesteps])
}
