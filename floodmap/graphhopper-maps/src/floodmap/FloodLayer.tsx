import { Map } from 'ol'
import { useEffect, useRef, useState } from 'react'
import TileLayer from 'ol/layer/Tile'
import XYZ from 'ol/source/XYZ'
import { FloodStoreState, floodTileUrl, getFloodStore } from '@/floodmap/FloodStore'

const floodLayerKey = 'floodLayer'

// Self-contained: subscribes to FloodStore itself for timestep/tilesVisible state, so App.tsx
// only has to pass the one thing it actually owns — MapModeToggle's on/off decision.
//
// `visible` (from MapModeToggle) is separate from `flood.tilesVisible` (TimeSlider's local-dev
// override) on purpose: the product toggle and the dev escape hatch answer different questions,
// and either one being off should hide the layer.
export default function useFloodLayer(map: Map, visible: boolean) {
    const [flood, setFlood] = useState<FloodStoreState>(getFloodStore().state)
    const layerRef = useRef<TileLayer<XYZ> | null>(null)

    useEffect(() => {
        const onChange = () => setFlood(getFloodStore().state)
        getFloodStore().register(onChange)
        return () => getFloodStore().deregister(onChange)
    }, [])

    // The layer outlives every timestep change: depth colouring comes from the
    // backend's rendered PNG, so switching timestep is a URL swap on one
    // source, not the add/remove cycle the old GeoJSON VectorSource needed.
    useEffect(() => {
        const layer = new TileLayer({ source: new XYZ({ crossOrigin: 'anonymous' }), visible: false })
        layer.set(floodLayerKey, true)
        layer.setZIndex(2)
        map.addLayer(layer)
        layerRef.current = layer
        return () => {
            map.removeLayer(layer)
            layerRef.current = null
        }
    }, [map])

    const step = flood.timesteps[flood.selectedIndex]
    useEffect(() => {
        const layer = layerRef.current
        if (!layer) return
        if (step) layer.getSource()?.setUrl(floodTileUrl(step))
        layer.setVisible(visible && flood.tilesVisible && step != null)
    }, [step?.run, step?.valid_time, flood.tilesVisible, visible])
}
