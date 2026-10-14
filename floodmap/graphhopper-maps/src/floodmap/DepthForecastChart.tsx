import { useEffect, useState } from 'react'
import styles from './DepthForecastChart.module.css'
import { BACKEND_BASE } from '@/floodmap/FloodStore'
import {
    DepthBar,
    FORECAST_REQUEST_STEPS,
    ForecastColumn,
    forecastRequestPoints,
    forecastWindowStart,
    shapeDepthChart,
} from '@/floodmap/depthForecast'

/**
 * Mean flood depth along the route for five steps 30 minutes apart, the "Average water depth" chart of
 * mockup screen 2e. Renders nothing until the forecast arrives, or when the backend has no raster
 * for any step in the window.
 */
export default function DepthForecastChart({
    coordinates,
    limitCm,
}: {
    coordinates: readonly number[][]
    limitCm?: number
}) {
    const columns = useDepthForecast(coordinates)
    if (!columns || columns.length === 0) return null
    const chart = shapeDepthChart(columns, Date.now(), limitCm)
    return (
        <figure className={styles.container} role="img" aria-label={describe(chart.bars)}>
            <figcaption className={styles.title} aria-hidden="true">
                Average water depth
            </figcaption>
            <div className={styles.plot} aria-hidden="true">
                <div className={styles.bars}>
                    {chart.bars.map(bar => (
                        <div
                            className={styles.column}
                            key={bar.validTime}
                            title={`${bar.timeLabel}: ${depthText(bar)}`}
                        >
                            <div
                                className={bar.isNow ? styles.nowBar : styles.bar}
                                style={{ height: `${bar.heightPercent}%` }}
                            />
                        </div>
                    ))}
                    {chart.nowLinePercent !== null && (
                        <div className={styles.nowLine} style={{ bottom: `${chart.nowLinePercent}%` }}>
                            <span className={styles.nowLineLabel}>{chart.nowDepthCm} cm</span>
                        </div>
                    )}
                    {chart.limitLinePercent !== null && (
                        <div className={styles.limitLine} style={{ bottom: `${chart.limitLinePercent}%` }}>
                            <span className={styles.limitLineLabel}>{chart.limitCm} cm</span>
                        </div>
                    )}
                </div>
            </div>
            <div className={styles.labels} aria-hidden="true">
                {chart.bars.map(bar => (
                    <span className={bar.isNow ? styles.nowLabel : styles.label} key={bar.validTime}>
                        {bar.label}
                    </span>
                ))}
            </div>
        </figure>
    )
}

function useDepthForecast(coordinates: readonly number[][]): ForecastColumn[] | null {
    const [columns, setColumns] = useState<ForecastColumn[] | null>(null)
    useEffect(() => {
        const controller = new AbortController()
        setColumns(null)
        fetch(new URL(`${BACKEND_BASE}flood/forecast`, window.location.href), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                points: forecastRequestPoints(coordinates),
                from: forecastWindowStart(Date.now()),
                steps: FORECAST_REQUEST_STEPS,
            }),
            signal: controller.signal,
        })
            .then(res => (res.ok ? res.json() : { columns: [] }))
            .then(data => setColumns(data.columns ?? []))
            .catch(() => {
                // Aborted by a newer route, or the backend is unreachable: the chart stays hidden.
            })
        return () => controller.abort()
    }, [coordinates])
    return columns
}

function depthText(bar: DepthBar): string {
    return bar.depthCm === null ? 'no data' : `${bar.depthCm} cm`
}

function describe(bars: readonly DepthBar[]): string {
    const steps = bars.map(bar => `${bar.isNow ? 'now, ' : ''}${bar.timeLabel}: ${depthText(bar)}`)
    return `Average water depth along the route. ${steps.join('; ')}.`
}
