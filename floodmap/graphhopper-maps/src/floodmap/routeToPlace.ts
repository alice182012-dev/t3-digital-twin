import { coordinateToText } from '@/Converters'
import { QueryPoint } from '@/stores/QueryStore'
import { Coordinate } from '@/utils'

/**
 * The destination point for a "route to" on a tapped place: the last query point, moved to the
 * tapped coordinate and named after the place. The other points stay as they are, so a start the
 * user already set is kept and an empty start stays empty.
 */
export function destinationForPlace(
    queryPoints: readonly QueryPoint[],
    coordinate: Coordinate,
    placeName: string | undefined,
): QueryPoint {
    const destination = queryPoints[queryPoints.length - 1]
    return {
        ...destination,
        coordinate,
        queryText: placeName || coordinateToText(coordinate),
        isInitialized: true,
    }
}

const sameCoordinate = (a: Coordinate, b: Coordinate) => a.lat === b.lat && a.lng === b.lng

/**
 * The start to set when the user taps the map with a destination already chosen and no start yet,
 * or null when the tap must leave the query points alone.
 */
export function startForTap(queryPoints: readonly QueryPoint[], coordinate: Coordinate): QueryPoint | null {
    const start = queryPoints[0]
    if (start.isInitialized || !queryPoints[queryPoints.length - 1].isInitialized) return null
    return { ...start, coordinate, queryText: coordinateToText(coordinate), isInitialized: true }
}

/** The start renamed to the place name once the lookup arrives, if the tap's coordinates are still all it holds. */
export function namedStart(
    queryPoints: readonly QueryPoint[],
    coordinate: Coordinate,
    placeName: string,
): QueryPoint | null {
    const start = queryPoints[0]
    if (!start.isInitialized || !sameCoordinate(start.coordinate, coordinate)) return null
    if (start.queryText !== coordinateToText(coordinate)) return null
    return { ...start, queryText: placeName }
}

/**
 * The points to set when the popup's route button is pressed, in dispatch order. A point that is
 * the start moves to the destination and leaves the start empty, so a route never runs from a
 * point to itself.
 */
export function pointsForRoute(
    queryPoints: readonly QueryPoint[],
    coordinate: Coordinate,
    placeName: string | undefined,
): QueryPoint[] {
    const start = queryPoints[0]
    if (!start.isInitialized || !sameCoordinate(start.coordinate, coordinate))
        return [destinationForPlace(queryPoints, coordinate, placeName)]
    const emptied = { ...start, coordinate: { lat: 0, lng: 0 }, queryText: '', isInitialized: false }
    return [emptied, destinationForPlace(queryPoints, coordinate, placeName || start.queryText)]
}
