import styles from './FloodLegend.module.css'
import { DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'
import { FloodTimestep } from '@/floodmap/FloodStore'
import { timestepCaption } from '@/floodmap/timestepLabel'

/**
 * Display-only, positioned top-right per the approved mockup
 * (artifacts/raw/mockups/Flood Routing Mockups v2.dc.html, screens 2b/2e).
 */
export default function FloodLegend({ timestep }: { timestep: FloodTimestep | undefined }) {
    const caption = timestep && timestepCaption(timestep.valid_time, Date.now())
    return (
        <div className={styles.container}>
            <div className={styles.title}>Flood depth</div>
            <ul className={styles.bands}>
                {DISPLAY_DEPTH_BANDS.map(band => (
                    <li className={styles.band} key={band.id}>
                        <span className={styles.swatch} style={{ backgroundColor: band.color }} />
                        {band.label}
                    </li>
                ))}
            </ul>
            {caption && <div className={styles.updated}>{caption}</div>}
        </div>
    )
}
