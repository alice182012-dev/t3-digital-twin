import { Path } from '@/api/graphhopper'
import { CurrentRequest, RequestState, SubRequest } from '@/stores/QueryStore'

export interface RouteTab {
    /** Position in `paths`, and the React key. */
    readonly index: number
    /** path.description when non-empty and unambiguous, otherwise `Route ${index + 1}`. */
    readonly label: string
    readonly path: Path
}

/** The slice of RoutingResultsProps this module derives from. */
export interface RoutingResultsViewInput {
    paths: Path[]
    selectedPath: Path
    currentRequest: CurrentRequest
    /** Every query point is initialized. */
    allPointsSet: boolean
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
    | { kind: 'routes'; tabs: RouteTab[]; activeIndex: number }

/**
 * Total function: every (paths, currentRequest, selectedPath) triple maps to exactly one variant.
 *
 * Routes beats loading, so existing paths stay visible while alternatives stream in. Loading beats
 * empty, so a pending alternative never flashes "no safe route".
 */
export function selectRoutingResultsView(input: RoutingResultsViewInput): RoutingResultsView {
    const { paths, selectedPath, currentRequest, allPointsSet } = input
    if (paths.length > 0)
        return { kind: 'routes', tabs: buildRouteTabs(paths), activeIndex: activeTabIndex(paths, selectedPath) }
    // Sub requests outlive the route they belonged to, so an emptied point still leaves them behind.
    if (!allPointsSet) return { kind: 'idle' }
    if (hasPendingRequests(currentRequest.subRequests)) return { kind: 'loading' }
    if (currentRequest.subRequests.length === 0) return { kind: 'idle' }
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

export function buildRouteTabs(paths: readonly Path[]): RouteTab[] {
    const counts = new Map<string, number>()
    for (const path of paths) {
        const description = descriptionText(path)
        if (description) counts.set(description, (counts.get(description) ?? 0) + 1)
    }
    return paths.map((path, index) => {
        const description = descriptionText(path)
        const label = description && counts.get(description) === 1 ? description : `Route ${index + 1}`
        return { index, label, path }
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
