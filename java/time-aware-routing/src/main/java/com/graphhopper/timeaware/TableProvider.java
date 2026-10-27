package com.graphhopper.timeaware;

import java.util.Optional;

/**
 * Where the router gets the depth table of a time-aware request (US-052). {@link #current()} is the table to use, and
 * {@link #problem()} says why there is none, so the response of a fallback can name the cause.
 */
public interface TableProvider {

    Optional<EdgeDepthTable> current();

    /** Empty while a table is available. */
    Optional<String> problem();

    /** The hash of the graph this provider serves tables for, when it knows it. A client uses it to refuse a stale table. */
    default Optional<String> graphHash() {
        return Optional.empty();
    }
}
