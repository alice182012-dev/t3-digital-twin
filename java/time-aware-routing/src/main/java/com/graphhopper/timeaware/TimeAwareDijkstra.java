package com.graphhopper.timeaware;

import com.carrotsearch.hppc.IntObjectMap;
import com.graphhopper.coll.GHIntObjectHashMap;
import com.graphhopper.routing.AbstractRoutingAlgorithm;
import com.graphhopper.routing.Path;
import com.graphhopper.routing.PathExtractor;
import com.graphhopper.routing.SPTEntry;
import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.storage.Graph;
import com.graphhopper.util.EdgeIterator;
import com.graphhopper.util.GHUtility;
import com.graphhopper.util.Parameters;
import java.util.ArrayList;
import java.util.List;
import java.util.PriorityQueue;

/**
 * The time-aware search of US-050: a Dijkstra search whose labels carry the time spent so far, and that does not enter
 * an edge while {@link StickyClosure} says it is closed for the arrival time at that edge.
 * <p>
 * The heap orders by weight. A node can hold several labels, because a label that is lighter but arrives later can
 * pass fewer roads than a heavier one that arrives earlier. A label is dropped only when another label at the same
 * node is no heavier and no later. A closure only grows with the arrival time, so an earlier arrival is never worse,
 * and the first label to reach the target is the lightest route that crosses no closed road. When weight is the
 * travel time each node holds one label and this is plain Dijkstra with closed roads.
 */
public class TimeAwareDijkstra extends AbstractRoutingAlgorithm {

    /** An SPT entry with the milliseconds since the departure. */
    static final class Label extends SPTEntry {
        final long elapsedMs;

        Label(int node, double weight) {
            super(node, weight);
            this.elapsedMs = 0;
        }

        Label(int edge, int adjNode, double weight, Label parent, long elapsedMs) {
            super(edge, adjNode, weight, parent);
            this.elapsedMs = elapsedMs;
        }
    }

    private final StickyClosure closure;
    private final IntObjectMap<List<Label>> labels = new GHIntObjectHashMap<>();
    private final PriorityQueue<Label> heap = new PriorityQueue<>();
    private final int baseEdges;
    private int visitedNodes;

    public TimeAwareDijkstra(Graph graph, Weighting weighting, TraversalMode traversalMode, StickyClosure closure) {
        super(graph, weighting, traversalMode);
        this.closure = closure;
        this.baseEdges = graph.getBaseGraph().getEdges();
    }

    @Override
    public Path calcPath(int from, int to) {
        checkAlreadyRun();
        setupFinishTime();
        Label start = new Label(from, 0);
        heap.add(start);
        Label found = null;
        while (!heap.isEmpty()) {
            Label current = heap.poll();
            if (current.isDeleted()) continue;
            visitedNodes++;
            if (isMaxVisitedNodesExceeded() || isTimeoutExceeded()) break;
            if (current.adjNode == to) {
                found = current;
                break;
            }
            expand(current);
        }
        if (found == null) return createEmptyPath();
        return PathExtractor.extractPath(graph, weighting, found);
    }

    private void expand(Label current) {
        EdgeIterator iter = edgeExplorer.setBaseNode(current.adjNode);
        while (iter.next()) {
            if (!accept(iter, current.edge)) continue;
            double weight = GHUtility.calcWeightWithTurnWeight(weighting, iter, false, current.edge) + current.weight;
            if (Double.isInfinite(weight)) continue;
            long edgeMillis = GHUtility.calcMillisWithTurnMillis(weighting, iter, false, current.edge);
            if (edgeMillis == Long.MAX_VALUE) continue;
            long enterMs = current.elapsedMs;
            if (weighting.hasTurnCosts() && EdgeIterator.Edge.isValid(current.edge)) {
                enterMs += weighting.calcTurnMillis(current.edge, iter.getBaseNode(), iter.getEdge());
            }
            // A virtual edge (a snap in the middle of a road) has an id past the base graph's. Its depth is its road's.
            int roadId = iter.getEdge() < baseEdges ? iter.getEdge() : EdgeIds.original(iter.detach(false));
            if (closure.closed(roadId, closure.departureEpochMs() + enterMs)) continue;

            int key = traversalMode.createTraversalId(iter, false);
            Label next = new Label(iter.getEdge(), iter.getAdjNode(), weight, current, current.elapsedMs + edgeMillis);
            if (keep(key, next)) heap.add(next);
        }
    }

    /** Adds the label unless another one at the same traversal id is no heavier and no later. Drops the ones it beats. */
    private boolean keep(int key, Label candidate) {
        List<Label> here = labels.get(key);
        if (here == null) {
            here = new ArrayList<>(2);
            labels.put(key, here);
        }
        for (Label other : here) {
            if (!other.isDeleted() && other.weight <= candidate.weight && other.elapsedMs <= candidate.elapsedMs) return false;
        }
        for (Label other : here) {
            if (!other.isDeleted() && candidate.weight <= other.weight && candidate.elapsedMs <= other.elapsedMs) {
                other.setDeleted();
            }
        }
        here.removeIf(SPTEntry::isDeleted);
        here.add(candidate);
        return true;
    }

    @Override
    public int getVisitedNodes() {
        return visitedNodes;
    }

    @Override
    public String getName() {
        return "time_aware_dijkstra";
    }
}
