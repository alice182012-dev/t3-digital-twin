import { formatTimestepTime } from '@/floodmap/timestepLabel'

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
