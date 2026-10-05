package com.graphhopper.timeaware;

import com.graphhopper.routing.Dijkstra;
import com.graphhopper.routing.Path;
import com.graphhopper.routing.ev.DecimalEncodedValue;
import com.graphhopper.routing.ev.DecimalEncodedValueImpl;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.util.TraversalMode;
import com.graphhopper.routing.weighting.SpeedWeighting;
import com.graphhopper.storage.BaseGraph;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.Instant;

/**
 * Runs the four synthetic flood scenarios of routing-not-time-aware.md through the time-aware search (US-050), for the
 * motorbike (limit 20 cm) and the car (30 cm), with and without a detour, and prints one line per run. The rows are the
 * ones in scripts/routing_reference/scenarios.py, and the expected column is the "C-lite, sticky" column of that table.
 * <p>
 * Each scenario floods one road, the corridor road, and sets how long the traveller takes to reach it. A road takes
 * whole minutes: SpeedWeighting divides the length by the speed, so a speed of 90 and a length of 5,400 m is one minute.
 * Exit code 0 means all 16 runs matched and no route crossed a closed road.
 */
public final class ScenarioReport {

    static final Instant T0 = Instant.parse("2026-10-05T10:00:00Z");
    private static final double METRES_PER_MINUTE = 5400;
    private static final int FLOOD_CM = 50;

    record Scenario(String name, int arrivalMin, int firstWetMin, int lastWetMin, boolean blocked) {
    }

    static final Scenario[] SCENARIOS = {
        new Scenario("1. Rises before arrival", 15, 10, Integer.MAX_VALUE, true),
        new Scenario("2. Rises after passing", 15, 45, Integer.MAX_VALUE, false),
        new Scenario("3. Flooded and drains", 25, 0, 20, true),
        new Scenario("4. Far road floods late", 30, 45, Integer.MAX_VALUE, false),
    };

    record Outcome(String observed, String expected, int crossings, int plainRouteCrossings, double routeMinutes) {
        boolean matches() {
            return observed.equals(expected) && crossings == 0;
        }
    }

    private ScenarioReport() {
    }

    public static void main(String[] args) throws IOException {
        System.exit(run(System.out));
    }

    static int run(PrintStream out) throws IOException {
        out.printf("%-26s %-9s %-10s %-9s %-9s %-9s %-9s %s%n", "scenario", "vehicle", "detour", "expected", "observed",
                "crossings", "plain-x", "minutes");
        int bad = 0;
        int runs = 0;
        for (Scenario s : SCENARIOS) {
            for (String vehicle : new String[] {"motorbike", "car"}) {
                int limit = vehicle.equals("motorbike") ? 20 : 30;
                for (boolean detour : new boolean[] {true, false}) {
                    Outcome o = outcome(s, limit, detour);
                    out.printf("%-26s %-9s %-10s %-9s %-9s %-9d %-9d %.1f%s%n", s.name(), vehicle, detour ? "with" : "without",
                            o.expected(), o.observed(), o.crossings(), o.plainRouteCrossings(), o.routeMinutes(),
                            o.matches() ? "" : "   <-- MISMATCH");
                    runs++;
                    if (!o.matches()) bad++;
                }
            }
        }
        out.println(bad == 0 ? "PASS: " + runs + " of " + runs + " runs match the sticky column and no route crosses a closed road"
                : "FAIL: " + bad + " of " + runs + " runs differ");
        return bad == 0 ? 0 : 1;
    }

    /** O -lead- A -corridor- B -rest- D, and with a detour O -- X -- D that takes longer. Edge 1 is the corridor road. */
    static Outcome outcome(Scenario s, int limitCm, boolean detour) throws IOException {
        DecimalEncodedValue speed = new DecimalEncodedValueImpl("speed", 5, 5, true);
        BaseGraph g = new BaseGraph.Builder(new EncodingManager.Builder().add(speed).build()).create();
        road(g, speed, 0, 1, s.arrivalMin());
        road(g, speed, 1, 2, 1);
        road(g, speed, 2, 3, 1);
        if (detour) {
            road(g, speed, 0, 4, s.arrivalMin() + 6);
            road(g, speed, 4, 3, s.arrivalMin() + 6);
        }
        EdgeDepthTable table = table(g.getEdges(), s);
        SpeedWeighting weighting = new SpeedWeighting(speed);
        StickyClosure closure = new StickyClosure(table, limitCm, T0.toEpochMilli(), StickyClosure.DEFAULT_MARGIN_MS);

        Path route = new TimeAwareDijkstra(g, weighting, TraversalMode.NODE_BASED, closure).calcPath(0, 3);
        Path plain = new Dijkstra(g, weighting, TraversalMode.NODE_BASED).calcPath(0, 3);

        String observed = !route.isFound() ? "none" : route.calcEdges().stream().anyMatch(e -> e.getEdge() == 1) ? "corridor" : "detour";
        String expected = !s.blocked() ? "corridor" : detour ? "detour" : "none";
        int crossings = route.isFound() ? StickyChecker.findCrossings(route, weighting, closure).size() : 0;
        int plainCrossings = StickyChecker.findCrossings(plain, weighting, closure).size();
        return new Outcome(observed, expected, crossings, plainCrossings, route.isFound() ? route.getTime() / 60000.0 : 0);
    }

    private static void road(BaseGraph g, DecimalEncodedValue speed, int a, int b, double minutes) {
        g.edge(a, b).setDistance(minutes * METRES_PER_MINUTE).set(speed, 90, 90);
    }

    /** A synthetic table in the format of edge-depth-table-format.md: 8 steps 15 minutes apart, only the corridor road wet. */
    private static EdgeDepthTable table(int edges, Scenario s) throws IOException {
        byte[] hash = "a".repeat(64).getBytes(StandardCharsets.UTF_8);
        byte[] run = "20261005T000000".getBytes(StandardCharsets.UTF_8);
        int steps = 8;
        ByteBuffer buf = ByteBuffer.allocate(16 + hash.length + run.length + 8 * steps + 2 * edges * steps).order(ByteOrder.LITTLE_ENDIAN);
        buf.put(EdgeDepthTable.MAGIC).putShort((short) 1).putShort((short) steps).putInt(edges)
                .putShort((short) hash.length).putShort((short) run.length).put(hash).put(run);
        for (int i = 0; i < steps; i++) buf.putLong(T0.getEpochSecond() + 900L * i);
        for (int e = 0; e < edges; e++) {
            for (int step = 0; step < steps; step++) {
                int minute = step * 15;
                boolean wet = e == 1 && s.firstWetMin() <= minute && minute <= s.lastWetMin();
                buf.putShort((short) (wet ? FLOOD_CM : 0));
            }
        }
        java.nio.file.Path file = Files.createTempFile("scenario-table", ".bin");
        try {
            Files.write(file, buf.array());
            return EdgeDepthTable.open(file);
        } finally {
            Files.deleteIfExists(file);
        }
    }
}
