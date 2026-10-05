package com.graphhopper.timeaware;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Follows the `latest` pointer of an edge depth table folder (US-043). {@link #current()} is the table to serve. A new
 * table is memory-mapped on {@link #refresh()}, which the daemon poll started by {@link #start()} calls every
 * interval (5 s by default, never over 30 s). A table that is damaged, built for another graph, or named by a
 * pointer whose file is gone is refused and logged at ERROR, and the valid current table stays. A caller that holds a
 * table keeps it, so a request in flight finishes on the table it began with.
 */
public final class LatestTableSource implements AutoCloseable {

    public static final Duration DEFAULT_INTERVAL = Duration.ofSeconds(5);
    public static final Duration MAX_INTERVAL = Duration.ofSeconds(30);
    private static final String POINTER = "latest";
    private static final Logger logger = LoggerFactory.getLogger(LatestTableSource.class);

    private final Path directory;
    private final String loadedGraphHash;
    private final Duration interval;

    private volatile EdgeDepthTable current;
    private volatile String currentName;
    private volatile String lastRefusal;
    private String lastRefusedName;
    private ScheduledExecutorService poller;

    public LatestTableSource(Path directory, String loadedGraphHash) {
        this(directory, loadedGraphHash, DEFAULT_INTERVAL);
    }

    public LatestTableSource(Path directory, String loadedGraphHash, Duration interval) {
        if (interval.isZero() || interval.isNegative() || interval.compareTo(MAX_INTERVAL) > 0) {
            throw new IllegalArgumentException("interval " + interval + " is outside (0, " + MAX_INTERVAL + "]");
        }
        this.directory = directory;
        this.loadedGraphHash = loadedGraphHash;
        this.interval = interval;
        refresh();
    }

    public Optional<EdgeDepthTable> current() {
        return Optional.ofNullable(current);
    }

    /** The file name of the current table, as the pointer named it. */
    public Optional<String> currentName() {
        return Optional.ofNullable(currentName);
    }

    public Duration interval() {
        return interval;
    }

    /** The reason the newest pointer was refused, if the last refresh refused one. */
    public Optional<String> lastRefusal() {
        return Optional.ofNullable(lastRefusal);
    }

    /** Starts the daemon poll. */
    public synchronized void start() {
        if (poller != null) return;
        poller = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "edge-depth-latest");
            t.setDaemon(true);
            return t;
        });
        poller.scheduleWithFixedDelay(this::refresh, interval.toMillis(), interval.toMillis(), TimeUnit.MILLISECONDS);
    }

    /** Returns true when a new table was loaded. */
    public synchronized boolean refresh() {
        String name;
        try {
            name = Files.readString(directory.resolve(POINTER), StandardCharsets.UTF_8).strip();
        } catch (NoSuchFileException e) {
            return false;
        } catch (IOException e) {
            refuse(null, "cannot read the pointer: " + e);
            return false;
        }
        if (name.isEmpty() || name.equals(POINTER) || !Path.of(name).getFileName().toString().equals(name)) {
            refuse(name, "the pointer names " + name + ", which is not a table file in " + directory);
            return false;
        }
        if (name.equals(currentName)) {
            lastRefusal = null;
            return false;
        }
        try {
            EdgeDepthTable table = EdgeDepthTable.open(directory.resolve(name)).requireGraphHash(loadedGraphHash);
            current = table;
            currentName = name;
            lastRefusal = null;
            lastRefusedName = null;
            logger.info("edge depth table {} loaded: run {}, {} edges, {} steps", name, table.runName(),
                    table.edgeCount(), table.stepCount());
            return true;
        } catch (NoSuchFileException e) {
            refuse(name, "the pointer names " + name + ", but the file is not in " + directory);
            return false;
        } catch (StaleTableException | TableFormatException | IOException e) {
            refuse(name, e.getMessage() != null ? e.getMessage() : e.toString());
            return false;
        }
    }

    private void refuse(String name, String reason) {
        lastRefusal = reason;
        // One ERROR line per refused pointer value, not one every poll.
        if (name == null || !name.equals(lastRefusedName)) {
            logger.error("edge depth table refused, keeping {}: {}", currentName == null ? "none" : currentName, reason);
        }
        lastRefusedName = name;
    }

    @Override
    public synchronized void close() {
        if (poller != null) {
            poller.shutdownNow();
            poller = null;
        }
    }
}
