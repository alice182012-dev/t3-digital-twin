import { Map } from 'ol'
import { useEffect } from 'react'
import VectorTileLayer from 'ol/layer/VectorTile'
import VectorTileSource from 'ol/source/VectorTile'
import { MVT } from 'ol/format'
import { Fill, Style } from 'ol/style'
import { bandForExtentCode, DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'

// One static extent: scripts/flood_extent/flood_extent.py's output for the default depth raster,
// served from the frontend's own /flood-extent/ folder. It does not follow any timestep.
export const floodExtentTilesUrl = '/flood-extent/{z}/{x}/{y}.pbf'

const fillOpacity = 0.75

function styleByBandId() {
    const styles: Record<string, Style> = {}
    for (const band of DISPLAY_DEPTH_BANDS) {
        const rgb = band.color.match(/[0-9a-f]{2}/gi)!.map(hex => parseInt(hex, 16))
        const color = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${fillOpacity})`
        styles[band.id] = new Style({ fill: new Fill({ color }) })
    }
    return styles
}

export default function useFloodExtentLayer(map: Map, visible: boolean) {
    useEffect(() => {
        if (!visible) return
        const styles = styleByBandId()
        const layer = new VectorTileLayer({
            source: new VectorTileSource({
                format: new MVT(),
                url: floodExtentTilesUrl,
                minZoom: 10,
                maxZoom: 16,
            }),
            // Beyond the source's max zoom OpenLayers overzooms tiles; vector mode keeps them sharp.
            renderMode: 'vector',
            zIndex: 2,
            style: feature => {
                const band = bandForExtentCode(feature.get('DN'))
                return band ? styles[band.id] : undefined
            },
        })
        map.addLayer(layer)
        return () => {
            map.removeLayer(layer)
        }
    }, [map, visible])
}
