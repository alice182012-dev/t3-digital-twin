import {
    coordinatesText,
    depthLine,
    depthQuery,
    placeFromResponse,
    readingFromResponse,
    stepDepthText,
} from '@/floodmap/placeDepth'
import { FRESH_DATA_WINDOW_MS } from '@/floodmap/FloodStore'

describe('readingFromResponse', () => {
    it('rounds a wet depth to centimetres', () => {
        expect(readingFromResponse({ status: 'wet', depth_m: 0.3049 })).toEqual({ kind: 'wet', depthCm: 30 })
    })

    it('keeps dry and no_data apart', () => {
        expect(readingFromResponse({ status: 'dry', depth_m: 0 })).toEqual({ kind: 'dry' })
        expect(readingFromResponse({ status: 'no_data', depth_m: null })).toEqual({ kind: 'no_data' })
    })

    it('reads a malformed body as unavailable, never as dry', () => {
        expect(readingFromResponse(null)).toEqual({ kind: 'unavailable' })
        expect(readingFromResponse({ error: 'no depth raster' })).toEqual({ kind: 'unavailable' })
        expect(readingFromResponse({ status: 'wet', depth_m: null })).toEqual({ kind: 'unavailable' })
    })
})

describe('placeFromResponse', () => {
    it('reads the name and address', () => {
        expect(placeFromResponse({ result: { name: 'Đại Mỗ', address: 'Nam Từ Liêm, Hà Nội' } })).toEqual({
            name: 'Đại Mỗ',
            address: 'Nam Từ Liêm, Hà Nội',
        })
    })

    it('returns null when nothing was found or the name is missing', () => {
        expect(placeFromResponse({ result: null })).toBeNull()
        expect(placeFromResponse({ result: { address: 'x' } })).toBeNull()
        expect(placeFromResponse(undefined)).toBeNull()
    })
})

describe('coordinatesText', () => {
    it('prints six decimals separated by a comma and a space', () => {
        expect(coordinatesText({ lat: 20.992987, lng: 105.773723 })).toEqual('20.992987, 105.773723')
        expect(coordinatesText({ lat: 21.1, lng: 105.5 })).toEqual('21.100000, 105.500000')
    })
})

describe('depthLine', () => {
    const step = new Date('2026-09-29T15:15:00+07:00')
    const timestep = { valid_time: step.toISOString(), run: '20260929T150000' }
    const now = step.getTime() + 5 * 60 * 1000

    it('says "now" for a recent step at or before now', () => {
        expect(depthLine({ kind: 'wet', depthCm: 30 }, timestep, now)).toEqual('Water depth now: 30 cm')
    })

    it('labels a step older than the freshness window with its time', () => {
        const late = step.getTime() + FRESH_DATA_WINDOW_MS + 60 * 1000
        expect(depthLine({ kind: 'wet', depthCm: 8 }, timestep, late)).toEqual(
            'Water depth as of 29/09/2026 15:15: 8 cm',
        )
    })

    it('labels a future step as a forecast', () => {
        expect(depthLine({ kind: 'wet', depthCm: 8 }, timestep, step.getTime() - 1000)).toEqual(
            'Forecast water depth for 29/09/2026 15:15: 8 cm',
        )
    })

    it('writes 0 cm for a dry point and "< 1 cm" for a film of water', () => {
        expect(depthLine({ kind: 'dry' }, timestep, now)).toEqual('Water depth now: 0 cm')
        expect(depthLine({ kind: 'wet', depthCm: 0 }, timestep, now)).toEqual('Water depth now: < 1 cm')
    })

    it('says so when there is no data or no answer', () => {
        expect(depthLine({ kind: 'no_data' }, timestep, now)).toEqual('No flood data at this point')
        expect(depthLine({ kind: 'unavailable' }, timestep, now)).toEqual('Water depth unavailable')
    })

    it('drops the time claim when there is no timestep', () => {
        expect(depthLine({ kind: 'wet', depthCm: 12 }, undefined, now)).toEqual('Water depth: 12 cm')
    })
})

describe('stepDepthText', () => {
    it('prints a wet depth in centimetres, with a floor for under 1 cm', () => {
        expect(stepDepthText({ kind: 'wet', depthCm: 8 })).toEqual('8 cm')
        expect(stepDepthText({ kind: 'wet', depthCm: 0 })).toEqual('< 1 cm')
    })

    it('prints a dry point as 0 cm', () => {
        expect(stepDepthText({ kind: 'dry' })).toEqual('0 cm')
    })

    it('prints nothing while loading, without data, or when the lookup failed', () => {
        expect(stepDepthText(undefined)).toBeNull()
        expect(stepDepthText({ kind: 'no_data' })).toBeNull()
        expect(stepDepthText({ kind: 'unavailable' })).toBeNull()
    })
})

describe('depthQuery', () => {
    it('names the point and the timestep of GET /flood/points', () => {
        const query = depthQuery(
            { lat: 21.005133, lng: 105.757325 },
            { valid_time: '2026-09-29T17:00:00+07:00', run: '20260929T163000' },
        )
        expect(Object.fromEntries(query)).toEqual({
            lat: '21.005133',
            lon: '105.757325',
            valid_time: '2026-09-29T17:00:00+07:00',
            run: '20260929T163000',
        })
    })
})
