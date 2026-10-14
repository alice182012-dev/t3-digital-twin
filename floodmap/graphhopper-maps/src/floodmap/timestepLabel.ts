/** Hanoi is UTC+7 all year. The map describes Hanoi, so every time it shows is Hanoi time, whatever the viewer's zone. */
export const HANOI_OFFSET_MS = 7 * 60 * 60 * 1000

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const pad = (n: number) => String(n).padStart(2, '0')

/** The Hanoi wall-clock fields of an instant. A shifted instant read in UTC fields gives them with no
 *  time zone data, so the result does not depend on the viewer's zone. Null when valid_time does not parse. */
function hanoiFields(validTime: string) {
    const t = Date.parse(validTime)
    if (Number.isNaN(t)) return null
    const d = new Date(t + HANOI_OFFSET_MS)
    return {
        year: d.getUTCFullYear(),
        month: d.getUTCMonth(),
        day: d.getUTCDate(),
        hour: d.getUTCHours(),
        minute: d.getUTCMinutes(),
    }
}

/** `DD/MM/YYYY HH:MM` in Hanoi time, the format of the mockup's legend ("Updated 12/09/2026 23:24").
 *  Returns null when valid_time does not parse. */
export function formatTimestepTime(validTime: string): string | null {
    const f = hanoiFields(validTime)
    if (!f) return null
    return `${pad(f.day)}/${pad(f.month + 1)}/${f.year} ${pad(f.hour)}:${pad(f.minute)}`
}

/** `Oct 11, 2026`, the Hanoi date of the same instant, for the demo banner. It is the date part of
 *  formatTimestepTime, so the banner and the legend caption cannot name different days. */
export function formatTimestepDate(validTime: string): string | null {
    const f = hanoiFields(validTime)
    if (!f) return null
    return `${MONTHS[f.month]} ${f.day}, ${f.year}`
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
