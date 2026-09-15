import { useEffect, useState } from 'react'
import {
    FloodStoreState,
    getFloodStore,
    loadFloodRuns,
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
 * Owns the flood data lifecycle. App mounts it unconditionally, so timestep loading and route
 * re-issuing no longer depend on TimeSlider being mounted. TimeSlider keeps its own copy of the
 * route-reissue effect because it stays untouched as a local testing tool; both are idempotent
 * for the same (index, vehicleType), so the overlap is a redundant reissue, not a wrong state.
 *
 * No `loadFloodAreas` call here: the raster tile layer (FloodLayer.tsx) reads depth-colored PNGs
 * straight off the backend keyed by timestep, it doesn't need the polygon GeoJSON that endpoint
 * returns.
 */
export function useFloodBootstrap(): void {
    const { selectedIndex, vehicleType, timesteps, selectedRun } = useFloodState()

    useEffect(() => {
        loadFloodRuns()
    }, [])

    // Keyed on selectedRun (not `[]`): fires on mount (selectedRun starts null, i.e. "latest")
    // and again whenever TimeSlider's run picker changes it, so switching runs actually refetches
    // instead of leaving the previous run's timesteps in the store under a new selectedRun.
    useEffect(() => {
        loadFloodTimesteps()
    }, [selectedRun])

    useEffect(() => {
        if (selectedIndex < 0 || timesteps.length === 0) return
        reissueCurrentRoute()
    }, [selectedIndex, vehicleType, timesteps])
}
