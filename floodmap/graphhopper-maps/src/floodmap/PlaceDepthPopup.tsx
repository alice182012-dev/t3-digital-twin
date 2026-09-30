import { useEffect, useState } from 'react'
import { Map } from 'ol'
import MapPopup from '@/layers/MapPopup'
import { BACKEND_BASE, FloodTimestep } from '@/floodmap/FloodStore'
import { coordinatesText, depthLine, depthQuery, placeFromResponse, readingFromResponse } from '@/floodmap/placeDepth'
import { Coordinate } from '@/utils'
import styles from './PlaceDepthPopup.module.css'

interface PlaceDepthPopupProps {
    map: Map
    coordinate: Coordinate | null
    timestep: FloodTimestep | undefined
    onClose: () => void
    /** Starts a route to the tapped point. `placeName` is undefined while the place lookup has no name. */
    onRoute: (placeName: string | undefined) => void
}

/**
 * The card of the approved mockup's screen 2b: place name, address, coordinates, and the water
 * depth at the tapped point, read from the selected flood timestep.
 */
export default function PlaceDepthPopup({ map, coordinate, timestep, onClose, onRoute }: PlaceDepthPopupProps) {
    const point = coordinate && { lat: String(coordinate.lat), lon: String(coordinate.lng) }
    const depthParams = coordinate && timestep && depthQuery(coordinate, timestep)
    const depthBody = useJson('flood/points', depthParams)
    const placeBody = useJson('places/reverse', point && new URLSearchParams(point))
    const depth = depthBody === undefined ? null : readingFromResponse(depthBody)
    const place = placeBody === undefined ? undefined : placeFromResponse(placeBody)

    useEffect(() => {
        if (!coordinate) return
        const onKeyDown = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
        document.addEventListener('keydown', onKeyDown)
        return () => document.removeEventListener('keydown', onKeyDown)
    }, [coordinate, onClose])

    return (
        <MapPopup map={map} coordinate={coordinate}>
            <div className={styles.anchor}>
                {coordinate && (
                    <>
                        <span className={styles.pin} />
                        <div className={styles.card} role="dialog" aria-label="Water depth at the selected point">
                            <button className={styles.close} onClick={onClose} aria-label="Close">
                                ×
                            </button>
                            <div className={styles.header}>
                                <div className={styles.headerText}>
                                    <div className={styles.name}>
                                        {place === undefined
                                            ? 'Looking up place…'
                                            : (place?.name ?? 'Selected location')}
                                    </div>
                                    {place?.address && <div className={styles.address}>{place.address}</div>}
                                </div>
                                <button
                                    className={styles.route}
                                    onClick={() => onRoute(place?.name)}
                                    aria-label="Route to this place"
                                    title="Route to this place"
                                >
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                        <path
                                            d="M6 20V10a4 4 0 0 1 4-4h8"
                                            stroke="#fff"
                                            strokeWidth="2.2"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                        />
                                        <path
                                            d="M15 3l3 3-3 3"
                                            stroke="#fff"
                                            strokeWidth="2.2"
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                        />
                                    </svg>
                                </button>
                            </div>
                            <div className={styles.coordinates}>{coordinatesText(coordinate)}</div>
                            <div className={styles.depth}>
                                {depth ? depthLine(depth, timestep, Date.now()) : 'Loading water depth…'}
                            </div>
                        </div>
                    </>
                )}
            </div>
        </MapPopup>
    )
}

/**
 * `undefined` while loading, `null` when the request failed or was not made. The depth and the
 * place come from different services, and the place lookup is the slow one, so each one shows as
 * soon as it arrives and a failure of one leaves the other readable.
 */
function useJson(path: string, params: URLSearchParams | null | undefined): unknown {
    const [body, setBody] = useState<unknown>(undefined)
    const query = params?.toString()

    useEffect(() => {
        setBody(undefined)
        if (query === undefined) {
            setBody(null)
            return
        }
        const controller = new AbortController()
        fetch(new URL(`${BACKEND_BASE}${path}?${query}`, window.location.href), { signal: controller.signal })
            .then(res => (res.ok ? res.json() : null))
            .catch(() => null)
            .then(json => controller.signal.aborted || setBody(json))
        return () => controller.abort()
    }, [path, query])

    return body
}
