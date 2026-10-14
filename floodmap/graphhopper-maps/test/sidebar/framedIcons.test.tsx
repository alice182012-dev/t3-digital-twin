import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import { framedProfileIcons } from '@/sidebar/search/routingProfiles/framedProfileIcons'
import { FramedStepIcon, stepIconKind } from '@/sidebar/instructions/FramedStepIcon'
import { deepestStepIndexes } from '@/floodmap/placeDepth'
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

describe('framed mode icons', () => {
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

    it('has the outline icon of the mockup for each of the four modes', () => {
        expect(Object.keys(framedProfileIcons)).toEqual(['car', 'motorbike', 'foot', 'truck'])
    })

    it.each(Object.keys(framedProfileIcons))('draws %s as a 30 px outline with a 1.75 stroke', name => {
        const Icon = framedProfileIcons[name]
        act(() => root.render(<Icon />))
        const svg = container.querySelector('svg')!
        expect(svg.getAttribute('width')).toBe('30')
        expect(svg.getAttribute('height')).toBe('30')
        expect(svg.getAttribute('stroke-width')).toBe('1.75')
        expect(svg.getAttribute('fill')).toBe('none')
        expect(svg.getAttribute('stroke')).toBe('currentColor')
    })

    it('draws a step icon as a 20 px svg without a text alternative', () => {
        act(() => root.render(<FramedStepIcon sign={2} isFirst={false} />))
        const svg = container.querySelector('svg')!
        expect(svg.getAttribute('width')).toBe('20')
        expect(svg.getAttribute('aria-hidden')).toBe('true')
    })
})

describe('stepIconKind', () => {
    it('gives the first row the origin pin and the destination sign the red pin', () => {
        expect(stepIconKind(0, true)).toBe('origin')
        expect(stepIconKind(4, false)).toBe('destination')
    })

    it('points left turns and u-turns left, right turns right, and anything else ahead', () => {
        expect([-3, -2, -1, -7, -8, -98].map(sign => stepIconKind(sign, false))).toEqual(Array(6).fill('left'))
        expect([1, 2, 3, 7, 8].map(sign => stepIconKind(sign, false))).toEqual(Array(5).fill('right'))
        expect([0, 6, -6, 9, 101].map(sign => stepIconKind(sign, false))).toEqual(Array(5).fill('ahead'))
    })
})

describe('deepestStepIndexes', () => {
    it('marks the deepest step, as the bold 22 cm of screen 2e', () => {
        const readings = [
            { kind: 'wet', depthCm: 8 },
            { kind: 'wet', depthCm: 22 },
            { kind: 'wet', depthCm: 5 },
            { kind: 'dry' },
            undefined,
        ] as const
        expect([...deepestStepIndexes(readings)]).toEqual([1])
    })

    it('marks every step that shares the deepest depth', () => {
        const readings = [
            { kind: 'wet', depthCm: 12 },
            { kind: 'wet', depthCm: 12 },
        ] as const
        expect([...deepestStepIndexes(readings)]).toEqual([0, 1])
    })

    it('marks nothing on a dry route or while the readings are in flight', () => {
        expect(deepestStepIndexes([{ kind: 'dry' }, { kind: 'no_data' }]).size).toBe(0)
        expect(deepestStepIndexes([undefined, undefined]).size).toBe(0)
    })
})
