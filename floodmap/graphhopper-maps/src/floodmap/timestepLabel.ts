/**
 * `DD/MM/YYYY HH:MM` in the viewer's local time zone, the format of the mockup's legend
 * ("Updated 12/09/2026 23:24"). valid_time arrives with a +07:00 offset (flood_extent_runs.py's
 * list_timesteps), so parsing it to an instant and reading local fields converts it for a viewer
 * outside Vietnam. Returns null when valid_time does not parse.
 */
export function formatTimestepTime(validTime: string): string | null {
    const t = Date.parse(validTime)
    if (Number.isNaN(t)) return null
    const d = new Date(t)
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * The legend's caption for the step the map shows. The time is when the drawn water depth is
 * valid, not when the data was updated, so the caption says "As of" instead of the mockup's
 * "Updated". The step is normally at or before now; findNowTimestepIndex's fallback can select a
 * future step, and that one is labeled as a forecast.
 */
export function timestepCaption(validTime: string, now: number): string | null {
    const time = formatTimestepTime(validTime)
    if (!time) return null
    return Date.parse(validTime) > now ? `Forecast for ${time}` : `As of ${time}`
}
