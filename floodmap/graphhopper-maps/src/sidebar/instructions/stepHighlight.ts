import { Bbox, Instruction } from '@/api/graphhopper'
import { Coordinate, getBBoxPoints } from '@/utils'

/** The part of a route that one turn step covers, and the box that frames it on the map. */
export function stepHighlight(instruction: Pick<Instruction, 'points'>): { segment: Coordinate[]; bbox: Bbox | null } {
    const segment = instruction.points.map(([lng, lat]) => ({ lng, lat }))
    return { segment, bbox: getBBoxPoints(segment) }
}
