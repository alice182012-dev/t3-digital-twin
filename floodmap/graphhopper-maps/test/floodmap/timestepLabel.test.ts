import { formatTimestepTime, timestepCaption } from '@/floodmap/timestepLabel'

describe('formatTimestepTime', () => {
    it('formats an instant as DD/MM/YYYY HH:MM in local time', () => {
        const localInstant = new Date(2026, 8, 12, 23, 24).toISOString()
        expect(formatTimestepTime(localInstant)).toEqual('12/09/2026 23:24')
    })

    it('zero-pads single-digit fields', () => {
        const localInstant = new Date(2026, 0, 5, 7, 3).toISOString()
        expect(formatTimestepTime(localInstant)).toEqual('05/01/2026 07:03')
    })

    it('returns null for an unparseable valid_time', () => {
        expect(formatTimestepTime('not-a-date')).toBeNull()
    })
})

describe('timestepCaption', () => {
    const step = new Date(2026, 8, 25, 14, 15)

    it('labels a step at or before now with "As of"', () => {
        expect(timestepCaption(step.toISOString(), step.getTime())).toEqual('As of 25/09/2026 14:15')
        expect(timestepCaption(step.toISOString(), step.getTime() + 10 * 60 * 1000)).toEqual('As of 25/09/2026 14:15')
    })

    it('labels a future step as a forecast', () => {
        expect(timestepCaption(step.toISOString(), step.getTime() - 60 * 1000)).toEqual('Forecast for 25/09/2026 14:15')
    })

    it('returns null for an unparseable valid_time', () => {
        expect(timestepCaption('not-a-date', step.getTime())).toBeNull()
    })
})
