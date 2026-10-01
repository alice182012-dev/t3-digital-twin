import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import RouteTabs from '@/sidebar/RouteTabs'
import { RouteTab } from '@/sidebar/routingResultsView'
import { Path } from '@/api/graphhopper'

// Lets act() flush effects and updates without the "not configured to support act" warning.
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

const tabs: RouteTab[] = ['Route 1', 'Route 2', 'Route 3'].map((label, index) => ({
    index,
    label,
    path: {} as Path,
}))

describe('RouteTabs', () => {
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

    function render(activeIndex: number, onSelect: (index: number) => void) {
        act(() => root.render(<RouteTabs tabs={tabs} activeIndex={activeIndex} onSelect={onSelect} />))
        return Array.from(container.querySelectorAll<HTMLButtonElement>('[role="tab"]'))
    }

    it('selects and focuses the next tab on ArrowRight', () => {
        const selected: number[] = []
        const buttons = render(0, index => selected.push(index))
        buttons[0].focus()

        act(() => {
            buttons[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
        })

        expect(selected).toEqual([1])
        expect(document.activeElement?.textContent).toBe('Route 2')
    })

    it('wraps from the first tab to the last on ArrowLeft', () => {
        const selected: number[] = []
        const buttons = render(0, index => selected.push(index))

        act(() => {
            buttons[0].dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }))
        })

        expect(selected).toEqual([2])
        expect(document.activeElement?.textContent).toBe('Route 3')
    })

    it('keeps only the selected tab in the tab order', () => {
        const buttons = render(1, () => {})
        expect(buttons.map(b => b.tabIndex)).toEqual([-1, 0, -1])
    })
})
