import { destinationForPlace, namedStart, pointsForRoute, startForTap } from '@/floodmap/routeToPlace'
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
const a = { lat: 21.025, lng: 105.755 }
const b = { lat: 21.0255, lng: 105.762 }
const filled = (point: QueryPoint, coordinate: typeof a, queryText: string): QueryPoint => ({
    ...point,
    coordinate,
    queryText,
    isInitialized: true,
})

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

describe('startForTap', () => {
    it('fills an empty start when the destination is set', () => {
        expect(startForTap([from, filled(to, b, 'Far place')], a)).toEqual(filled(from, a, '21.025,105.755'))
    })

    it('changes nothing when both points are empty', () => {
        expect(startForTap([from, to], a)).toBeNull()
    })

    it('changes nothing when both points are set', () => {
        expect(startForTap([filled(from, b, 'Start'), filled(to, b, 'End')], a)).toBeNull()
    })

    it('changes nothing when only the start is set', () => {
        expect(startForTap([filled(from, b, 'Start'), to], a)).toBeNull()
    })
})

describe('namedStart', () => {
    const autoFilled = [filled(from, a, '21.025,105.755'), filled(to, b, 'Far place')]

    it('renames a start that still holds the tapped coordinates', () => {
        expect(namedStart(autoFilled, a, 'Cầu Giấy')).toEqual(filled(from, a, 'Cầu Giấy'))
    })

    it('changes nothing when the start moved to another coordinate', () => {
        expect(namedStart([filled(from, b, '21.0255,105.762'), autoFilled[1]], a, 'Cầu Giấy')).toBeNull()
    })

    it('changes nothing when the user already typed another text', () => {
        expect(namedStart([filled(from, a, 'My home'), autoFilled[1]], a, 'Cầu Giấy')).toBeNull()
    })

    it('changes nothing when the start is empty', () => {
        expect(namedStart([from, autoFilled[1]], a, 'Cầu Giấy')).toBeNull()
    })
})

describe('pointsForRoute', () => {
    it('moves the auto-filled start to the destination and empties the start', () => {
        const points = [filled(from, a, '21.025,105.755'), filled(to, b, 'Far place')]
        expect(pointsForRoute(points, a, 'Cầu Giấy')).toEqual([from, filled(to, a, 'Cầu Giấy')])
    })

    it('keeps the name the start already had when the lookup has no name', () => {
        const points = [filled(from, a, 'Cầu Giấy'), filled(to, b, 'Far place')]
        expect(pointsForRoute(points, a, undefined)).toEqual([from, filled(to, a, 'Cầu Giấy')])
    })

    it('sets only the destination when both points are set and the start is elsewhere', () => {
        const points = [filled(from, b, 'Start'), filled(to, b, 'Far place')]
        expect(pointsForRoute(points, a, 'Cầu Giấy')).toEqual([filled(to, a, 'Cầu Giấy')])
    })

    it('sets only the destination when both points are empty', () => {
        expect(pointsForRoute([from, to], a, 'Cầu Giấy')).toEqual([filled(to, a, 'Cầu Giấy')])
    })
})
