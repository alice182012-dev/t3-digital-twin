import { Map } from 'ol'
import { useEffect, useRef } from 'react'
import VectorTileLayer from 'ol/layer/VectorTile'
import VectorTileSource from 'ol/source/VectorTile'
import { MVT } from 'ol/format'
import { Fill, Style } from 'ol/style'
import { bandForExtentCode, DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'
import { floodExtentOverrideUrl, floodExtentTilesUrl } from '@/floodmap/floodExtentTiles'
import type { FloodTimestep } from '@/floodmap/FloodStore'

// The flood layer is drawn from scripts/flood_extent/flood_extent.py's tiles for the selected
// timestep, served from the frontend's own /flood-extent/ folder (see floodExtentTiles.ts).

const fillOpacity = 0.75

// Read once, when the module loads: the app rewrites the address's query string as the query changes.
const overrideUrl = typeof window === 'undefined' ? undefined : floodExtentOverrideUrl(window.location.search)

function styleByBandId() {
    const styles: Record<string, Style> = {}
    for (const band of DISPLAY_DEPTH_BANDS) {
        const rgb = band.color.match(/[0-9a-f]{2}/gi)!.map(hex => parseInt(hex, 16))
        const color = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${fillOpacity})`
        styles[band.id] = new Style({ fill: new Fill({ color }) })
    }
    return styles
}

export default function useFloodExtentLayer(map: Map, visible: boolean, timestep: FloodTimestep | undefined) {
    const sourceRef = useRef<VectorTileSource | null>(null)
    const url = overrideUrl ?? (timestep ? floodExtentTilesUrl(timestep) : undefined)
    const urlRef = useRef(url)
    urlRef.current = url
    const hasTimestep = url !== undefined

    // The layer exists while it is visible and there is a timestep to draw.
    useEffect(() => {
        if (!visible || !hasTimestep) return
        const styles = styleByBandId()
        const source = new VectorTileSource({
            format: new MVT(),
            url: urlRef.current,
            minZoom: 10,
            maxZoom: 16,
        })
        const layer = new VectorTileLayer({
            source,
            // Beyond the source's max zoom OpenLayers overzooms tiles; vector mode keeps them sharp.
            renderMode: 'vector',
            zIndex: 2,
            style: feature => {
                const band = bandForExtentCode(feature.get('DN'))
                return band ? styles[band.id] : undefined
            },
        })
        sourceRef.current = source
        map.addLayer(layer)
        return () => {
            sourceRef.current = null
            map.removeLayer(layer)
        }
    }, [map, visible, hasTimestep])

    // Stepping through the timeline re-points the same layer instead of rebuilding it.
    useEffect(() => {
        if (url) sourceRef.current?.setUrl(url)
    }, [url])
}
