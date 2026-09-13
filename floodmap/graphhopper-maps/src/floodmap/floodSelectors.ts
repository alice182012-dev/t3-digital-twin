import { FloodStoreState } from '@/floodmap/FloodStore'

/**
 * How far the viewed timestep sits from the newest one in the list. This depends on invariant I2
 * (one run per list): with a cross-run composite, "latest" is not a single forecast series and
 * stepsBehind means nothing.
 */
export interface ForecastRecency {
    /** timesteps.length - 1 - selectedIndex, clamped to >= 0. Zero means viewing the newest step. */
    stepsBehind: number
    isLatest: boolean
    /** Human label for the viewed step, e.g. "14:30". Empty when there is no selection. */
    validTimeLabel: string
}

export function selectForecastRecency(state: FloodStoreState): ForecastRecency {
    const { timesteps, selectedIndex } = state
    const step = timesteps[selectedIndex]
    if (!step) return { stepsBehind: 0, isLatest: true, validTimeLabel: '' }

    const stepsBehind = Math.max(timesteps.length - 1 - selectedIndex, 0)
    const parsed = Date.parse(step.valid_time)
    const validTimeLabel = Number.isNaN(parsed)
        ? ''
        : new Date(parsed).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    return { stepsBehind, isLatest: stepsBehind === 0, validTimeLabel }
}
