import { floodView, parseFloodMode } from '@/floodmap/floodMode'

// The answer GET /flood/mode gives in DEMO on the server (US-130 details item 2).
const DEMO_ANSWER = {
    mode: 'DEMO',
    decided_at: '2026-10-13T03:30:00+00:00',
    demo: { run: '20261011T001500', valid_time: '2026-10-10T19:00:00+00:00' },
}

describe('parseFloodMode', () => {
    it('reads LIVE and PENDING', () => {
        expect(parseFloodMode({ mode: 'LIVE', decided_at: null, demo: null })).toEqual({ kind: 'LIVE' })
        expect(parseFloodMode({ mode: 'PENDING', decided_at: null, demo: null })).toEqual({ kind: 'PENDING' })
    })

    it('reads the pinned step of DEMO as a +07:00 step, the form the tile folders are named by', () => {
        expect(parseFloodMode(DEMO_ANSWER)).toEqual({
            kind: 'DEMO',
            pinned: { run: '20261011T001500', valid_time: '2026-10-11T02:00:00+07:00' },
        })
    })

    it('reads DEMO with no pinned step', () => {
        expect(parseFloodMode({ mode: 'DEMO', decided_at: null, demo: null })).toEqual({ kind: 'DEMO', pinned: null })
    })

    it('falls back to LIVE for an answer it does not know', () => {
        expect(parseFloodMode({ mode: 'MAYBE' })).toEqual({ kind: 'LIVE' })
        expect(parseFloodMode(null)).toEqual({ kind: 'LIVE' })
    })
})

describe('floodView', () => {
    it('shows no banner and the flood in LIVE', () => {
        expect(floodView({ kind: 'LIVE' })).toEqual({ banner: null, drawFlood: true })
    })

    it('warns that the simulation is running and draws no flood in PENDING', () => {
        expect(floodView({ kind: 'PENDING' })).toEqual({
            banner: 'The flood simulation is running. The map stays dry until it finishes.',
            drawFlood: false,
        })
    })

    it('names the Hanoi date of the pinned step in DEMO, one day after its UTC date', () => {
        expect(floodView(parseFloodMode(DEMO_ANSWER))).toEqual({
            banner: 'No flood forecasted, displaying the demo flood of Oct 11, 2026',
            drawFlood: true,
        })
    })

    it('uses the date of the story when the answer carries no pinned step', () => {
        expect(floodView({ kind: 'DEMO', pinned: null })).toEqual({
            banner: 'No flood forecasted, displaying the demo flood of Sep 16, 2026',
            drawFlood: true,
        })
    })
})
