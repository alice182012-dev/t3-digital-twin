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

// Keeps its own FloodStore subscription rather than taking `areas` as a prop: `areas` is bulk
// GeoJSON that App has no use for, and routing it through App's render tree on every timestep
// change is real, avoidable cost. App and this hook read disjoint slices of one store.
//
// `visible` is separate from "is there data" on purpose: an empty FeatureCollection in Flood mode
// is a real answer (no flooding at this step), not the same thing as the overlay being off.
export default function useFloodLayer(map: Map, visible: boolean) {
    const [areas, setAreas] = useState(getFloodStore().state.areas)
    useEffect(() => {
        const onChange = () => setAreas(getFloodStore().state.areas)
        getFloodStore().register(onChange)
        return () => getFloodStore().deregister(onChange)
    }, [])

    useEffect(() => {
        removeFloodLayer(map)
        if (visible && areas && areas.features.length > 0) addFloodLayer(map, areas)
        return () => removeFloodLayer(map)
    }, [map, areas, visible])
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
