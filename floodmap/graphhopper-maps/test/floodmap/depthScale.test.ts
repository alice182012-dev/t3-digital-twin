import { bandForDepthCm, bandForExtentCode } from '@/floodmap/depthScale'

describe('bandForExtentCode', () => {
    it('maps each notebook upper-limit code to the band that ends there', () => {
        expect(bandForExtentCode(10)?.label).toBe('5–10 cm')
        expect(bandForExtentCode(30)?.label).toBe('20–30 cm')
        expect(bandForExtentCode(60)?.label).toBe('50–60 cm')
    })

    it('maps the top code to the open-ended band', () => {
        expect(bandForExtentCode(600)?.label).toBe('> 60 cm')
    })

    it('has no band for dry cells or unknown codes', () => {
        expect(bandForExtentCode(0)).toBeUndefined()
        expect(bandForExtentCode(15)).toBeUndefined()
    })
})

describe('bandForDepthCm', () => {
    it('puts a lower limit in the band that starts there', () => {
        expect(bandForDepthCm(5)?.label).toBe('5–10 cm')
        expect(bandForDepthCm(10)?.label).toBe('10–20 cm')
        expect(bandForDepthCm(59.9)?.label).toBe('50–60 cm')
    })

    it('puts everything from 60 cm up in the open-ended band', () => {
        expect(bandForDepthCm(60)?.label).toBe('> 60 cm')
        expect(bandForDepthCm(300)?.label).toBe('> 60 cm')
    })

    it('has no band under 5 cm', () => {
        expect(bandForDepthCm(0)).toBeUndefined()
        expect(bandForDepthCm(4.9)).toBeUndefined()
    })
})
