import { floodExtentOverrideUrl, floodExtentTilesUrl, tileFolderKey } from '@/floodmap/floodExtentTiles'

describe('tileFolderKey', () => {
    it('turns the database timestamp into the tile builder folder name', () => {
        expect(tileFolderKey('2026-08-11T01:40:00')).toBe('20260811T014000')
    })

    it('drops fractional seconds and offsets', () => {
        expect(tileFolderKey('2026-08-11T01:40:00.250')).toBe('20260811T014000')
        expect(tileFolderKey('2026-08-11T01:40:00+07:00')).toBe('20260811T014000')
    })
})

describe('floodExtentTilesUrl', () => {
    it('addresses the selected run and timestep', () => {
        expect(floodExtentTilesUrl({ run: '2026-08-11T01:40:00', valid_time: '2026-08-11T02:40:00' })).toBe(
            '/flood-extent/20260811T014000/20260811T024000/{z}/{x}/{y}.pbf',
        )
    })
})

describe('floodExtentOverrideUrl', () => {
    it('turns a run and timestep in the address into a tile template', () => {
        expect(floodExtentOverrideUrl('?flood_extent=20251006T000000/20251006T013001')).toBe(
            '/flood-extent/20251006T000000/20251006T013001/{z}/{x}/{y}.pbf',
        )
    })

    it('ignores other parameters and a missing value', () => {
        expect(floodExtentOverrideUrl('')).toBeUndefined()
        expect(floodExtentOverrideUrl('?point=1,2&profile=car')).toBeUndefined()
    })

    it('rejects anything that is not two tile folder names', () => {
        expect(floodExtentOverrideUrl('?flood_extent=../../etc/passwd')).toBeUndefined()
        expect(floodExtentOverrideUrl('?flood_extent=20251006T000000')).toBeUndefined()
        expect(floodExtentOverrideUrl('?flood_extent=20251006T000000/20251006T013001/../x')).toBeUndefined()
    })
})
