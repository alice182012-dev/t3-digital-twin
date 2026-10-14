import {
    getSpeedThresholds,
    getSpeedLabels,
    classifyBikeLTS,
    classifyFootLTS,
    computeLTSDistances,
} from '@/pathDetails/elevationWidget/colors'

describe('colors', () => {
    describe('speed buckets', () => {
        it('uses motor vehicle thresholds for car and truck', () => {
            expect(getSpeedThresholds('car')).toEqual([30, 50, 80])
            expect(getSpeedThresholds('truck')).toEqual([30, 50, 80])
        })

        it('uses bike thresholds for bike profile', () => {
            expect(getSpeedThresholds('bike')).toEqual([5, 10, 15, 20])
        })

        it('uses foot thresholds for hike profile', () => {
            expect(getSpeedThresholds('hike')).toEqual([3, 4, 5])
        })

        it('generates correct speed labels', () => {
            const labels = getSpeedLabels([30, 50, 80])
            expect(labels).toEqual(['< 30', '30\u201350', '50\u201380', '\u2265 80'])
        })
    })

    describe('classifyBikeLTS', () => {
        it('cycleway track/separate overrides road class to LTS 1', () => {
            expect(classifyBikeLTS('primary', 'track', true)).toBe(1)
            expect(classifyBikeLTS('trunk', 'separate', false)).toBe(1)
        })

        it('urban primary/secondary: missing/lane softened to 3, no stays 4', () => {
            expect(classifyBikeLTS('primary', 'missing', false)).toBe(3)
            expect(classifyBikeLTS('secondary', 'lane', false)).toBe(3)
            expect(classifyBikeLTS('primary', 'no', false)).toBe(4)
        })

        it('rural primary/secondary with lane is LTS 3, without is LTS 4', () => {
            expect(classifyBikeLTS('primary', 'lane', true)).toBe(3)
            expect(classifyBikeLTS('secondary', 'lane', true)).toBe(3)
            expect(classifyBikeLTS('primary', 'missing', true)).toBe(4)
            expect(classifyBikeLTS('secondary', 'missing', true)).toBe(4)
        })

        it('steps is LTS 3, service is LTS 2', () => {
            expect(classifyBikeLTS('steps', 'no', false)).toBe(3)
            expect(classifyBikeLTS('service', 'no', false)).toBe(2)
        })
    })

    describe('classifyFootLTS', () => {
        it('sidewalk yes is LTS 1, urban primary without sidewalk is LTS 3', () => {
            expect(classifyFootLTS('primary', 'yes', false)).toBe(1)
            expect(classifyFootLTS('primary', 'missing', false)).toBe(3)
        })
    })

    describe('computeLTSDistances', () => {
        it('treats rural density as higher stress', () => {
            const coords = [
                [0, 0, 0],
                [0, 0.001, 0],
                [0, 0.002, 0],
            ]
            const roadClass: [number, number, string][] = [[0, 2, 'primary']]
            const infra: [number, number, string][] = [[0, 2, 'missing']]
            const density: [number, number, string][] = [
                [0, 1, 'urban'],
                [1, 2, 'rural'],
            ]

            const distances = computeLTSDistances(coords, roadClass, infra, density, classifyBikeLTS)
            expect(distances[2]).toBeGreaterThan(0) // LTS 3 for urban primary + missing cycleway
            expect(distances[3]).toBeGreaterThan(0) // LTS 4 for rural primary + missing cycleway
        })
    })
})
