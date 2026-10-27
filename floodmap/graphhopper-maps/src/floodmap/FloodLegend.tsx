import styles from './FloodLegend.module.css'
import { legendGradient, legendTicks } from '@/floodmap/depthScale'
import { FloodTimestep } from '@/floodmap/FloodStore'
import { timestepCaption } from '@/floodmap/timestepLabel'

/**
 * Display-only, positioned bottom-right per the approved mockup
 * (artifacts/raw/frontend-mockups/Flood Routing Mockups v2.html, screen 2b): a vertical gradient
 * bar with a tick and a label at the lower limit of each depth band.
 */
export default function FloodLegend({ timestep }: { timestep: FloodTimestep | undefined }) {
    const caption = timestep && timestepCaption(timestep.valid_time, Date.now())
    return (
        <div className={styles.container}>
            <div className={styles.title}>Flood depth</div>
            <div className={styles.scale}>
                <div className={styles.bar} style={{ background: legendGradient() }} />
                <div className={styles.ticks}>
                    {legendTicks().map(tick => (
                        <span className={styles.tick} style={{ top: tick.topPx }} key={tick.label}>
                            <span className={styles.tickMark} />
                            {tick.label}
                        </span>
                    ))}
                </div>
            </div>
            {caption && <div className={styles.updated}>{caption}</div>}
        </div>
    )
}
