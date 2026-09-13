import styles from './FloodLegend.module.css'
import { DISPLAY_DEPTH_BANDS } from '@/floodmap/depthScale'
import { ForecastRecency } from '@/floodmap/floodSelectors'

/**
 * Display-only. It takes the recency it renders rather than reading a store, so the neutral and
 * warning states are reachable from a plain value in a test.
 *
 * The badge counts forecast steps, not runs: every entry in `timesteps` comes from the same run,
 * so being "behind" means being behind within one forecast series.
 */
export default function FloodLegend({ recency }: { recency: ForecastRecency }) {
    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <span className={styles.title}>Water depth</span>
                {recency.isLatest ? (
                    <span className={styles.badge}>
                        {recency.validTimeLabel ? `Updated ${recency.validTimeLabel}` : 'Latest forecast'}
                    </span>
                ) : (
                    <span className={styles.badgeStale}>
                        {recency.stepsBehind} {recency.stepsBehind === 1 ? 'step' : 'steps'} behind latest
                    </span>
                )}
            </div>
            <ul className={styles.bands}>
                {DISPLAY_DEPTH_BANDS.map(band => (
                    <li className={styles.band} key={band.id}>
                        <span className={styles.swatch} style={{ backgroundColor: band.color }} />
                        {band.label}
                    </li>
                ))}
            </ul>
        </div>
    )
}
