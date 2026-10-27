package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.graphhopper.routing.Dijkstra;
import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.storage.BaseGraph;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The independent re-walk of a route (US-050). It mirrors find_crossings in scripts/routing_reference/sticky_reference.py. */
class StickyCheckerTest {

    @org.junit.jupiter.api.AfterEach
    void closeGraphs() {
        TimeAwareDijkstraTest.closeAll();
    }

    private static final long T0 = TimeAwareDijkstraTest.T0.toEpochMilli();
    private static final long MIN = 60_000L;

    private static StickyClosure rule(Path dir, int floodedEdge, int[][] wet) throws Exception {
        return new StickyClosure(TimeAwareDijkstraTest.table(dir, 3, floodedEdge, 50, wet), 20, T0, StickyClosure.DEFAULT_MARGIN_MS);
    }

    @Test
    void aRouteOverDryRoadsHasNoCrossing(@TempDir Path dir) throws Exception {
        assertEquals(List.of(), StickyChecker.findCrossings(List.of(0, 1, 2), List.of(5 * MIN, 5 * MIN, 5 * MIN), rule(dir, 1, new int[][] {})));
    }

    @Test
    void aRoadThatRisesBeforeArrivalIsACrossing(@TempDir Path dir) throws Exception {
        // Edge 1 is entered at minute 15 and is wet from minute 10, so the step at 15 is inside the window.
        List<StickyChecker.Crossing> found = StickyChecker.findCrossings(
                List.of(0, 1, 2), List.of(15 * MIN, MIN, MIN), rule(dir, 1, new int[][] {{10, 1000}}));

        assertEquals(1, found.size());
        assertEquals(1, found.get(0).position());
        assertEquals(1, found.get(0).edgeId());
        assertEquals(T0 + 15 * MIN, found.get(0).arrivalEpochMs());
    }

    @Test
    void arrivalAddsUpTheTimeOfTheEdgesBeforeIt(@TempDir Path dir) throws Exception {
        // Wet at minute 45 only. Entered at minute 15 it passes, entered at minute 35 it does not.
        StickyClosure rule = rule(dir, 1, new int[][] {{45, 45}});
        assertEquals(0, StickyChecker.findCrossings(List.of(0, 1), List.of(15 * MIN, MIN), rule).size());
        assertEquals(1, StickyChecker.findCrossings(List.of(0, 1), List.of(35 * MIN, MIN), rule).size());
    }

    @Test
    void theWalkStartsAtTheDepartureAndNotAtTheFlooredStep(@TempDir Path dir) throws Exception {
        // Wet from the step at 1,800 s. Requested at 840 s, floored to 0 s, the road entered 1,000 s into the trip.
        // From 0 s the entry would be at 1,000 s with the window [0, 1600 s], and the road would pass.
        StickyClosure rule = new StickyClosure(TimeAwareDijkstraTest.table(dir, 3, 1, 50, new int[][] {{30, 1000}}), 20,
                T0, T0 + 840_000L, StickyClosure.DEFAULT_MARGIN_MS);

        List<StickyChecker.Crossing> found = StickyChecker.findCrossings(List.of(0, 1), List.of(1_000_000L, MIN), rule);

        assertEquals(List.of(new StickyChecker.Crossing(1, 1, T0 + 1_840_000L)), found);
    }

    @Test
    void everyCrossingIsReported(@TempDir Path dir) throws Exception {
        StickyClosure rule = new StickyClosure(
                TestTables.table(dir, "t.bin", 3, TestTables.quarterHours(TimeAwareDijkstraTest.T0, 8), (e, s) -> e == 2 ? 0 : 50),
                20, T0, StickyClosure.DEFAULT_MARGIN_MS);

        assertEquals(2, StickyChecker.findCrossings(List.of(0, 1, 2), List.of(MIN, MIN, MIN), rule).size());
    }

    @Test
    void edgesAndTimesMustLineUp(@TempDir Path dir) throws Exception {
        assertThrows(IllegalArgumentException.class,
                () -> StickyChecker.findCrossings(List.of(0, 1), List.of(MIN), rule(dir, 1, new int[][] {})));
    }

    @Test
    void aNegativeTravelTimeIsRefused(@TempDir Path dir) throws Exception {
        assertThrows(IllegalArgumentException.class,
                () -> StickyChecker.findCrossings(List.of(0), List.of(-1L), rule(dir, 1, new int[][] {})));
    }

    // On the scenarios: the time-aware route has no crossing, and the plain shortest route crosses in the blocked ones.

    @Test
    void theTimeAwareRouteHasNoCrossingAndThePlainRouteCrossesInTheBlockedScenarios(@TempDir Path dir) throws Exception {
        int blockedWherePlainCrosses = 0;
        for (TimeAwareDijkstraTest.Scenario s : TimeAwareDijkstraTest.SCENARIOS) {
            for (int limit : new int[] {20, 30}) {
                BaseGraph g = TimeAwareDijkstraTest.newGraph();
                TimeAwareDijkstraTest.road(g, 0, 1, s.arrivalMin());
                int corridor = TimeAwareDijkstraTest.road(g, 1, 2, 1);
                TimeAwareDijkstraTest.road(g, 2, 3, 1);
                TimeAwareDijkstraTest.road(g, 0, 4, s.arrivalMin() + 6);
                TimeAwareDijkstraTest.road(g, 4, 3, s.arrivalMin() + 6);
                var weighting = TimeAwareDijkstraTest.plain(g);
                StickyClosure closure = new StickyClosure(
                        TimeAwareDijkstraTest.table(dir, g.getEdges(), corridor, 50, s.wet()), limit, T0, StickyClosure.DEFAULT_MARGIN_MS);

                var aware = new TimeAwareDijkstra(g, weighting, TraversalMode.NODE_BASED, closure).calcPath(0, 3);
                var plain = new Dijkstra(g, weighting, TraversalMode.NODE_BASED).calcPath(0, 3);

                assertEquals(0, StickyChecker.findCrossings(aware, weighting, closure).size(), s.name());
                int crossings = StickyChecker.findCrossings(plain, weighting, closure).size();
                if (s.blocked()) {
                    assertTrue(crossings > 0, s.name() + " limit " + limit + ": the plain route must cross the closed road");
                    blockedWherePlainCrosses++;
                } else {
                    assertEquals(0, crossings, s.name());
                }
            }
        }
        assertEquals(4, blockedWherePlainCrosses);
    }
}
