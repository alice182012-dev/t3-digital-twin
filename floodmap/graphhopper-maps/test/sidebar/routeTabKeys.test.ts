import { routeTabKeyTarget } from '@/sidebar/routeTabKeys'

describe('routeTabKeyTarget', () => {
    it('moves to the next tab on ArrowRight and ArrowDown', () => {
        expect(routeTabKeyTarget('ArrowRight', 0, 3)).toBe(1)
        expect(routeTabKeyTarget('ArrowDown', 1, 3)).toBe(2)
    })

    it('moves to the previous tab on ArrowLeft and ArrowUp', () => {
        expect(routeTabKeyTarget('ArrowLeft', 2, 3)).toBe(1)
        expect(routeTabKeyTarget('ArrowUp', 1, 3)).toBe(0)
    })

    it('wraps past either end', () => {
        expect(routeTabKeyTarget('ArrowRight', 2, 3)).toBe(0)
        expect(routeTabKeyTarget('ArrowLeft', 0, 3)).toBe(2)
    })

    it('jumps to the first tab on Home and the last on End', () => {
        expect(routeTabKeyTarget('Home', 2, 3)).toBe(0)
        expect(routeTabKeyTarget('End', 0, 3)).toBe(2)
    })

    it('stays on the only tab when there is one', () => {
        expect(routeTabKeyTarget('ArrowRight', 0, 1)).toBe(0)
        expect(routeTabKeyTarget('ArrowLeft', 0, 1)).toBe(0)
    })

    it('ignores other keys and an empty strip', () => {
        expect(routeTabKeyTarget('Enter', 0, 3)).toBeNull()
        expect(routeTabKeyTarget('a', 1, 3)).toBeNull()
        expect(routeTabKeyTarget('ArrowRight', 0, 0)).toBeNull()
        expect(routeTabKeyTarget('ArrowRight', 0, 3)).toBe(1)
    })
})
