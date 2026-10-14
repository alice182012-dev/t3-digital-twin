import type { FloodTimestep } from '@/floodmap/FloodStore'
import { formatTimestepDate, HANOI_OFFSET_MS } from '@/floodmap/timestepLabel'

/** The answer of GET /flood/mode (backend/flood_mode.py). `pinned` is the demo step, null when none is pinned. */
export type FloodMode = { kind: 'LIVE' } | { kind: 'PENDING' } | { kind: 'DEMO'; pinned: FloodTimestep | null }

export interface FloodView {
    banner: string | null
    drawFlood: boolean
}

/** The backend pins a step in UTC, but the tile folders are named by the +07:00 times of GET /flood/timesteps. */
function toVietnamTime(validTime: string): string {
    return new Date(Date.parse(validTime) + HANOI_OFFSET_MS).toISOString().slice(0, 19) + '+07:00'
}

/** Any answer that is not a well-formed PENDING or DEMO is LIVE, the behavior before the mode existed. */
export function parseFloodMode(answer: any): FloodMode {
    if (answer?.mode === 'PENDING') return { kind: 'PENDING' }
    if (answer?.mode !== 'DEMO') return { kind: 'LIVE' }
    const demo = answer.demo
    if (!demo || Number.isNaN(Date.parse(demo.valid_time))) return { kind: 'DEMO', pinned: null }
    return { kind: 'DEMO', pinned: { run: demo.run, valid_time: toVietnamTime(demo.valid_time) } }
}

// US-131 gives this date in the warning. It is the fallback for a DEMO answer without a pinned step.
const STORY_DEMO_DATE = 'Sep 16, 2026'

export function floodView(mode: FloodMode): FloodView {
    switch (mode.kind) {
        case 'LIVE':
            return { banner: null, drawFlood: true }
        case 'PENDING':
            return {
                banner: 'The flood simulation is running. The map stays dry until it finishes.',
                drawFlood: false,
            }
        case 'DEMO': {
            const date = (mode.pinned && formatTimestepDate(mode.pinned.valid_time)) || STORY_DEMO_DATE
            return { banner: `No flood forecasted, displaying the demo flood of ${date}`, drawFlood: true }
        }
    }
}
