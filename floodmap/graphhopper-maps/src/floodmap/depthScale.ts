/**
 * Display water-depth palette. Used by FloodLegend, and mirrored exactly (same cm edges, same
 * hex values converted to RGB) by the raster tile layer's colors in
 * backend/tiles.py's DISPLAY_DEPTH_BANDS_CM — the map's own paint has to match what the legend
 * promises. Deliberately a different scale from the routing-cost bands in
 * scripts/flood_utils.py's DEPTH_BANDS, which answer a different question: those bands
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

/** Ascending by depth, ascending in colour intensity. d7 keeps the approved mockup's
 *  (artifacts/designs/mockups/Flood Routing Mockups v2.dc.html) deepest color; d1 through d6
 *  are a deliberate linear interpolation from the mockup's lightest color, not copied from any
 *  QGIS-generated gradient. The mockup itself still shows the old 5-band legend and needs its
 *  own redesign pass. Depths under 5 cm are not painted, matching the 0 code in
 *  scripts/flood_extent/flood_extent.py. */
export const DISPLAY_DEPTH_BANDS: readonly DepthBand[] = [
    { id: 'd1', minCm: 5, maxCm: 10, label: '5–10 cm', color: '#b5cce6' },
    { id: 'd2', minCm: 10, maxCm: 20, label: '10–20 cm', color: '#9ab4d5' },
    { id: 'd3', minCm: 20, maxCm: 30, label: '20–30 cm', color: '#809dc4' },
    { id: 'd4', minCm: 30, maxCm: 40, label: '30–40 cm', color: '#6585b3' },
    { id: 'd5', minCm: 40, maxCm: 50, label: '40–50 cm', color: '#4b6ea2' },
    { id: 'd6', minCm: 50, maxCm: 60, label: '50–60 cm', color: '#305691' },
    { id: 'd7', minCm: 60, maxCm: null, label: '> 60 cm', color: '#163f80' },
]

/** Maps a `DN` code from scripts/flood_extent/flood_extent.py's `BAND_TABLE` to its display
 *  band. Codes 10 to 60 are the band's upper limit in cm, and `TOP_CODE` (600) is the open-ended
 *  band. Returns undefined for 0 (dry) and for any code the notebook doesn't emit. */
export function bandForExtentCode(code: number): DepthBand | undefined {
    if (code === 600) return DISPLAY_DEPTH_BANDS.find(band => band.maxCm === null)
    return DISPLAY_DEPTH_BANDS.find(band => band.maxCm === code)
}
