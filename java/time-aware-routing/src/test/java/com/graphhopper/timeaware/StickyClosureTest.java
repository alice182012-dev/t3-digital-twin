package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The closure rule of US-050, with the cases of scripts/routing_reference/test_sticky_reference.py. */
class StickyClosureTest {

    static final Instant T0 = Instant.parse("2026-10-05T10:00:00Z");
    static final long MIN = 60_000L;

    /** Edge 0 is flooded to `cm` at the minutes in `wetMinutes`. Steps are at minutes 0, 15, 30, ... 105. */
    private static StickyClosure rule(Path dir, int limitCm, long departureMinute, int cm, int... wetMinutes) throws Exception {
        EdgeDepthTable table = TestTables.table(dir, "t.bin", 2, TestTables.quarterHours(T0, 8), (edge, step) -> {
            if (edge != 0) return 0;
            for (int m : wetMinutes) if (m == step * 15) return cm;
            return 0;
        });
        return new StickyClosure(table, limitCm, T0.toEpochMilli() + departureMinute * MIN, 10 * 60_000L);
    }

    private static long at(long minute) {
        return T0.toEpochMilli() + minute * MIN;
    }

    @Test
    void aDryRoadIsOpen(@TempDir Path dir) throws Exception {
        assertFalse(rule(dir, 20, 0, 50).closed(0, at(30)));
    }

    @Test
    void aRoadThatFloodsInsideTheWindowIsClosed(@TempDir Path dir) throws Exception {
        // arrival at minute 15, margin 10: window is minutes 0 to 25, and the road is wet at minute 15.
        assertTrue(rule(dir, 20, 0, 50, 15).closed(0, at(15)));
    }

    @Test
    void aRoadThatFloodsAfterTheWindowIsOpen(@TempDir Path dir) throws Exception {
        assertFalse(rule(dir, 20, 0, 50, 45).closed(0, at(15)));
    }

    @Test
    void theEndOfTheWindowIsIncluded(@TempDir Path dir) throws Exception {
        StickyClosure rule = rule(dir, 20, 0, 50, 30);
        assertTrue(rule.closed(0, at(20)));   // window ends at minute 30 exactly
        assertFalse(rule.closed(0, at(20) - 1));
    }

    @Test
    void waterThatDrainedBeforeDepartureDoesNotCloseTheRoad(@TempDir Path dir) throws Exception {
        StickyClosure rule = rule(dir, 20, 30, 50, 0, 15);
        assertFalse(rule.closed(0, at(35)));
    }

    @Test
    void aStepAtTheDepartureCounts(@TempDir Path dir) throws Exception {
        assertTrue(rule(dir, 20, 30, 50, 30).closed(0, at(30)));
    }

    @Test
    void floodedThenDrainedStaysClosedForALaterArrivalInsideTheSameWindow(@TempDir Path dir) throws Exception {
        StickyClosure rule = rule(dir, 20, 0, 50, 0);
        assertTrue(rule.closed(0, at(5)));
        assertTrue(rule.closed(0, at(40)));
    }

    @Test
    void theLimitDecidesWhichVehicleIsBlocked(@TempDir Path dir) throws Exception {
        // 25 cm: over the motorbike limit of 20, under the car limit of 30.
        assertTrue(rule(dir, 20, 0, 25, 15).closed(0, at(15)));
        assertFalse(rule(dir, 30, 0, 25, 15).closed(0, at(15)));
    }

    @Test
    void aDepthEqualToTheLimitClosesTheRoad(@TempDir Path dir) throws Exception {
        assertTrue(rule(dir, 20, 0, 20, 15).closed(0, at(15)));
        assertFalse(rule(dir, 20, 0, 19, 15).closed(0, at(15)));
    }

    @Test
    void anEdgeOutsideTheTableReadsAsClear(@TempDir Path dir) throws Exception {
        assertFalse(rule(dir, 20, 0, 50, 15).closed(999, at(15)));
        assertFalse(rule(dir, 20, 0, 50, 15).closed(-1, at(15)));
    }

    @Test
    void closureOnlyGrowsWithArrivalTime(@TempDir Path dir) throws Exception {
        StickyClosure rule = rule(dir, 20, 0, 50, 45, 60);
        boolean closedBefore = false;
        for (long m = 0; m <= 100; m++) {
            boolean closed = rule.closed(0, at(m));
            assertTrue(closed || !closedBefore, "reopened at minute " + m);
            closedBefore = closed;
        }
    }

    @Test
    void aNegativeMarginIsRefused(@TempDir Path dir) throws Exception {
        EdgeDepthTable table = TestTables.table(dir, "t.bin", 1, TestTables.quarterHours(T0, 2), (e, s) -> 0);
        assertThrows(IllegalArgumentException.class, () -> new StickyClosure(table, 20, 0, -1));
        assertEquals(10 * 60_000L, StickyClosure.DEFAULT_MARGIN_MS);
    }
}
