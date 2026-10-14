import { readFileSync } from 'fs'
import { join } from 'path'

const SRC = join(__dirname, '../../src')

function declaration(cssFile: string, selector: string, property: string): string {
    const css = readFileSync(join(SRC, cssFile), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')
    for (const [, selectors, body] of css.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
        if (!selectors.split(',').some(s => s.trim() === selector)) continue
        const match = body.match(new RegExp(`(?:^|[;\\s])${property}\\s*:\\s*([^;]+);`))
        if (match) return match[1].trim()
    }
    throw new Error(`${selector} sets no ${property} in ${cssFile}`)
}

function luminance(color: string): number {
    const named = color === 'white' ? '#ffffff' : color
    const hex = named.length === 4 ? '#' + [...named.slice(1)].map(c => c + c).join('') : named
    const [r, g, b] = [1, 3, 5]
        .map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
        .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrast(foreground: string, background: string): number {
    const [lighter, darker] = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
    return (lighter + 0.05) / (darker + 0.05)
}

const LEGEND = 'floodmap/FloodLegend.module.css'
const TABS = 'sidebar/RoutingResult.module.css'
const LEGEND_BACKGROUND = declaration(LEGEND, '.container', 'background')

describe('text contrast', () => {
    it('measures known pairs with the WCAG formula', () => {
        expect(contrast('#000000', '#ffffff')).toBeCloseTo(21, 5)
        expect(contrast('#6b7280', '#ffffff')).toBeCloseTo(4.83, 2)
    })

    const pairs: [string, string, string][] = [
        ['legend title', declaration(LEGEND, '.title', 'color'), LEGEND_BACKGROUND],
        ['legend tick label', declaration(LEGEND, '.ticks', 'color'), LEGEND_BACKGROUND],
        ['legend updated line', declaration(LEGEND, '.updated', 'color'), LEGEND_BACKGROUND],
        [
            'inactive route tab',
            declaration(TABS, '.routeTab', 'color'),
            declaration(TABS, '.routeTab', 'background-color'),
        ],
        [
            'inactive route tab on hover',
            declaration(TABS, '.routeTab', 'color'),
            declaration(TABS, '.routeTab:hover', 'background-color'),
        ],
        [
            'active route tab',
            declaration(TABS, '.routeTabActive', 'color'),
            declaration(TABS, '.routeTabActive', 'background-color'),
        ],
    ]

    it.each(pairs)('%s is at least 4.5:1', (_name, foreground, background) => {
        expect(contrast(foreground, background)).toBeGreaterThanOrEqual(4.5)
    })
})
