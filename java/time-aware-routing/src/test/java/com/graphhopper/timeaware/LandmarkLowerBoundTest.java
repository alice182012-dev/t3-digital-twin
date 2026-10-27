package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.graphhopper.routing.AlgorithmOptions;
import com.graphhopper.routing.Dijkstra;
import com.graphhopper.routing.Path;
import com.graphhopper.routing.RoutingAlgorithm;
import com.graphhopper.routing.ev.DecimalEncodedValue;
import com.graphhopper.routing.ev.DecimalEncodedValueImpl;
import com.graphhopper.routing.ev.Subnetwork;
import com.graphhopper.routing.ev.TurnCost;
import com.graphhopper.routing.lm.LMApproximator;
import com.graphhopper.routing.lm.LMConfig;
import com.graphhopper.routing.lm.LMRoutingAlgorithmFactory;
import com.graphhopper.routing.lm.LandmarkStorage;
import com.graphhopper.routing.lm.PrepareLandmarks;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.routing.weighting.SpeedWeighting;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.DAType;
import com.graphhopper.storage.Directory;
import com.graphhopper.storage.GHDirectory;
import com.graphhopper.util.EdgeIteratorState;
import com.graphhopper.util.Parameters;
import com.graphhopper.util.RandomGraph;
import java.util.function.DoubleUnaryOperator;
import org.junit.jupiter.api.Test;

/**
 * A weighting that only raises edge weights keeps the landmark (LM) lower bounds valid. This is the question of
 * US-049: if it fails, the time-aware search must run without LM.
 * <p>
 * The graphs are the random graphs of GraphHopper's own LMApproximatorTest. The landmarks are prepared with the
 * stock speed weighting, and the search runs with a decorated weighting, as the engine will.
 */
class LandmarkLowerBoundTest {

