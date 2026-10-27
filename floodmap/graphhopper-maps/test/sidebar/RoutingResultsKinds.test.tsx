import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import RoutingResults from '@/sidebar/RoutingResults'
import { Path, RoutingHints } from '@/api/graphhopper'
import { RequestState } from '@/stores/QueryStore'
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

function path(minutes: number, km: number): Path {
    return {
        time: minutes * 60000,
        distance: km * 1000,
        description: '',
        ascend: 0,
        descend: 0,
        points: {
            type: 'LineString',
            coordinates: [
                [105.755, 21.025],
                [105.762, 21.0255],
            ],
        },
        instructions: [],
        details: {},
    } as unknown as Path
}

describe('RoutingResults with the two options of the backend', () => {
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

    function render(paths: Path[], selected: number, hints: RoutingHints) {
        act(() =>
            root.render(
                <RoutingResults
                    framed
                    info={{ copyright: [], road_data_timestamp: '', took: 1 }}
                    hints={hints}
                    paths={paths}
                    selectedPath={paths[selected]}
                    currentRequest={{ subRequests: [{ args: {} as any, state: RequestState.SUCCESS }] }}
                    allPointsSet={true}
                    profile="truck"
                />,
            ),
        )
        return {
            tabs: Array.from(container.querySelectorAll('[role="tab"]')).map(tab => tab.textContent),
            text: container.textContent ?? '',
        }
    }

    it('shows the recommended tab first and the through-water tab second, and labels the second one when it is open', () => {
        const paths = [path(14, 2.1), path(9, 1.9)]
        const hints = { 'td.limit_cm': 35, 'td.precaution_cm': 18, 'td.kinds': 'recommended,through_water' }
        const recommended = render(paths, 0, hints)
        expect(recommended.tabs).toEqual(['Recommended14 min', 'Through water9 min'])
        expect(recommended.text).not.toContain('Passes through water')

        const throughWater = render(paths, 1, hints)
        expect(throughWater.text).toContain('Passes through water between 18 cm and 35 cm deep.')
    })

    it('shows one tab and no label for one recommended route', () => {
        const only = render([path(14, 2.1)], 0, {
            'td.limit_cm': 35,
            'td.precaution_cm': 18,
            'td.kinds': 'recommended',
        })
        expect(only.tabs).toEqual(['Route 114 min'])
        expect(only.text).not.toContain('Passes through water')
    })
})
