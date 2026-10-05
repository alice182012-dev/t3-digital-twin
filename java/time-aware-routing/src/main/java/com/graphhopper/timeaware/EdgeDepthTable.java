package com.graphhopper.timeaware;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Reader of the edge depth table (US-043): flood depth in centimetres by GraphHopper edge id and step. The byte layout
 * is in artifacts/docs/concepts/edge-depth-table-format.md and the checks equal the Python reader's (read_table in
 * scripts/edge_depth/edge_depth_table.py). The file is memory-mapped read-only, so a reader never copies the body and
 * a file removed by retention stays readable until the table is dropped.
 */
public final class EdgeDepthTable {

    static final byte[] MAGIC = {'E', 'D', 'G', 'D'};
    static final int VERSION = 1;
    private static final int FIXED_SIZE = 16;
    private static final int DEPTH_BYTES = 2;

    private final String graphHash;
    private final String runName;
    private final List<Instant> stepTimes;
    private final int edgeCount;
    private final int stepCount;
    private final ByteBuffer data;
    private final int bodyOffset;

    private EdgeDepthTable(String graphHash, String runName, List<Instant> stepTimes, int edgeCount, ByteBuffer data,
            int bodyOffset) {
        this.graphHash = graphHash;
        this.runName = runName;
        this.stepTimes = stepTimes;
        this.edgeCount = edgeCount;
        this.stepCount = stepTimes.size();
        this.data = data;
        this.bodyOffset = bodyOffset;
    }

    public static EdgeDepthTable open(Path path) throws IOException {
        ByteBuffer buf;
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.READ)) {
            long size = channel.size();
            if (size > Integer.MAX_VALUE) {
                throw new TableFormatException("file is " + size + " bytes, this reader maps at most " + Integer.MAX_VALUE);
            }
            buf = channel.map(FileChannel.MapMode.READ_ONLY, 0, size).order(ByteOrder.LITTLE_ENDIAN);
        }
        long size = buf.capacity();
        if (size < FIXED_SIZE) {
            throw new TableFormatException("header is cut off: " + size + " bytes, at least " + FIXED_SIZE + " needed");
        }
        for (int i = 0; i < MAGIC.length; i++) {
            if (buf.get(i) != MAGIC[i]) {
                throw new TableFormatException("bad magic, expected EDGD");
            }
        }
        int version = buf.getShort(4) & 0xFFFF;
        if (version != VERSION) {
            throw new TableFormatException("version " + version + ", this reader reads version " + VERSION);
        }
        int steps = buf.getShort(6) & 0xFFFF;
        long edges = buf.getInt(8) & 0xFFFFFFFFL;
        int hashLen = buf.getShort(12) & 0xFFFF;
        int runLen = buf.getShort(14) & 0xFFFF;
        long bodyOffset = FIXED_SIZE + (long) hashLen + runLen + 8L * steps;
        if (size < bodyOffset) {
            throw new TableFormatException("header is cut off: " + size + " bytes, " + bodyOffset + " needed");
        }
        long bodyNeeded = edges * steps * DEPTH_BYTES;
        if (size - bodyOffset != bodyNeeded) {
            throw new TableFormatException("body is " + (size - bodyOffset) + " bytes, " + edges + " edges and " + steps
                    + " steps need " + bodyNeeded);
        }
        if (edges > Integer.MAX_VALUE) {
            throw new TableFormatException(edges + " edges, this reader reads at most " + Integer.MAX_VALUE);
        }
        String hash = text(buf, FIXED_SIZE, hashLen);
        String run = text(buf, FIXED_SIZE + hashLen, runLen);
        if (steps == 0) {
            throw new TableFormatException("a table needs at least one step");
        }
        int timesAt = FIXED_SIZE + hashLen + runLen;
        List<Instant> times = new ArrayList<>(steps);
        long previous = Long.MIN_VALUE;
        for (int i = 0; i < steps; i++) {
            long epoch = buf.getLong(timesAt + 8 * i);
            if (i > 0 && epoch <= previous) {
                throw new TableFormatException("step times must increase, step " + i + " does not");
            }
            previous = epoch;
            times.add(Instant.ofEpochSecond(epoch));
        }
        return new EdgeDepthTable(hash, run, Collections.unmodifiableList(times), (int) edges, buf, (int) bodyOffset);
    }

    private static String text(ByteBuffer buf, int at, int length) {
        byte[] bytes = new byte[length];
        buf.get(at, bytes);
        try {
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        } catch (CharacterCodingException e) {
            throw new TableFormatException("header text is not UTF-8: " + e.getMessage());
        }
    }

    public String graphHash() {
        return graphHash;
    }

    public String runName() {
        return runName;
    }

    public int edgeCount() {
        return edgeCount;
    }

    public int stepCount() {
        return stepCount;
    }

    public List<Instant> stepTimes() {
        return stepTimes;
    }

    /** Depth in centimetres, 0 to 65535. */
    public int depthCm(int edgeId, int step) {
        if (edgeId < 0 || edgeId >= edgeCount) {
            throw new IndexOutOfBoundsException("edge " + edgeId + " is outside 0.." + (edgeCount - 1));
        }
        if (step < 0 || step >= stepCount) {
            throw new IndexOutOfBoundsException("step " + step + " is outside 0.." + (stepCount - 1));
        }
        return data.getShort(bodyOffset + (edgeId * stepCount + step) * DEPTH_BYTES) & 0xFFFF;
    }

    /** Returns this table when it was built for the loaded graph, and throws {@link StaleTableException} when not. */
    public EdgeDepthTable requireGraphHash(String loadedGraphHash) {
        if (!graphHash.equals(loadedGraphHash)) {
            throw new StaleTableException(runName, graphHash, loadedGraphHash);
        }
        return this;
    }
}
