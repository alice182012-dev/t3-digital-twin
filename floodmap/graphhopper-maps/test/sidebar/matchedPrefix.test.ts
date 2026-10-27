import { splitMatchedPrefix } from '@/sidebar/search/matchedPrefix'

describe('splitMatchedPrefix', () => {
    it('bolds the query and keeps the rest of the name', () => {
        expect(splitMatchedPrefix('C5 Giảng Võ', 'C5')).toEqual({ matched: 'C5', rest: ' Giảng Võ' })
    })

    it('matches a query with diacritics and keeps the diacritics of the name', () => {
        expect(splitMatchedPrefix('Hoàn Kiếm Lake', 'Hoàn Kiếm')).toEqual({ matched: 'Hoàn Kiếm', rest: ' Lake' })
    })

    it('matches a query typed without diacritics, ignoring case', () => {
        expect(splitMatchedPrefix('Hoàn Kiếm', 'hoan kiem')).toEqual({ matched: 'Hoàn Kiếm', rest: '' })
        expect(splitMatchedPrefix('Đại Mỗ', 'dai')).toEqual({ matched: 'Đại', rest: ' Mỗ' })
    })

    it('matches decomposed input against a composed name', () => {
        expect(splitMatchedPrefix('Hoàn Kiếm', 'Hoàn')).toEqual({ matched: 'Hoàn', rest: ' Kiếm' })
    })

    it('bolds nothing when the query is not a prefix of the name', () => {
        expect(splitMatchedPrefix('Nghĩa Tân', 'Tân')).toEqual({ matched: '', rest: 'Nghĩa Tân' })
        expect(splitMatchedPrefix('C5', 'C5 Giảng Võ')).toEqual({ matched: '', rest: 'C5' })
    })

    it('bolds nothing for an empty query', () => {
        expect(splitMatchedPrefix('C5', '  ')).toEqual({ matched: '', rest: 'C5' })
    })
})
