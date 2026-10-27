import { depthBadges, DepthSample, maxDepthCm } from '@/floodmap/depthBadges'

/** One sample per depth, spaced along a west-east line so the order is the route order. */
function line(...depths: (number | null)[]): DepthSample[] {
    return depths.map((depth_m, i) => ({ lon: 105.75 + i * 0.001, lat: 21.0, depth_m }))
}

const summary = (samples: DepthSample[]) => depthBadges(samples).map(b => b.label)

describe('depthBadges', () => {
    it('marks each change of depth band, like the four badges of mockup screen 2e', () => {
        const samples = line(0.08, 0.08, 0.08, 0.22, 0.22, 0.22, 0.05, 0.05, 0.05, 0, 0, 0)

        expect(summary(samples)).toEqual(['8 cm', '22 cm', '5 cm', '0 cm'])
    })

    it('puts a badge at the deepest sample of its stretch, with that depth', () => {
        const samples = line(0.12, 0.18, 0.14, 0.11)

        expect(depthBadges(samples)).toEqual([
            { lng: samples[1].lon, lat: 21.0, depthCm: 18, band: 'd2', label: '18 cm' },
        ])
    })

    it('gives a dry route no badges, and a route outside the raster none either', () => {
        expect(depthBadges(line(0, 0, 0, 0))).toEqual([])
        expect(depthBadges(line(null, null, null))).toEqual([])
        expect(depthBadges([])).toEqual([])
    })

    it('smooths a one-sample dry blip inside a wet stretch', () => {
        expect(summary(line(0.3, 0.3, 0.3, 0, 0.3, 0.3, 0.3))).toEqual(['30 cm'])
    })

    it('keeps a one-sample deep stretch, since a driver needs to know about it', () => {
        expect(summary(line(0, 0, 0, 0, 0.7, 0, 0, 0, 0))).toEqual(['0 cm', '70 cm', '0 cm'])
    })

    it('reads a trace under 5 cm as "< 5 cm" and a dry stretch as "0 cm"', () => {
        expect(summary(line(0.03, 0.03, 0.03, 0.3, 0.3, 0.3, 0, 0, 0))).toEqual(['< 5 cm', '30 cm', '0 cm'])
    })

    it('skips samples outside the raster instead of reading them as dry', () => {
        expect(summary(line(0.3, 0.3, null, null, 0.3, 0.3))).toEqual(['30 cm'])
    })

    it('keeps at most 6 badges: the first, the last, and the deepest of the rest', () => {
        // Bands 1 to 7 alternate with dry, so there are 15 runs of 2 samples each.
        const depths = [0.06, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65].flatMap(d => [0, 0, d, d])
        const badges = depthBadges(line(...depths, 0, 0))

        expect(badges.map(b => b.label)).toEqual(['0 cm', '35 cm', '45 cm', '55 cm', '65 cm', '0 cm'])
    })
})

describe('maxDepthCm', () => {
    it('is the deepest sample in whole centimetres', () => {
        expect(maxDepthCm(line(0.08, 0.224, null, 0.1))).toBe(22)
    })

    it('is 0 for a dry route and null when no sample is inside the raster', () => {
        expect([maxDepthCm(line(0, 0)), maxDepthCm(line(null, null)), maxDepthCm([])]).toEqual([0, null, null])
    })
})
