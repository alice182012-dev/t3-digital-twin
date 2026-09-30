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
