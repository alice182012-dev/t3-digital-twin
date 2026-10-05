package com.graphhopper.timeaware;

/** The file is not a version 1 edge depth table, or it is damaged. A bug, unlike {@link StaleTableException}. */
public class TableFormatException extends RuntimeException {

    public TableFormatException(String message) {
        super(message);
    }
}
