package com.graphhopper.timeaware;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.function.IntBinaryOperator;

/** Writes edge depth tables for tests, in the format of edge-depth-table-format.md (the same bytes the Python writer makes). */
final class TestTables {

    static final String HASH = "a".repeat(64);

    private TestTables() {
    }

    /** steps are epoch seconds. depthCm gives the depth of (edge, step). */
    static EdgeDepthTable table(Path dir, String name, int edges, long[] steps, IntBinaryOperator depthCm) throws IOException {
        return table(dir, name, HASH, edges, steps, depthCm);
    }

    static EdgeDepthTable table(Path dir, String name, String graphHash, int edges, long[] steps, IntBinaryOperator depthCm)
            throws IOException {
        byte[] hash = graphHash.getBytes(StandardCharsets.UTF_8);
        byte[] run = "20261005T000000".getBytes(StandardCharsets.UTF_8);
        ByteBuffer buf = ByteBuffer.allocate(16 + hash.length + run.length + 8 * steps.length + 2 * edges * steps.length)
                .order(ByteOrder.LITTLE_ENDIAN);
        buf.put(EdgeDepthTable.MAGIC).putShort((short) 1).putShort((short) steps.length).putInt(edges)
                .putShort((short) hash.length).putShort((short) run.length);
        buf.put(hash).put(run);
        for (long s : steps) buf.putLong(s);
        for (int e = 0; e < edges; e++) {
            for (int s = 0; s < steps.length; s++) buf.putShort((short) depthCm.applyAsInt(e, s));
        }
        Path file = dir.resolve(name);
        Files.write(file, buf.array());
        return EdgeDepthTable.open(file);
    }

    /** Eight steps 15 minutes apart from `first`, the shape of a real run. */
    static long[] quarterHours(Instant first, int count) {
        long[] steps = new long[count];
        for (int i = 0; i < count; i++) steps[i] = first.getEpochSecond() + 900L * i;
        return steps;
    }
}
