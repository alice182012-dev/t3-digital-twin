import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import FloodLegend from '@/floodmap/FloodLegend'
import { legendGradient, legendTicks } from '@/floodmap/depthScale'
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

describe('legendTicks', () => {
    it('puts a tick at the lower limit of every band and one for the open-ended band, 24 px apart', () => {
        expect(legendTicks()).toEqual([
            { label: '5 cm', topPx: 0 },
            { label: '10 cm', topPx: 24 },
            { label: '20 cm', topPx: 48 },
            { label: '30 cm', topPx: 72 },
            { label: '40 cm', topPx: 96 },
            { label: '50 cm', topPx: 120 },
            { label: '60 cm', topPx: 144 },
            { label: '> 60 cm', topPx: 168 },
        ])
    })
})

describe('legendGradient', () => {
    it('centres each band colour in its step, as in the mockup', () => {
        expect(legendGradient()).toBe(
            'linear-gradient(to bottom, #deebf7 7%, #c6dbef 21%, #9ecae1 36%, #6baed6 50%, #4292c6 64%, #2171b5 79%, #08306b 93%)',
        )
    })
})

describe('FloodLegend', () => {
    let container: HTMLDivElement
    let root: Root

    beforeEach(() => {
        container = document.createElement('div')
        document.body.appendChild(container)
        root = createRoot(container)
    })

    afterEach(() => {
        act(() => root.unmount())
        container.remove()
    })

    it('shows the title, the gradient bar, and the eight tick labels', async () => {
        await act(async () => root.render(<FloodLegend timestep={undefined} />))
        expect(container.textContent).toBe('Flood depth5 cm10 cm20 cm30 cm40 cm50 cm60 cm> 60 cm')
        const bar = container.querySelector<HTMLElement>('.bar')
        expect(bar?.style.background).toContain('linear-gradient(to bottom')
        expect(container.querySelectorAll('.tick')).toHaveLength(8)
    })

    it('adds the caption of the shown step under the scale', async () => {
        const timestep = { valid_time: '2026-10-10T19:00:00+00:00', run: '20261011T001500' }
        await act(async () => root.render(<FloodLegend timestep={timestep} />))
        expect(container.querySelector('.updated')?.textContent).toMatch(/^As of \d\d\/\d\d\/2026 \d\d:\d\d$/)
    })
})
