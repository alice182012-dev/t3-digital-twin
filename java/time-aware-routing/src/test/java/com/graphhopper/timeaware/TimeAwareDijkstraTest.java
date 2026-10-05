package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.graphhopper.routing.ev.DecimalEncodedValue;
import com.graphhopper.routing.ev.DecimalEncodedValueImpl;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.routing.weighting.SpeedWeighting;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.util.EdgeIteratorState;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.function.IntToDoubleFunction;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The time-aware search of US-050 on small graphs with exact times (a road's length is chosen so that it takes whole minutes).
 * The four scenarios are the rows of scripts/routing_reference/scenarios.py.
 */
class TimeAwareDijkstraTest {

    static final Instant T0 = Instant.parse("2026-10-05T10:00:00Z");
    static final double METRES_PER_MINUTE = 5400; // SpeedWeighting takes millis = distance / speed * 1000, so 90 gives 5,400 m per minute

    private static final java.util.Map<BaseGraph, DecimalEncodedValue> SPEEDS = new java.util.IdentityHashMap<>();

    static BaseGraph newGraph() {
        DecimalEncodedValue speed = new DecimalEncodedValueImpl("speed", 5, 5, true);
        BaseGraph g = new BaseGraph.Builder(new EncodingManager.Builder().add(speed).build()).create();
        SPEEDS.put(g, speed);
        return g;
    }

    static DecimalEncodedValue speed(BaseGraph g) {
        return SPEEDS.get(g);
    }

    /** An undirected road of `minutes` at 90 km/h. Returns its edge id. */
    static int road(BaseGraph g, int a, int b, double minutes) {
        EdgeIteratorState e = g.edge(a, b).setDistance(minutes * METRES_PER_MINUTE).set(speed(g), 90, 90);
        return e.getEdge();
    }

    /** Scales the weight of chosen edges and leaves the time alone, as a priority factor would. */
    static Weighting weighted(BaseGraph g, IntToDoubleFunction factorOfEdge) {
        SpeedWeighting base = new SpeedWeighting(speed(g));
        return new LandmarkLowerBoundTest.ScaledWeighting(base, edge -> factorOfEdge.applyAsDouble((int) edge));
    }

    static Weighting plain(BaseGraph g) {
        return new SpeedWeighting(speed(g));
    }

    /** Depth `cm` on `edge` at the steps whose minute is in the ranges, 0 elsewhere. Steps: minutes 0, 15 ... 105. */
    static EdgeDepthTable table(Path dir, int edges, int floodedEdge, int cm, int[][] wetMinuteRanges) throws Exception {
        return TestTables.table(dir, "t.bin", edges, TestTables.quarterHours(T0, 8), (edge, step) -> {
            if (edge != floodedEdge) return 0;
            int minute = step * 15;
            for (int[] r : wetMinuteRanges) if (r[0] <= minute && minute <= r[1]) return cm;
            return 0;
        });
    }

    static com.graphhopper.routing.Path search(BaseGraph g, Weighting w, EdgeDepthTable t, int limit, int from, int to) {
        StickyClosure closure = new StickyClosure(t, limit, T0.toEpochMilli(), StickyClosure.DEFAULT_MARGIN_MS);
        return new TimeAwareDijkstra(g, w, TraversalMode.NODE_BASED, closure).calcPath(from, to);
    }

    @Test
    void aRoadOfOneMinuteTakesSixtyThousandMillis() {
        BaseGraph g = newGraph();
        road(g, 0, 1, 1);
        var it = g.createEdgeExplorer().setBaseNode(0);
        it.next();

        assertEquals(60_000L, plain(g).calcEdgeMillis(it, false));
    }

    // The four scenarios.

    record Scenario(String name, boolean far, int arrivalMin, int[][] wet, boolean blocked) {
    }

    static final Scenario[] SCENARIOS = {
        new Scenario("1. Rises before arrival", false, 15, new int[][] {{10, 1000}}, true),
        new Scenario("2. Rises after passing", false, 15, new int[][] {{45, 1000}}, false),
        new Scenario("3. Flooded and drains", false, 25, new int[][] {{0, 20}}, true),
        new Scenario("4. Far road floods late", true, 30, new int[][] {{45, 1000}}, false),
    };

    /** O -lead- A -corridor- B -rest- D, and with a detour O -- X -- D that is longer. Edge 1 is the corridor road. */
    private static com.graphhopper.routing.Path runScenario(Path dir, Scenario s, int limit, int depthCm, boolean detour)
            throws Exception {
        BaseGraph g = newGraph();
        double lead = s.arrivalMin();
        int e0 = road(g, 0, 1, lead);
        int corridor = road(g, 1, 2, 1);
        int e2 = road(g, 2, 3, 1);
        assertEquals(1, corridor);
        if (detour) {
            road(g, 0, 4, lead + 6);
            road(g, 4, 3, lead + 6);
        }
        EdgeDepthTable table = table(dir, g.getEdges(), corridor, depthCm, s.wet());
        return search(g, plain(g), table, limit, 0, 3);
    }

    private static boolean usesCorridor(com.graphhopper.routing.Path p) {
        return p.calcEdges().stream().anyMatch(e -> e.getEdge() == 1);
    }

    @Test
    void theFourScenariosGiveTheStickyColumnForMotorbikeAndCarWithAndWithoutADetour(@TempDir Path dir) throws Exception {
        int checked = 0;
        for (Scenario s : SCENARIOS) {
            for (int limit : new int[] {20, 30}) {
                for (boolean detour : new boolean[] {true, false}) {
                    com.graphhopper.routing.Path p = runScenario(dir, s, limit, 50, detour);
                    String at = s.name() + " limit " + limit + (detour ? " with detour" : " without detour");
                    if (!s.blocked()) {
                        assertTrue(p.isFound() && usesCorridor(p), at + ": must use the corridor road");
                    } else if (detour) {
                        assertTrue(p.isFound() && !usesCorridor(p), at + ": must go round");
                    } else {
                        assertFalse(p.isFound(), at + ": must find no route");
                    }
                    checked++;
                }
            }
        }
        assertEquals(16, checked);
    }

    @Test
    void theLimitDecidesWhichVehicleIsBlocked(@TempDir Path dir) throws Exception {
        Scenario rises = SCENARIOS[0];
        // 25 cm is over the motorbike limit (20) and under the car limit (30).
        assertFalse(usesCorridor(runScenario(dir, rises, 20, 25, true)), "motorbike goes round");
        assertTrue(usesCorridor(runScenario(dir, rises, 30, 25, true)), "car passes");
    }

    @Test
    void theRouteGoesRoundAtTheCostOfTheLongerWay(@TempDir Path dir) throws Exception {
        com.graphhopper.routing.Path p = runScenario(dir, SCENARIOS[0], 20, 50, true);

        assertEquals(2, p.getEdgeCount());
        assertEquals(2 * (15 + 6) * 600.0, p.getWeight(), 1.0); // SpeedWeighting weighs a minute as 600
    }

    // Weight and time can disagree. Only a search that keeps the early label gets this right.

    @Test
    void aHeavierLabelThatArrivesEarlierIsKept(@TempDir Path dir) throws Exception {
        // S=0 P=1 Q=2 M=3 T=4. Via P: light (weight x0.1) but slow, 40 minutes to M. Via Q: 10 minutes to M.
        // The road M-T closes for an arrival at minute 40 (a step at minute 45 is inside the window) and not at minute 10.
        BaseGraph g = newGraph();
        int sp = road(g, 0, 1, 20);
        int pm = road(g, 1, 3, 20);
        int sq = road(g, 0, 2, 5);
        int qm = road(g, 2, 3, 5);
        int mt = road(g, 3, 4, 5);
        Weighting w = weighted(g, edge -> (edge == sp || edge == pm) ? 0.1 : 1.0);
        EdgeDepthTable table = table(dir, g.getEdges(), mt, 50, new int[][] {{45, 1000}});

        com.graphhopper.routing.Path p = search(g, w, table, 20, 0, 4);

        assertTrue(p.isFound(), "the route over Q reaches T in time");
        List<Integer> ids = new ArrayList<>();
        p.calcEdges().forEach(e -> ids.add(e.getEdge()));
        assertEquals(List.of(sq, qm, mt), ids);
    }

    @Test
    void theLighterRouteWinsWhenBothArriveInTime(@TempDir Path dir) throws Exception {
        BaseGraph g = newGraph();
        int sp = road(g, 0, 1, 20);
        int pm = road(g, 1, 3, 20);
        int sq = road(g, 0, 2, 5);
        int qm = road(g, 2, 3, 5);
        int mt = road(g, 3, 4, 5);
        Weighting w = weighted(g, edge -> (edge == sp || edge == pm) ? 0.1 : 1.0);
        EdgeDepthTable table = table(dir, g.getEdges(), mt, 50, new int[][] {});

        List<Integer> ids = new ArrayList<>();
        search(g, w, table, 20, 0, 4).calcEdges().forEach(e -> ids.add(e.getEdge()));

        assertEquals(List.of(sp, pm, mt), ids);
    }

    @Test
    void aTripFromANodeToItselfIsEmptyAndFound(@TempDir Path dir) throws Exception {
        BaseGraph g = newGraph();
        road(g, 0, 1, 5);
        com.graphhopper.routing.Path p = search(g, plain(g), table(dir, 1, 0, 50, new int[][] {{0, 1000}}), 20, 0, 0);

        assertTrue(p.isFound());
        assertEquals(0, p.getEdgeCount());
    }

    @Test
    void aClosedFirstRoadBlocksTheTripAtTheOrigin(@TempDir Path dir) throws Exception {
        BaseGraph g = newGraph();
        road(g, 0, 1, 5);
        assertFalse(search(g, plain(g), table(dir, 1, 0, 50, new int[][] {{0, 1000}}), 20, 0, 1).isFound());
    }

    @Test
    void anUnreachableDestinationGivesNoRoute(@TempDir Path dir) throws Exception {
        BaseGraph g = newGraph();
        road(g, 0, 1, 5);
        g.getNodeAccess().setNode(2, 0, 0);
        assertFalse(search(g, plain(g), table(dir, 1, 0, 0, new int[][] {}), 20, 0, 2).isFound());
    }

    @Test
    void theTripStartsAtTheDepartureTime(@TempDir Path dir) throws Exception {
        // Road is wet at minute 0 only. A trip that leaves at minute 30 ignores that.
        BaseGraph g = newGraph();
        road(g, 0, 1, 5);
        EdgeDepthTable table = table(dir, 1, 0, 50, new int[][] {{0, 0}});
        StickyClosure late = new StickyClosure(table, 20, T0.toEpochMilli() + 30 * 60_000L, StickyClosure.DEFAULT_MARGIN_MS);

        assertTrue(new TimeAwareDijkstra(g, plain(g), TraversalMode.NODE_BASED, late).calcPath(0, 1).isFound());
        assertFalse(search(g, plain(g), table, 20, 0, 1).isFound());
    }

    // An exhaustive search over all simple paths is the oracle.

    @Test
    void theSearchMatchesBruteForceOnRandomGraphs(@TempDir Path dir) throws Exception {
        int withRoute = 0;
        int withoutRoute = 0;
        for (long seed = 0; seed < 300; seed++) {
            Random rnd = new Random(seed);
            int nodes = 4 + rnd.nextInt(5);
            BaseGraph g = newGraph();
            List<int[]> ends = new ArrayList<>();
            List<Double> minutes = new ArrayList<>();
            for (int i = 1; i < nodes; i++) { // a spanning tree, so most pairs connect
                ends.add(new int[] {rnd.nextInt(i), i});
                minutes.add(1.0 + rnd.nextInt(30));
            }
            for (int extra = rnd.nextInt(nodes + 2); extra > 0; extra--) {
                int a = rnd.nextInt(nodes);
                int b = rnd.nextInt(nodes);
                if (a == b) continue;
                ends.add(new int[] {a, b});
                minutes.add(1.0 + rnd.nextInt(30));
            }
            double[] factor = new double[ends.size()];
            for (int i = 0; i < ends.size(); i++) {
                road(g, ends.get(i)[0], ends.get(i)[1], minutes.get(i));
                factor[i] = 0.2 + rnd.nextInt(10) / 5.0;
            }
            int edgeCount = ends.size();
            boolean[][] wet = new boolean[edgeCount][8];
            for (int e = 0; e < edgeCount; e++) for (int s = 0; s < 8; s++) wet[e][s] = rnd.nextInt(5) == 0;
            EdgeDepthTable table = TestTables.table(dir, "r" + seed + ".bin", edgeCount, TestTables.quarterHours(T0, 8),
                    (e, s) -> wet[e][s] ? 50 : 0);
            Weighting w = weighted(g, e -> factor[e]);
            StickyClosure closure = new StickyClosure(table, 20, T0.toEpochMilli(), StickyClosure.DEFAULT_MARGIN_MS);

            int from = rnd.nextInt(nodes);
            int to = rnd.nextInt(nodes);
            double expected = bruteForce(g, w, closure, from, to);
            com.graphhopper.routing.Path got = new TimeAwareDijkstra(g, w, TraversalMode.NODE_BASED, closure).calcPath(from, to);

            String at = "seed " + seed + " " + from + "->" + to;
            assertEquals(expected < Double.POSITIVE_INFINITY, got.isFound(), at);
            if (got.isFound()) {
                assertEquals(expected, got.getWeight(), 1e-6, at);
                withRoute++;
            } else {
                withoutRoute++;
            }
        }
        assertTrue(withRoute > 60 && withoutRoute > 5, "the random graphs must cover both outcomes: " + withRoute + "/" + withoutRoute);
    }

    /** Lightest weight over all simple paths that enter no road while it is closed. */
    private static double bruteForce(BaseGraph g, Weighting w, StickyClosure closure, int from, int to) {
        double[] best = {Double.POSITIVE_INFINITY};
        walk(g, w, closure, from, to, new boolean[g.getNodes()], 0, 0, best);
        return best[0];
    }

    private static void walk(BaseGraph g, Weighting w, StickyClosure closure, int node, int to, boolean[] seen, double weight,
            long elapsedMs, double[] best) {
        if (node == to) {
            best[0] = Math.min(best[0], weight);
            return;
        }
        seen[node] = true;
        var it = g.createEdgeExplorer().setBaseNode(node);
        while (it.next()) {
            if (seen[it.getAdjNode()]) continue;
            if (closure.closed(it.getEdge(), closure.departureEpochMs() + elapsedMs)) continue;
            walk(g, w, closure, it.getAdjNode(), to, seen, weight + w.calcEdgeWeight(it, false),
                    elapsedMs + w.calcEdgeMillis(it, false), best);
        }
        seen[node] = false;
    }
}
