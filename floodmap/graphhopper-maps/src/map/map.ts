import Dispatcher from '@/stores/Dispatcher'
import { Map, View } from 'ol'
import { fromLonLat } from 'ol/proj'
import { MapIsLoaded, StopSyncCurrentLocation } from '@/actions/Actions'
import { defaults as defaultControls } from 'ol/control'
import styles from '@/map/Map.module.css'

let map: Map | undefined

export function createMap(): Map {
    map = new Map({
        view: new View({
            enableRotation: false,
            multiWorld: false,
            constrainResolution: false,
            // Fixed initial view over the flood-forecast area, not the routing graph's own bbox
            // (see MapActionReceiver's InfoReceived handler, which no longer overrides this).
            center: fromLonLat([105.74599494716486, 21.00753674005938]),
            zoom: 14,
        }),
        controls: defaultControls({
            zoom: true,
            zoomOptions: {
                className: styles.customZoom,
            },
            attribution: true,
            attributionOptions: {
                className: styles.customAttribution,
                collapsible: false,
            },
        }),
    })
    map.once('postrender', () => {
        Dispatcher.dispatch(new MapIsLoaded())
    })

    map.on('pointerdrag', () => {
        if (!getMap().getView().getAnimating()) Dispatcher.dispatch(new StopSyncCurrentLocation())
    })

    return map
}

export function setMap(m: Map) {
    map = m
}

export function getMap(): Map {
    if (!map) throw Error('Map must be initialized before it can be used. Use "createMap" when starting the app')
    return map
}
