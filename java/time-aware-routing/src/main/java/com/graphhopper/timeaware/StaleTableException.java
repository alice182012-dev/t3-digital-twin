package com.graphhopper.timeaware;

/**
 * The table is whole, but it was built for another graph than the one the reader has loaded. Edge ids change on
 * every graph re-import, so its depths would land on the wrong roads. Not a {@link TableFormatException}: a damaged
 * file is a bug, and a stale one is a re-import that is not finished.
 */
public class StaleTableException extends RuntimeException {

    private final String tableGraphHash;
    private final String loadedGraphHash;

    public StaleTableException(String runName, String tableGraphHash, String loadedGraphHash) {
        super("stale edge depth table: run " + runName + " was built for graph hash " + tableGraphHash
                + ", but the loaded graph has hash " + loadedGraphHash
                + ". Write a new export and build a new table (artifacts/docs/concepts/graph-reimport-procedure.md).");
        this.tableGraphHash = tableGraphHash;
        this.loadedGraphHash = loadedGraphHash;
    }

    public String tableGraphHash() {
        return tableGraphHash;
    }

    public String loadedGraphHash() {
        return loadedGraphHash;
    }
}
