/**
 * Display water-depth palette. Used by FloodLegend, and by the flood-extent vector tile layer
 * (FloodExtentLayer.tsx paints each DN band with the matching color here) — the map's own paint
 * has to match what the legend promises. Deliberately a different scale from the routing-cost
 * bands in scripts/flood_utils.py's DEPTH_BANDS, which answer a different question: those bands
 * (b2/b3/b4) are fractions of the vehicle's wading threshold, because what matters for routing
 * is whether this vehicle can pass, while what matters for a human reading the map is absolute
 * depth. The id namespaces are kept disjoint ('d1'..'d7' vs 'b2'..'b4') so the two are never
 * confused for each other.
 */
export type DepthBandId = 'd1' | 'd2' | 'd3' | 'd4' | 'd5' | 'd6' | 'd7'

export interface DepthBand {
    readonly id: DepthBandId
    readonly minCm: number
    /** null means open-ended (the ">60 cm" band). */
    readonly maxCm: number | null
    readonly label: string
    readonly color: string
}

/** Ascending by depth, ascending in colour intensity. Colors are the reference QML's
 *  (test/waterdepth_steps/waterdepth_steps/depth_20251006_000000.qml) interpolated blue ramp —
 *  a 9-stop ColorBrewer "Blues" sequence — taken in rank order (stop 1 through stop 8) rather
 *  than sampled at the ramp's literal meter values. The QML's own value axis spans 0 to ~4.27 m
 *  (that scene's actual max depth), while this palette's domain is 0.05-0.6+ m, so sampling by
 *  meters would compress six of the seven bands into near-identical pale blues; rank order
 *  instead reuses the ramp's full light-to-dark sequence, one stop per band. Depths under 5 cm
 *  are not painted, matching the 0 code in scripts/flood_extent/flood_extent.py. */
export const DISPLAY_DEPTH_BANDS: readonly DepthBand[] = [
    { id: 'd1', minCm: 5, maxCm: 10, label: '5–10 cm', color: '#deebf7' },
    { id: 'd2', minCm: 10, maxCm: 20, label: '10–20 cm', color: '#c6dbef' },
    { id: 'd3', minCm: 20, maxCm: 30, label: '20–30 cm', color: '#9ecae1' },
    { id: 'd4', minCm: 30, maxCm: 40, label: '30–40 cm', color: '#6baed6' },
    { id: 'd5', minCm: 40, maxCm: 50, label: '40–50 cm', color: '#4292c6' },
    { id: 'd6', minCm: 50, maxCm: 60, label: '50–60 cm', color: '#2171b5' },
    { id: 'd7', minCm: 60, maxCm: null, label: '> 60 cm', color: '#08306b' },
]

/** Rank of each band, so two depths compare by band. */
export const DEPTH_BAND_INDEX: Readonly<Record<DepthBandId, number>> = {
    d1: 0,
    d2: 1,
    d3: 2,
    d4: 3,
    d5: 4,
    d6: 5,
    d7: 6,
}

/** Maps a `DN` code from scripts/flood_extent/flood_extent.py's `BAND_TABLE` to its display
 *  band. Codes 10 to 60 are the band's upper limit in cm, and `TOP_CODE` (600) is the open-ended
 *  band. Returns undefined for 0 (dry) and for any code the notebook doesn't emit. */
export function bandForExtentCode(code: number): DepthBand | undefined {
    if (code === 600) return DISPLAY_DEPTH_BANDS.find(band => band.maxCm === null)
    return DISPLAY_DEPTH_BANDS.find(band => band.maxCm === code)
}

/** The display band of a depth in centimetres. Undefined under 5 cm, which the map does not paint. */
export function bandForDepthCm(depthCm: number): DepthBand | undefined {
    return DISPLAY_DEPTH_BANDS.find(band => depthCm >= band.minCm && (band.maxCm === null || depthCm < band.maxCm))
}

/** One tick of the legend's vertical scale: the label and its offset from the top of the bar. */
export interface LegendTick {
    readonly label: string
    readonly topPx: number
}

/** Distance between two ticks in the legend, as in the mockup (168 px for 7 bands). */
export const LEGEND_TICK_STEP_PX = 24

/** The ticks of the legend, top to bottom: the lower limit of every band, then the open-ended
 *  band's own label. Each band is one step tall, so a band's colour is centred between its
 *  two ticks. */
export function legendTicks(bands: readonly DepthBand[] = DISPLAY_DEPTH_BANDS): LegendTick[] {
    const lowerLimits = bands.map(band => `${band.minCm} cm`)
    const top = bands[bands.length - 1].label
    return [...lowerLimits, top].map((label, i) => ({ label, topPx: i * LEGEND_TICK_STEP_PX }))
}

/** The CSS gradient of the legend bar, top to bottom. Each band's colour sits at the middle of
 *  its step, so the colour of a depth reads against the tick on either side of it. */
export function legendGradient(bands: readonly DepthBand[] = DISPLAY_DEPTH_BANDS): string {
    const stops = bands.map((band, i) => `${band.color} ${Math.round(((i + 0.5) / bands.length) * 100)}%`)
    return `linear-gradient(to bottom, ${stops.join(', ')})`
}
