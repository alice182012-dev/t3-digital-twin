import { useEffect, useState } from 'react'
import {
    FloodStoreState,
    getFloodStore,
    loadFloodAreas,
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
 * Owns the flood data lifecycle. App mounts it unconditionally, so flood data no longer depends on
 * TimeSlider being mounted. TimeSlider keeps its own copy of the areas effect because it stays
 * untouched as a local testing tool; both are idempotent for the same (index, vehicleType), so the
 * overlap is a redundant fetch rather than a wrong state.
 */
export function useFloodBootstrap(): void {
    const { selectedIndex, vehicleType, timesteps } = useFloodState()

    useEffect(() => {
        loadFloodTimesteps()
    }, [])

    useEffect(() => {
        if (selectedIndex < 0 || timesteps.length === 0) return
        loadFloodAreas(selectedIndex, vehicleType)
        reissueCurrentRoute()
    }, [selectedIndex, vehicleType, timesteps])
}
