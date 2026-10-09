package com.graphhopper.timeaware;

import java.time.Instant;
import java.util.List;

/**
 * The sticky closure rule of US-050 (the Java form of StickyClosure in scripts/routing_reference/sticky_reference.py).
 * An edge is closed for an arrival when some forecast step in [window start, arrival + margin] has a depth at or above
 * the vehicle's limit. Steps before the window start are ignored, so water that drained before the trip does not close a
 * road. The end of the window is included. The router starts the window at the step that contains the departure and
 * measures every arrival from the departure itself (US-096), so the two are separate times. A closure only grows with the
 * arrival time, so an earlier arrival is never worse. An edge outside the table reads as clear.
 */
public final class StickyClosure {

    /** The 10 minutes of the PRD, fixed on the server. */
    public static final long DEFAULT_MARGIN_MS = 10 * 60_000L;

    private final EdgeDepthTable table;
    private final int limitCm;
    private final long windowStartMs;
    private final long departureMs;
    private final long marginMs;
    private final long[] stepMs;

    /** A departure that is also the start of the window. */
    public StickyClosure(EdgeDepthTable table, int limitCm, long departureEpochMs, long marginMs) {
        this(table, limitCm, departureEpochMs, departureEpochMs, marginMs);
    }

    public StickyClosure(EdgeDepthTable table, int limitCm, long windowStartEpochMs, long departureEpochMs, long marginMs) {
        if (marginMs < 0) throw new IllegalArgumentException("the margin cannot be negative");
        this.table = table;
        this.limitCm = limitCm;
        this.windowStartMs = windowStartEpochMs;
        this.departureMs = departureEpochMs;
        this.marginMs = marginMs;
        List<Instant> times = table.stepTimes();
        stepMs = new long[times.size()];
        for (int i = 0; i < stepMs.length; i++) stepMs[i] = times.get(i).toEpochMilli();
    }

    public int limitCm() {
        return limitCm;
    }

    /** The first forecast step the closure counts. */
    public long windowStartEpochMs() {
        return windowStartMs;
    }

    /** The time the trip starts. Every arrival is this plus the time travelled. */
    public long departureEpochMs() {
        return departureMs;
    }

    public EdgeDepthTable table() {
        return table;
    }

    /** True when the road is closed for a traveller who enters it at arrivalEpochMs. */
    public boolean closed(int edgeId, long arrivalEpochMs) {
        if (edgeId < 0 || edgeId >= table.edgeCount()) return false;
        long end = arrivalEpochMs + marginMs;
        for (int step = 0; step < stepMs.length; step++) {
            if (stepMs[step] > end) return false;
            if (stepMs[step] >= windowStartMs && table.depthCm(edgeId, step) >= limitCm) return true;
        }
        return false;
    }
}
