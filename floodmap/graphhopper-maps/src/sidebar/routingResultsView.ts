import { Path, RoutingHints } from '@/api/graphhopper'
import { milliSecondsToText } from '@/Converters'
import { CurrentRequest, RequestState, SubRequest } from '@/stores/QueryStore'

export type RouteKind = 'recommended' | 'through_water'

/**
 * One kind per path from the `td.kinds` hint, or null when the backend sent none, an unknown word, or a list that
 * does not match the number of paths. A client that cannot tell which path is which must not guess.
 */
export function parseRouteKinds(hint: unknown, pathCount: number): RouteKind[] | null {
    if (typeof hint !== 'string') return null
    const kinds = hint.split(',').map(kind => kind.trim())
    if (kinds.length !== pathCount) return null
    return kinds.every(isRouteKind) ? (kinds as RouteKind[]) : null
}

function isRouteKind(kind: string): kind is RouteKind {
    return kind === 'recommended' || kind === 'through_water'
}

export interface RouteTab {
    /** Position in `paths`, and the React key. */
    readonly index: number
    /** `Via ${path.description}` when the description is non-empty and unambiguous, otherwise `Route ${index + 1}`. */
    readonly label: string
    /** The travel time, then the maximum depth along the route once known: "14 min · 22 cm". */
    readonly detail: string
    /** Null when the backend named no kinds. */
    readonly kind: RouteKind | null
    /**
     * Only a through-water route has one: it passes through water between the precaution depth and the limit, and
     * names its deepest road once the depth is known.
     */
    readonly note: string | null
    readonly path: Path
}

/** The slice of RoutingResultsProps this module derives from. */
export interface RoutingResultsViewInput {
    paths: Path[]
    selectedPath: Path
    currentRequest: CurrentRequest
    /** Every query point is initialized. */
    allPointsSet: boolean
    /** The maximum depth in cm along each of `paths`, null while unknown. */
    maxDepthsCm?: readonly (number | null)[]
    /** The `td.*` hints of the route answer. */
    hints?: RoutingHints
}

/**
 * Everything the results panel can be. A union rather than a chain of falsy checks, because
 * "the request came back with zero paths" is the one state a flood-routing product must say out
 * loud, and the old placeholder-padded list had nowhere to put it.
 */
export type RoutingResultsView =
    | { kind: 'idle' }
    | { kind: 'loading' }
    | { kind: 'empty' }
    | { kind: 'timedOut' }
    | { kind: 'routes'; tabs: RouteTab[]; activeIndex: number }

/**
 * Total function: every (paths, currentRequest, selectedPath) triple maps to exactly one variant.
 *
 * Routes beats loading, so existing paths stay visible while alternatives stream in. Loading beats
 * empty, so a pending alternative never flashes "no safe route".
 */
export function selectRoutingResultsView(input: RoutingResultsViewInput): RoutingResultsView {
    const { paths, selectedPath, currentRequest, allPointsSet, maxDepthsCm, hints } = input
    if (paths.length > 0)
        return {
            kind: 'routes',
            tabs: buildRouteTabs(paths, maxDepthsCm, hints),
            activeIndex: activeTabIndex(paths, selectedPath),
        }
    // Sub requests outlive the route they belonged to, so an emptied point still leaves them behind.
    if (!allPointsSet) return { kind: 'idle' }
    if (hasPendingRequests(currentRequest.subRequests)) return { kind: 'loading' }
    if (currentRequest.subRequests.length === 0) return { kind: 'idle' }
    const { subRequests } = currentRequest
    // A definite "no connection" answer beats a timeout of the other request.
    if (subRequests.some(req => req.timedOut) && !subRequests.some(req => req.noConnection)) return { kind: 'timedOut' }
    return { kind: 'empty' }
}

export function hasPendingRequests(subRequests: SubRequest[]): boolean {
    return subRequests.some(req => req.state === RequestState.SENT)
}

/**
 * A description labels its tab only when it is non-empty and unique across `paths`; two routes
 * "via A1" would otherwise give two identical tabs. Every member of a colliding group falls back
 * to "Route N", not just the later duplicates, so the strip stays internally consistent.
 */
/**
 * A path's description as text. The typings say string, but GraphHopper answers a list of street
 * names (`["Đường Hoàng Tùng"]`) when it has one, and calling `trim` on that threw and blanked the
 * app. Anything that is not text or a list of text reads as empty.
 */
function descriptionText(path: Path): string {
    const raw: unknown = path.description
    const text = Array.isArray(raw) ? raw.filter(part => typeof part === 'string').join(', ') : raw
    return typeof text === 'string' ? text.trim() : ''
}

const KIND_LABEL: Record<RouteKind, string> = { recommended: 'Recommended', through_water: 'Through water' }

/** Whole sentences, so a missing hint or depth leaves one out and never prints "undefined cm". */
function throughWaterNote(hints: RoutingHints | undefined, deepestCm: number | null | undefined): string {
    const precautionCm = hints?.['td.precaution_cm']
    const limitCm = hints?.['td.limit_cm']
    const sentences = [
        precautionCm != null && limitCm != null
            ? `Passes through water between ${precautionCm} cm and ${limitCm} cm deep.`
            : 'Passes through water.',
    ]
    if (deepestCm != null) sentences.push(`Deepest road ${deepestCm} cm.`)
    return sentences.join(' ')
}

/** `paths[i]`'s maximum depth in cm is `maxDepthsCm[i]`, null or absent while unknown. */
export function buildRouteTabs(
    paths: readonly Path[],
    maxDepthsCm: readonly (number | null)[] = [],
    hints?: RoutingHints,
): RouteTab[] {
    const kinds = parseRouteKinds(hints?.['td.kinds'], paths.length)
    const counts = new Map<string, number>()
    for (const path of paths) {
        const description = descriptionText(path)
        if (description) counts.set(description, (counts.get(description) ?? 0) + 1)
    }
    return paths.map((path, index) => {
        const description = descriptionText(path)
        const kind = kinds?.[index] ?? null
        const depthCm = maxDepthsCm[index]
        const label =
            kind && (paths.length > 1 || kind === 'through_water')
                ? KIND_LABEL[kind]
                : description && counts.get(description) === 1
                  ? `Via ${description}`
                  : `Route ${index + 1}`
        const time = milliSecondsToText(path.time)
        const detail = depthCm == null ? time : `${time} · ${depthCm} cm`
        return {
            index,
            label,
            detail,
            kind,
            note: kind === 'through_water' ? throughWaterNote(hints, depthCm) : null,
            path,
        }
    })
}

/**
 * RouteStore holds selectedPath by reference (RouteStore.ts:76/108), so identity is the right
 * comparison. Falls back to 0 when the reference is stale, which keeps the result a valid index
 * into a non-empty `paths` by construction.
 */
export function activeTabIndex(paths: readonly Path[], selectedPath: Path): number {
    const index = paths.indexOf(selectedPath)
    return index >= 0 ? index : 0
}
