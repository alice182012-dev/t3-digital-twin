import { useEffect, useState } from 'react'
import {
    FloodStoreState,
    getFloodStore,
    loadFloodTimesteps,
    reissueCurrentRoute,
    TIMESTEP_REFRESH_INTERVAL_MS,
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
 * Owns the flood data lifecycle: loads the timesteps that both the map's flood layer and routing
 * follow, and re-issues the current route when the timestep or vehicle changes.
 */
export function useFloodBootstrap(): void {
    const { selectedIndex, vehicleType, timesteps } = useFloodState()

    // Refetching (not just re-picking from the existing list) is deliberate: a session left open
    // past FRESH_DATA_WINDOW_MS needs the newer run a fresh fetch would surface, not just a
    // different index into data that's already stale.
    useEffect(() => {
        loadFloodTimesteps()
        const id = setInterval(loadFloodTimesteps, TIMESTEP_REFRESH_INTERVAL_MS)
        return () => clearInterval(id)
    }, [])

    useEffect(() => {
        if (selectedIndex < 0 || timesteps.length === 0) return
        reissueCurrentRoute()
    }, [selectedIndex, vehicleType, timesteps])
}
