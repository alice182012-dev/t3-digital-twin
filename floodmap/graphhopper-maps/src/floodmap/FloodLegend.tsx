import styles from './FloodLegend.module.css'
import { DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'
import { ForecastRecency } from '@/floodmap/floodSelectors'

/**
 * Display-only, positioned top-right per the approved mockup
 * (artifacts/designs/mockups/Flood Routing Mockups v2.dc.html, screens 2b/2e).
 *
 * It takes the recency it renders rather than reading a store, so the neutral and stale states
 * are reachable from a plain value in a test.
 *
 * The mockup's static "Updated <timestamp>" footer is replaced with a real recency signal: the
 * neutral state keeps that same slot and look; the stale state re-colors it amber and counts
 * forecast steps, not runs — every entry in `timesteps` comes from the same run (see the backend
 * fix), so being "behind" means being behind within one forecast series.
 */
export default function FloodLegend({ recency }: { recency: ForecastRecency }) {
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
            {recency.isLatest ? (
                <div className={styles.footer}>
                    {recency.validTimeLabel ? `Updated ${recency.validTimeLabel}` : 'Latest forecast'}
                </div>
            ) : (
                <div className={styles.footerStale}>
                    {recency.stepsBehind} {recency.stepsBehind === 1 ? 'step' : 'steps'} behind latest
                </div>
            )}
        </div>
    )
}
