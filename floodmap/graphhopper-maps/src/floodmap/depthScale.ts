/**
 * Display-only water-depth palette for FloodLegend. Deliberately a different scale from the
 * routing-cost bands in scripts/flood_utils.py's DEPTH_BANDS, which answer a different question.
 *
 * Those bands (b2/b3/b4) are fractions of the vehicle's wading threshold, because what matters for
 * routing is whether this vehicle can pass. What matters for a human reading a map is absolute
 * depth. The id namespaces are kept disjoint ('d1'..'d5' vs 'b2'..'b4') so indexing FloodLayer's
 * BAND_STYLE with a DepthBandId, or this table with a feature's `band` property, is a type error
 * rather than a silent wrong color.
 */
export type DepthBandId = 'd1' | 'd2' | 'd3' | 'd4' | 'd5'

export interface DepthBand {
    readonly id: DepthBandId
    readonly minCm: number
    /** null means open-ended (the ">60 cm" band). */
    readonly maxCm: number | null
    readonly label: string
    readonly color: string
}

/** Ascending by depth, ascending in colour intensity. Exact hex values from the approved
 *  mockup (artifacts/designs/mockups/Flood Routing Mockups v2.dc.html, legend swatches). */
export const DISPLAY_DEPTH_BANDS: readonly DepthBand[] = [
    { id: 'd1', minCm: 1, maxCm: 5, label: '1–5 cm', color: '#cfe3f7' },
    { id: 'd2', minCm: 5, maxCm: 10, label: '5–10 cm', color: '#9ec5ec' },
    { id: 'd3', minCm: 10, maxCm: 30, label: '10–30 cm', color: '#5d9ad9' },
    { id: 'd4', minCm: 30, maxCm: 60, label: '30–60 cm', color: '#2f6fbf' },
    { id: 'd5', minCm: 60, maxCm: null, label: '> 60 cm', color: '#163f80' },
]
