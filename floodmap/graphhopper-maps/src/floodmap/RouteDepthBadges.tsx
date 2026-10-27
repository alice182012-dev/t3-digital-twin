import { useMemo } from 'react'
import { Map } from 'ol'
import MapPopup from '@/layers/MapPopup'
import { FloodTimestep } from '@/floodmap/FloodStore'
import { depthBadges, MAX_BADGES } from '@/floodmap/depthBadges'
import { DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'
import { useDepthProfile } from '@/floodmap/useDepthProfile'
import styles from './RouteDepthBadges.module.css'

const DRY_DOT = '#e5e7eb'

interface RouteDepthBadgesProps {
    map: Map
    /** The selected route's [lng, lat] vertices. */
    coordinates: readonly number[][]
    /** Set in Flood mode. Without it no badge is drawn. */
    timestep: FloodTimestep | undefined
}

/**
 * The depth pills of the approved mockup's screen 2e: one white pill with a band-colored dot on
 * each stretch of the route where the depth band changes.
 */
export default function RouteDepthBadges({ map, coordinates, timestep }: RouteDepthBadgesProps) {
    const samples = useDepthProfile(coordinates, timestep)
    const badges = useMemo(() => (samples ? depthBadges(samples) : []), [samples])
    const deepest = Math.max(0, ...badges.map(b => b.depthCm))
    // OpenLayers moves each popup's element out of the tree React built, so a MapPopup that
    // unmounts while the map lives makes React remove a node it no longer owns, and the whole app
    // goes blank. A fixed set of slots stays mounted, and a slot without a badge is hidden.
    return (
        <>
            {Array.from({ length: MAX_BADGES }, (_, slot) => {
                const badge = badges[slot]
                return (
                    <MapPopup key={slot} map={map} coordinate={badge ? { lat: badge.lat, lng: badge.lng } : null}>
                        <div className={styles.anchor}>
                            {badge && (
                                <span className={badge.depthCm === deepest ? styles.deepestPill : styles.pill}>
                                    <span
                                        className={styles.dot}
                                        style={{
                                            background: badge.band
                                                ? DISPLAY_DEPTH_BANDS.find(b => b.id === badge.band)!.color
                                                : DRY_DOT,
                                        }}
                                    />
                                    {badge.label}
                                </span>
                            )}
                        </div>
                    </MapPopup>
                )
            })}
        </>
    )
}
