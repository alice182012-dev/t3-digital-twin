import { destinationForPlace } from '@/floodmap/routeToPlace'
import { QueryPoint, QueryPointType } from '@/stores/QueryStore'

const from: QueryPoint = {
    isInitialized: false,
    queryText: '',
    coordinate: { lat: 0, lng: 0 },
    id: 0,
    color: '#417900',
    type: QueryPointType.From,
}
const to: QueryPoint = { ...from, id: 1, color: '#F97777', type: QueryPointType.To }
const tapped = { lat: 21.008917, lng: 105.733807 }

describe('destinationForPlace', () => {
    it('sets the destination to the tapped point, named after the place', () => {
        expect(destinationForPlace([from, to], tapped, 'Đại Mỗ')).toEqual({
            ...to,
            coordinate: tapped,
            queryText: 'Đại Mỗ',
            isInitialized: true,
        })
    })

    it('falls back to the coordinates when the place has no name', () => {
        expect(destinationForPlace([from, to], tapped, undefined).queryText).toEqual('21.008917,105.733807')
        expect(destinationForPlace([from, to], tapped, '').queryText).toEqual('21.008917,105.733807')
    })

    it('changes the last point, the destination, when there are via points', () => {
        const via = { ...from, id: 2, type: QueryPointType.Via }
        expect(destinationForPlace([from, via, to], tapped, 'Đại Mỗ').id).toEqual(to.id)
    })
})
