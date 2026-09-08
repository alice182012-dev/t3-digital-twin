import { Map } from 'ol'
import { useEffect, useState } from 'react'
import VectorLayer from 'ol/layer/Vector'
import VectorSource from 'ol/source/Vector'
import { GeoJSON } from 'ol/format'
import { Fill, Stroke, Style } from 'ol/style'
import { getFloodStore } from '@/floodmap/FloodStore'

const floodLayerKey = 'floodLayer'

// b2/b3/b4 match backend/flood_utils.py's DEPTH_BANDS — deepest (b4,
// impassable) drawn most opaque.
const BAND_STYLE: Record<string, Style> = {
    b2: new Style({ stroke: new Stroke({ color: '#f5c542', width: 1 }), fill: new Fill({ color: 'rgba(245,197,66,0.35)' }) }),
    b3: new Style({ stroke: new Stroke({ color: '#f57c1f', width: 1 }), fill: new Fill({ color: 'rgba(245,124,31,0.45)' }) }),
    b4: new Style({ stroke: new Stroke({ color: '#d32f2f', width: 1 }), fill: new Fill({ color: 'rgba(211,47,47,0.55)' }) }),
}
const DEFAULT_STYLE = BAND_STYLE.b3

// Self-contained: subscribes to FloodStore itself so callers (App.tsx) only
// need `useFloodLayer(map)`, no store plumbing at the call site.
export default function useFloodLayer(map: Map) {
    const [areas, setAreas] = useState(getFloodStore().state.areas)
    useEffect(() => {
        const onChange = () => setAreas(getFloodStore().state.areas)
        getFloodStore().register(onChange)
        return () => getFloodStore().deregister(onChange)
    }, [])

    useEffect(() => {
        removeFloodLayer(map)
        if (areas && areas.features.length > 0) addFloodLayer(map, areas)
        return () => removeFloodLayer(map)
    }, [map, areas])
}

function addFloodLayer(map: Map, areas: GeoJSON.FeatureCollection) {
    const source = new VectorSource({
        features: new GeoJSON({ featureProjection: 'EPSG:3857' }).readFeatures(areas),
    })
    const layer = new VectorLayer({
        source,
        style: feature => BAND_STYLE[feature.get('band')] || DEFAULT_STYLE,
    })
    layer.set(floodLayerKey, true)
    layer.setZIndex(2)
    map.addLayer(layer)
}

function removeFloodLayer(map: Map) {
    map.getLayers()
        .getArray()
        .filter(l => l.get(floodLayerKey))
        .forEach(l => map.removeLayer(l))
}
