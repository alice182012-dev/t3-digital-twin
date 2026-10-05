package com.graphhopper.timeaware;

import com.graphhopper.routing.querygraph.VirtualEdgeIteratorState;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.GHUtility;

/** The id of the real graph edge behind an edge state, which is what the edge depth table is indexed by. */
final class EdgeIds {

    private EdgeIds() {
    }

    /** A snap in the middle of an edge splits it into virtual edges. Their depth is the depth of the edge they came from. */
    static int original(EdgeIteratorState edge) {
        if (edge instanceof VirtualEdgeIteratorState virtual) {
            return GHUtility.getEdgeFromEdgeKey(virtual.getOriginalEdgeKey());
        }
        return edge.getEdge();
    }
}
