import { act } from 'react'
import { createRoot, Root } from 'react-dom/client'
import Autocomplete, { GeocodingItem } from '@/sidebar/search/AddressInputAutocomplete'
;(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true

const bbox: [number, number, number, number] = [0, 0, 0, 0]
const point = { lat: 21, lng: 105.7 }

describe('Autocomplete geocoding rows', () => {
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

    function render(items: GeocodingItem[], query: string, onSelect: (item: unknown) => void = () => {}) {
        act(() =>
            root.render(<Autocomplete items={items} highlightedItem={items[0]} onSelect={onSelect} query={query} />),
        )
        return Array.from(container.querySelectorAll<HTMLButtonElement>('button'))
    }

    it('bolds only the matched part of the name, in the order of the backend', () => {
        const rows = render(
            [
                new GeocodingItem('C5 Giảng Võ', 'Hà Nội', point, bbox, 'Ba Đình'),
                new GeocodingItem('C5 Thanh Xuân Bắc', 'Hà Nội', point, bbox, 'Thanh Xuân'),
            ],
            'C5',
        )
        expect(rows.map(r => r.textContent)).toEqual(['C5 Giảng VõBa Đình', 'C5 Thanh Xuân BắcThanh Xuân'])
        expect(rows.map(r => r.querySelector('[class*="matchedText"]')!.textContent)).toEqual(['C5', 'C5'])
    })

    it('keeps the diacritics of a query with diacritics and gives each row a name with the district', () => {
        const rows = render([new GeocodingItem('Hoàn Kiếm', 'Hà Nội', point, bbox, 'Hoàn Kiếm')], 'Hoàn Kiếm')
        expect(rows[0].querySelector('[class*="matchedText"]')!.textContent).toBe('Hoàn Kiếm')
        expect(rows[0].getAttribute('aria-label')).toBe('Hoàn Kiếm, Hoàn Kiếm')
    })

    it('names a row with no district by its name alone and selects it on click', () => {
        const item = new GeocodingItem('Đại Mỗ', 'Hà Nội', point, bbox)
        const selected: unknown[] = []
        const rows = render([item], 'xyz', i => selected.push(i))
        expect(rows[0].getAttribute('aria-label')).toBe('Đại Mỗ')
        expect(rows[0].querySelector('[class*="matchedText"]')).toBeNull()
        act(() => rows[0].click())
        expect(selected).toEqual([item])
    })
})
