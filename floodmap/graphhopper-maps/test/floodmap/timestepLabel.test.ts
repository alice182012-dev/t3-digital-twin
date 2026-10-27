import { formatTimestepDate, formatTimestepTime, timestepCaption } from '@/floodmap/timestepLabel'

// The step the demo pins on the server: 19:00 UTC on 10 Oct, which is 02:00 on 11 Oct in Hanoi.
const PINNED_UTC = '2026-10-10T19:00:00+00:00'

describe('formatTimestepTime', () => {
    it('reads an instant as DD/MM/YYYY HH:MM in Hanoi time', () => {
        expect(formatTimestepTime(PINNED_UTC)).toEqual('11/10/2026 02:00')
        expect(formatTimestepTime('2026-09-12T16:24:00+00:00')).toEqual('12/09/2026 23:24')
    })

    it('gives the same text for one instant written with different offsets', () => {
        expect(formatTimestepTime('2026-10-11T02:00:00+07:00')).toEqual('11/10/2026 02:00')
        expect(formatTimestepTime('2026-10-10T21:00:00+02:00')).toEqual('11/10/2026 02:00')
    })

    it('zero-pads single-digit fields', () => {
        expect(formatTimestepTime('2026-01-05T00:03:00+07:00')).toEqual('05/01/2026 00:03')
    })

    it('rolls over the year at Hanoi midnight', () => {
        expect(formatTimestepTime('2026-12-31T17:00:00+00:00')).toEqual('01/01/2027 00:00')
    })

    it('returns null for an unparseable valid_time', () => {
        expect(formatTimestepTime('not-a-date')).toBeNull()
    })
})

describe('formatTimestepDate', () => {
    it('names the Hanoi date, not the UTC date', () => {
        expect(formatTimestepDate(PINNED_UTC)).toEqual('Oct 11, 2026')
    })

    it('returns null for an unparseable valid_time', () => {
        expect(formatTimestepDate('not-a-date')).toBeNull()
    })
})

describe('timestepCaption', () => {
    const step = Date.parse(PINNED_UTC)

    it('labels a step at or before now with "As of"', () => {
        expect(timestepCaption(PINNED_UTC, step)).toEqual('As of 11/10/2026 02:00')
        expect(timestepCaption(PINNED_UTC, step + 10 * 60 * 1000)).toEqual('As of 11/10/2026 02:00')
    })

    it('labels a future step as a forecast', () => {
        expect(timestepCaption(PINNED_UTC, step - 60 * 1000)).toEqual('Forecast for 11/10/2026 02:00')
    })

    it('returns null for an unparseable valid_time', () => {
        expect(timestepCaption('not-a-date', step)).toBeNull()
    })
})
