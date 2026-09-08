import { useEffect, useState } from 'react'
import styles from './TimeSlider.module.css'
import {
    getFloodStore,
    loadFloodTimesteps,
    reissueCurrentRoute,
    FloodStoreState,
    SelectFloodTimestep,
    SelectFloodVehicle,
    ToggleFloodTiles,
} from '@/floodmap/FloodStore'
import Dispatcher from '@/stores/Dispatcher'

export default function TimeSlider() {
    const [flood, setFlood] = useState<FloodStoreState>(getFloodStore().state)

    useEffect(() => {
        const onChange = () => setFlood(getFloodStore().state)
        getFloodStore().register(onChange)
        loadFloodTimesteps()
        return () => getFloodStore().deregister(onChange)
    }, [])

    useEffect(() => {
        if (flood.selectedIndex < 0 || flood.timesteps.length === 0) return
        reissueCurrentRoute()
    }, [flood.selectedIndex, flood.vehicleType, flood.timesteps])

    if (flood.timesteps.length === 0) return null

    const step = flood.timesteps[flood.selectedIndex]
    const label = step ? new Date(step.valid_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''

    return (
        <div className={styles.container}>
            <select
                className={styles.select}
                value={flood.vehicleType}
                onChange={e => Dispatcher.dispatch(new SelectFloodVehicle(e.target.value))}
            >
                <option value="motorbike">Motorbike</option>
                <option value="car">Car</option>
                <option value="truck">Truck</option>
            </select>
            <span className={styles.label}>{label}</span>
            <input
                className={styles.slider}
                type="range"
                min={0}
                max={flood.timesteps.length - 1}
                step={1}
                value={Math.max(flood.selectedIndex, 0)}
                onChange={e => Dispatcher.dispatch(new SelectFloodTimestep(parseInt(e.target.value, 10)))}
            />
            <label className={styles.toggle}>
                <input
                    type="checkbox"
                    checked={flood.tilesVisible}
                    onChange={e => Dispatcher.dispatch(new ToggleFloodTiles(e.target.checked))}
                />
                Flood
            </label>
        </div>
    )
}
