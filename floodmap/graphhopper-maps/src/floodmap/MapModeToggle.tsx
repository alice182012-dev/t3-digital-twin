import styles from './MapModeToggle.module.css'
import PlainButton from '@/PlainButton'
import { MapMode } from '@/floodmap/FloodStore'

/**
 * Two-state map/flood switch. It sits in the same .onMapRightSide slot as MapOptions and shares
 * its PlainButton shape, but has no hover panel: there is nothing to choose from, only a state to
 * flip.
 *
 * Presentational on purpose. The recency-derived default lives in FloodStore's reducer, so this
 * component never reads a clock and renders identically for a given `mode`.
 */
export default function MapModeToggle({ mode, onChange }: { mode: MapMode; onChange: (mode: MapMode) => void }) {
    return (
        <div className={styles.container} role="group" aria-label="Map mode">
            <PlainButton
                className={mode === 'map' ? styles.optionActive : styles.option}
                aria-pressed={mode === 'map'}
                onClick={() => onChange('map')}
                title="Show the plain map"
            >
                Map
            </PlainButton>
            <PlainButton
                className={mode === 'flood' ? styles.optionActive : styles.option}
                aria-pressed={mode === 'flood'}
                onClick={() => onChange('flood')}
                title="Show the flood overlay"
            >
                Flood
            </PlainButton>
        </div>
    )
}
