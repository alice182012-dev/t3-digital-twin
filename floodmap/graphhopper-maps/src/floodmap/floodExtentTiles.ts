/**
 * Where the flood-extent tiles of one timestep live. The Airflow task 9_build_flood_tiles
 * (scripts/flood_extent/flood_extent.py's build_run_tiles) writes one folder per (run, timestep),
 * named after the same two values FloodStore already holds, so no extra lookup is needed.
 */
interface TimestepIdentity {
    valid_time: string
    run: string
}

/** '2026-08-11T01:40:00' -> '20260811T014000', the folder name the tile builder uses. */
export function tileFolderKey(isoTime: string): string {
    return isoTime.replace(/[-:]/g, '').slice(0, 15)
}

/** An OpenLayers XYZ template. A timestep with no flooding has no tiles, so every tile 404s and
 *  the map shows nothing, which is the right picture. */
export function floodExtentTilesUrl(step: TimestepIdentity): string {
    return `/flood-extent/${tileFolderKey(step.run)}/${tileFolderKey(step.valid_time)}/{z}/{x}/{y}.pbf`
}

const OVERRIDE_PARAM = 'flood_extent'
const OVERRIDE_VALUE = /^\d{8}T\d{6}\/\d{8}T\d{6}$/

/**
 * A tile folder named in the page address, for looking at tiles the database doesn't list. Open
 * `/?flood_extent=20251006T000000/20251006T013001` (run, then timestep) to draw that folder's
 * tiles instead of the selected timestep's. Returns undefined when the parameter is absent or
 * isn't shaped like two tile folder names, so an arbitrary path can't be requested.
 */
export function floodExtentOverrideUrl(search: string): string | undefined {
    const value = new URLSearchParams(search).get(OVERRIDE_PARAM)
    if (!value || !OVERRIDE_VALUE.test(value)) return undefined
    return `/flood-extent/${value}/{z}/{x}/{y}.pbf`
}
