import { bandForDepthCm, DEPTH_BAND_INDEX, DepthBandId } from '@/floodmap/depthScale'

/** One sample of POST /flood/profile (backend/flood_profile.py). `depth_m` is null outside the raster. */
export interface DepthSample {
    lon: number
    lat: number
    depth_m: number | null
}

export interface DepthBadge {
    lng: number
    lat: number
    depthCm: number
    /** The display band of the depth, or null under 5 cm. */
    band: DepthBandId | null
    label: string
}

/** A stretch shorter than this many samples (25 m apart) is dropped unless it is a local peak. */
const MIN_RUN_SAMPLES = 2
export const MAX_BADGES = 6
/** Level of a depth under 5 cm, which the map does not paint. */
const UNDER_5_CM = -1

interface Run {
    level: number
    samples: DepthSample[]
}

/**
 * The badges of a route: one per stretch of the same depth band, at the stretch's deepest sample.
 * The rule and its reasons are in artifacts/docs/claude-plan/route-depth-badges.md.
 */
export function depthBadges(samples: readonly DepthSample[]): DepthBadge[] {
    const runs = mergeEqualNeighbors(dropShortRuns(toRuns(samples.filter(s => s.depth_m !== null))))
    if (runs.length === 0 || (runs.length === 1 && runs[0].level === UNDER_5_CM)) return []
    return capBadges(runs).map(toBadge)
}

/** The deepest sample of a route in whole centimetres, or null when no sample is inside the raster. */
export function maxDepthCm(samples: readonly DepthSample[]): number | null {
    const depths = samples.flatMap(s => (s.depth_m === null ? [] : [s.depth_m]))
    return depths.length === 0 ? null : Math.round(Math.max(...depths) * 100)
}

function levelOf(depthM: number): number {
    const band = bandForDepthCm(depthM * 100)
    return band ? DEPTH_BAND_INDEX[band.id] : UNDER_5_CM
}

function toRuns(samples: DepthSample[]): Run[] {
    const runs: Run[] = []
    for (const sample of samples) {
        const level = levelOf(sample.depth_m!)
        const last = runs[runs.length - 1]
        if (last && last.level === level) last.samples.push(sample)
        else runs.push({ level, samples: [sample] })
    }
    return runs
}

/** A short stretch survives only when it is deeper than every neighbor it has. */
function dropShortRuns(runs: Run[]): Run[] {
    return runs.filter((run, i) => {
        if (run.samples.length >= MIN_RUN_SAMPLES) return true
        const neighbors = [runs[i - 1], runs[i + 1]].filter(Boolean)
        return neighbors.every(n => run.level > n.level)
    })
}

function mergeEqualNeighbors(runs: Run[]): Run[] {
    const merged: Run[] = []
    for (const run of runs) {
        const last = merged[merged.length - 1]
        if (last && last.level === run.level) last.samples.push(...run.samples)
        else merged.push({ level: run.level, samples: [...run.samples] })
    }
    return merged
}

function peak(run: Run): number {
    return Math.max(...run.samples.map(s => s.depth_m!))
}

/** Keeps the first run, the last run, and the deepest of the rest, in route order. */
function capBadges(runs: Run[]): Run[] {
    if (runs.length <= MAX_BADGES) return runs
    const middle = runs.slice(1, -1)
    const keep = new Set([...middle].sort((a, b) => peak(b) - peak(a)).slice(0, MAX_BADGES - 2))
    return runs.filter((run, i) => i === 0 || i === runs.length - 1 || keep.has(run))
}

function toBadge(run: Run): DepthBadge {
    const deepest = peak(run)
    if (run.level === UNDER_5_CM) {
        const middle = run.samples[Math.floor(run.samples.length / 2)]
        return {
            lng: middle.lon,
            lat: middle.lat,
            depthCm: Math.round(deepest * 100),
            band: null,
            label: deepest === 0 ? '0 cm' : '< 5 cm',
        }
    }
    const at = run.samples.find(s => s.depth_m === deepest)!
    const depthCm = Math.round(deepest * 100)
    return { lng: at.lon, lat: at.lat, depthCm, band: bandForDepthCm(deepest * 100)!.id, label: `${depthCm} cm` }
}
