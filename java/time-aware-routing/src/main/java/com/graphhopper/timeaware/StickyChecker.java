package com.graphhopper.timeaware;

import com.graphhopper.routing.Path;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.util.EdgeIteratorState;
import java.util.ArrayList;
import java.util.List;

/**
 * Walks a route edge by edge from the departure time and lists every edge that was closed on entry (US-050). It does not
 * share code with the search, so a fault in the search shows up here. It mirrors find_crossings in
 * scripts/routing_reference/sticky_reference.py.
 */
public final class StickyChecker {

    public record Crossing(int position, int edgeId, long arrivalEpochMs) {
    }

    private StickyChecker() {
    }

    /** edgeMillis holds the travel time of each edge, in the order of edgeIds. */
    public static List<Crossing> findCrossings(List<Integer> edgeIds, List<Long> edgeMillis, StickyClosure rule) {
        if (edgeIds.size() != edgeMillis.size()) {
            throw new IllegalArgumentException(edgeIds.size() + " edges but " + edgeMillis.size() + " travel times");
        }
        List<Crossing> crossings = new ArrayList<>();
        long time = rule.departureEpochMs();
        for (int position = 0; position < edgeIds.size(); position++) {
            long millis = edgeMillis.get(position);
            if (millis < 0) throw new IllegalArgumentException("edge " + edgeIds.get(position) + " has a negative travel time");
            if (rule.closed(edgeIds.get(position), time)) crossings.add(new Crossing(position, edgeIds.get(position), time));
            time += millis;
        }
        return crossings;
    }

    /** The crossings of a path that the engine returned, with the travel times of the weighting that made it. */
    public static List<Crossing> findCrossings(Path path, Weighting weighting, StickyClosure rule) {
        List<Integer> ids = new ArrayList<>();
        List<Long> millis = new ArrayList<>();
        for (EdgeIteratorState edge : path.calcEdges()) {
            ids.add(EdgeIds.original(edge));
            millis.add(weighting.calcEdgeMillis(edge, false));
        }
        return findCrossings(ids, millis, rule);
    }
}
