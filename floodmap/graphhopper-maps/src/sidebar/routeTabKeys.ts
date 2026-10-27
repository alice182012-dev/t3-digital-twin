/** Index the WAI-ARIA tabs pattern moves to for `key`, wrapping at both ends; null if the key is not a tab key. */
export function routeTabKeyTarget(key: string, activeIndex: number, count: number): number | null {
    if (count === 0) return null
    switch (key) {
        case 'ArrowRight':
        case 'ArrowDown':
            return (activeIndex + 1) % count
        case 'ArrowLeft':
        case 'ArrowUp':
            return (activeIndex - 1 + count) % count
        case 'Home':
            return 0
        case 'End':
            return count - 1
        default:
            return null
    }
}