    private static final long[] SEEDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};

    /** Scales every edge weight by a factor that depends on the edge id. Turn costs and millis pass through. */
    static final class ScaledWeighting implements Weighting {
        private final Weighting base;
        private final DoubleUnaryOperator factorOfEdge;

        ScaledWeighting(Weighting base, DoubleUnaryOperator factorOfEdge) {
            this.base = base;
            this.factorOfEdge = factorOfEdge;
        }

        @Override
        public double calcMinWeightPerDistance() {
            return base.calcMinWeightPerDistance();
        }

        @Override
        public double calcEdgeWeight(EdgeIteratorState edgeState, boolean reverse) {
            return base.calcEdgeWeight(edgeState, reverse) * factorOfEdge.applyAsDouble(edgeState.getEdge());
        }

        @Override
        public long calcEdgeMillis(EdgeIteratorState edgeState, boolean reverse) {
            return base.calcEdgeMillis(edgeState, reverse);
        }

        @Override
        public double calcTurnWeight(int inEdge, int viaNode, int outEdge) {
            return base.calcTurnWeight(inEdge, viaNode, outEdge);
        }

        @Override
        public long calcTurnMillis(int inEdge, int viaNode, int outEdge) {
            return base.calcTurnMillis(inEdge, viaNode, outEdge);
        }

        @Override
        public boolean hasTurnCosts() {
            return base.hasTurnCosts();
        }

        @Override
        public String getName() {
            return base.getName();
        }
    }

    private static final DoubleUnaryOperator RAISE_1_TO_5 = edge -> 1 + (int) edge % 5;
    private static final DoubleUnaryOperator CLOSE_SOME = edge -> (int) edge % 7 == 0 ? Double.POSITIVE_INFINITY : 1;
    private static final DoubleUnaryOperator LOWER = edge -> 0.5;

    /** A prepared random graph. */
    private static final class Fixture {
        final BaseGraph graph;
        final DecimalEncodedValue speedEnc;
        final Weighting base;
        final PrepareLandmarks prepare;

        Fixture(long seed) {
            Directory dir = new GHDirectory("", DAType.RAM);
            speedEnc = new DecimalEncodedValueImpl("speed", 5, 5, true);
            EncodingManager em = new EncodingManager.Builder()
                    .add(speedEnc).addTurnCostEncodedValue(TurnCost.create("car", 1)).add(Subnetwork.create("car")).build();
            graph = new BaseGraph.Builder(em).setDir(dir).withTurnCosts(true).create();
            RandomGraph.start().seed(seed).nodes(50).curviness(0.1).speedZero(0.1).fill(graph, speedEnc);
            base = new SpeedWeighting(speedEnc);
            prepare = new PrepareLandmarks(dir, graph, em, new LMConfig("car", base), 16);
            prepare.setMaximumWeight(10000);
            prepare.doWork();
        }

        LandmarkStorage landmarks() {
            return prepare.getLandmarkStorage();
        }
    }

    /** Counts the nodes where the LM estimate to t is higher than the real weight under the routing weighting. */
    private static int overEstimates(Fixture f, Weighting routing) {
        int count = 0;
        for (int t = 0; t < f.graph.getNodes(); t++) {
            LMApproximator approximator = new LMApproximator(f.graph, f.base, routing, f.landmarks(), 8, false);
            approximator.setTo(t);
            for (int v = 0; v < f.graph.getNodes(); v++) {
                Path path = new Dijkstra(f.graph, routing, TraversalMode.NODE_BASED).calcPath(v, t);
                if (!path.isFound()) continue;
                // GraphHopper's own test allows 10 mm per edge, because a stored edge distance can be rounded down.
                double slack = path.getEdgeCount() * (10 / 1000.0);
                if (approximator.approximate(v) - slack > path.getWeight()) count++;
            }
        }
        return count;
    }

    @Test
    void estimatesStayBelowTheRealWeightWhenWeightsOnlyRise() {
        for (long seed : SEEDS) {
            Fixture f = new Fixture(seed);
            assertEquals(0, overEstimates(f, new ScaledWeighting(f.base, RAISE_1_TO_5)), "seed " + seed);
        }
    }

    @Test
    void estimatesStayBelowTheRealWeightWhenEdgesAreClosed() {
        for (long seed : SEEDS) {
            Fixture f = new Fixture(seed);
            assertEquals(0, overEstimates(f, new ScaledWeighting(f.base, CLOSE_SOME)), "seed " + seed);
        }
    }

    @Test
    void theCheckCatchesAWeightingThatLowersWeights() {
        int total = 0;
        for (long seed : SEEDS) {
            Fixture f = new Fixture(seed);
            total += overEstimates(f, new ScaledWeighting(f.base, LOWER));
        }
        assertTrue(total > 0, "a lowering weighting must break the bounds, or this test checks nothing");
    }

    /** The search the engine will run: LM A* with a raised weighting must find the weight Dijkstra finds. */
    private static void assertSearchMatchesDijkstra(DoubleUnaryOperator factor, String algorithm) {
        for (long seed : SEEDS) {
            Fixture f = new Fixture(seed);
            Weighting routing = new ScaledWeighting(f.base, factor);
            LMRoutingAlgorithmFactory lm = new LMRoutingAlgorithmFactory(f.landmarks());
            AlgorithmOptions options = new AlgorithmOptions()
                    .setAlgorithm(algorithm).setTraversalMode(TraversalMode.NODE_BASED);
            for (int from = 0; from < f.graph.getNodes(); from += 3) {
                for (int to = 1; to < f.graph.getNodes(); to += 4) {
                    RoutingAlgorithm lmSearch = lm.createAlgo(f.graph, routing, options);
                    Path viaLm = lmSearch.calcPath(from, to);
                    Path viaDijkstra = new Dijkstra(f.graph, routing, TraversalMode.NODE_BASED).calcPath(from, to);
                    String at = "seed " + seed + " " + from + "->" + to;
                    assertEquals(viaDijkstra.isFound(), viaLm.isFound(), at);
                    if (viaDijkstra.isFound()) assertEquals(viaDijkstra.getWeight(), viaLm.getWeight(), 1e-6, at);
                }
            }
        }
    }

    @Test
    void lmAStarFindsTheDijkstraWeightWithRaisedWeights() {
        assertSearchMatchesDijkstra(RAISE_1_TO_5, Parameters.Algorithms.ASTAR);
        assertSearchMatchesDijkstra(RAISE_1_TO_5, Parameters.Algorithms.ASTAR_BI);
    }

    @Test
    void lmAStarFindsTheDijkstraWeightWithClosedEdges() {
        assertSearchMatchesDijkstra(CLOSE_SOME, Parameters.Algorithms.ASTAR);
        assertSearchMatchesDijkstra(CLOSE_SOME, Parameters.Algorithms.ASTAR_BI);
    }
}
