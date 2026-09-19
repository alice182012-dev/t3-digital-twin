import { bandForExtentCode } from '@/floodmap/depthScale'

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
