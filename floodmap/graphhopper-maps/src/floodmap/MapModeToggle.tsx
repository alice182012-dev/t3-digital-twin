import styles from './MapModeToggle.module.css'
import PlainButton from '@/PlainButton'
import { MapMode } from '@/floodmap/FloodStore'

/**
 * Two square thumbnail buttons, bottom-left, per the approved mockup
 * (artifacts/raw/mockups/Flood Routing Mockups v2.dc.html, screens 2a/2b/2c/2d/2e/2f).
 * Not modeled on MapOptions — that control's hover-to-expand single button doesn't fit an
 * always-visible two-button toggle; this is its own absolutely-positioned sibling.
 *
 * Presentational on purpose. The recency-derived default lives in FloodStore's reducer, so this
 * component never reads a clock and renders identically for a given `mode`.
 */
export default function MapModeToggle({ mode, onChange }: { mode: MapMode; onChange: (mode: MapMode) => void }) {
    return (
        <div className={styles.container} role="group" aria-label="Map mode">
            <PlainButton
                className={mode === 'map' ? styles.thumbActive : styles.thumb}
                aria-pressed={mode === 'map'}
                onClick={() => onChange('map')}
                title="Show the plain map"
            >
                <span className={styles.thumbLabel}>Map</span>
            </PlainButton>
            <PlainButton
                className={mode === 'flood' ? styles.thumbActive : styles.thumb}
                aria-pressed={mode === 'flood'}
                onClick={() => onChange('flood')}
                title="Show the flood overlay"
            >
                <span className={styles.floodTint} />
                <span className={styles.thumbLabel}>Flood</span>
            </PlainButton>
        </div>
    )
}
