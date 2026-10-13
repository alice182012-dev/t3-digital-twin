/** One column of POST /flood/forecast (backend/flood_forecast.py). The depth fields are null when
 *  no part of the route lies inside that step's raster. */
export interface ForecastColumn {
    valid_time: string
    run: string
    mean_depth_m: number | null
    max_depth_m: number | null
    wet_fraction: number | null
}

export interface DepthBar {
    validTime: string
    /** HH:MM in the viewer's local time zone. */
    timeLabel: string
    /** Axis label: "Now" for the now bar, HH:MM on the hour, empty otherwise. */
    label: string
    depthCm: number | null
    /** Bar height as a percentage of the chart's depth scale. */
    heightPercent: number
    isNow: boolean
}

export interface DepthChart {
    bars: DepthBar[]
    /** Depth of the "now" bar, drawn as the dashed line. Null when no bar is now or it has no depth. */
    nowDepthCm: number | null
    nowLinePercent: number | null
}

/** The backend's cap on route vertices. */
export const MAX_FORECAST_POINTS = 2000
export const FORECAST_STEP_MS = 15 * 60 * 1000
const COLUMN_STRIDE_MS = 2 * FORECAST_STEP_MS
const COLUMNS_BEFORE_NOW = 1
const COLUMN_COUNT = 5
/** Covers the window from 30 minutes before the current half hour to 90 minutes after it. */
export const FORECAST_REQUEST_STEPS = 9
/** A dry or nearly dry route still gets a 10 cm scale, so 1 cm does not fill the chart. */
const MIN_SCALE_CM = 10

/**
 * Columns to bars. The pipeline publishes 15-minute steps and the chart shows the ones on the half
 * hour, so the hour columns carry a label: the five times are halfHour + k * 30 minutes for
 * k = -1..3, where halfHour is the latest :00 or :30 at or before `now`. Columns are matched by
 * `valid_time` because the backend omits steps that have no raster, and a missing slot gives no
 * bar. The "now" bar is the latest selected column at or before `now`. When every column is in the
 * future, no bar is now: labelling a forecast as the present would misstate what the route looks like.
 */
export function shapeDepthChart(columns: readonly ForecastColumn[], now: number): DepthChart {
    const anchor = halfHourStart(now)
    const byTime = new Map(columns.map(column => [Date.parse(column.valid_time), column]))
    const parsed = Array.from({ length: COLUMN_COUNT }, (_, i) => {
        const t = anchor + (i - COLUMNS_BEFORE_NOW) * COLUMN_STRIDE_MS
        return { column: byTime.get(t), t }
    }).flatMap(({ column, t }) => (column ? [{ column, t }] : []))
    let nowIndex = -1
    parsed.forEach(({ t }, i) => {
        if (t <= now) nowIndex = i
    })
    const depths = parsed.map(({ column }) =>
        column.mean_depth_m === null ? null : Math.round(column.mean_depth_m * 100),
    )
    const scaleCm = Math.max(MIN_SCALE_CM, ...depths.map(d => d ?? 0))
    const bars = parsed.map(({ column, t }, i) => ({
        validTime: column.valid_time,
        timeLabel: formatClock(t),
        label: i === nowIndex ? 'Now' : new Date(t).getMinutes() === 0 ? formatClock(t) : '',
        depthCm: depths[i],
        heightPercent: ((depths[i] ?? 0) / scaleCm) * 100,
        isNow: i === nowIndex,
    }))
    const nowDepthCm = nowIndex < 0 ? null : depths[nowIndex]
    return {
        bars,
        nowDepthCm,
        nowLinePercent: nowDepthCm === null ? null : (nowDepthCm / scaleCm) * 100,
    }
}

/** The request window starts 30 minutes before the current half hour, so the chart shows where the
 *  route has just been as well as where it is going. */
export function forecastWindowStart(now: number): string {
    return new Date(halfHourStart(now) - COLUMN_STRIDE_MS).toISOString()
}

function halfHourStart(now: number): number {
    return Math.floor(now / COLUMN_STRIDE_MS) * COLUMN_STRIDE_MS
}

/** Route coordinates as [lon, lat] pairs, thinned evenly to the backend's cap with both ends
 *  kept. GraphHopper adds elevation as a third value when it is enabled. */
export function forecastRequestPoints(coordinates: readonly number[][]): [number, number][] {
    const count = Math.min(coordinates.length, MAX_FORECAST_POINTS)
    const picked =
        count === coordinates.length
            ? coordinates
            : Array.from(
                  { length: count },
                  (_, i) => coordinates[Math.round((i * (coordinates.length - 1)) / (count - 1))],
              )
    return picked.map(c => [c[0], c[1]])
}

function formatClock(t: number): string {
    const d = new Date(t)
    return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
