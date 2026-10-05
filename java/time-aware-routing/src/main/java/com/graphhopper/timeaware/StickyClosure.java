package com.graphhopper.timeaware;

import java.time.Instant;
import java.util.List;

/**
 * The sticky closure rule of US-050 (the Java form of StickyClosure in scripts/routing_reference/sticky_reference.py).
 * An edge is closed for an arrival when some forecast step in [departure, arrival + margin] has a depth at or above the
 * vehicle's limit. Steps before the departure are ignored, so water that drained before the trip does not close a road.
 * The end of the window is included. A closure only grows with the arrival time, so an earlier arrival is never worse.
 * An edge outside the table reads as clear.
 */
public final class StickyClosure {

    /** The 10 minutes of the PRD, fixed on the server. */
    public static final long DEFAULT_MARGIN_MS = 10 * 60_000L;

    private final EdgeDepthTable table;
    private final int limitCm;
    private final long departureMs;
    private final long marginMs;
    private final long[] stepMs;

    public StickyClosure(EdgeDepthTable table, int limitCm, long departureEpochMs, long marginMs) {
        if (marginMs < 0) throw new IllegalArgumentException("the margin cannot be negative");
        this.table = table;
        this.limitCm = limitCm;
        this.departureMs = departureEpochMs;
        this.marginMs = marginMs;
        List<Instant> times = table.stepTimes();
        stepMs = new long[times.size()];
        for (int i = 0; i < stepMs.length; i++) stepMs[i] = times.get(i).toEpochMilli();
    }

    public int limitCm() {
        return limitCm;
    }

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
            if (stepMs[step] >= departureMs && table.depthCm(edgeId, step) >= limitCm) return true;
        }
        return false;
    }
}
