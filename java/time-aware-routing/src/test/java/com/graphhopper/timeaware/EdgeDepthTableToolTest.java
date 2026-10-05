package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The command line reader of US-043, which reader-check.sh runs on the server. */
class EdgeDepthTableToolTest {

    static byte[] golden;

    @BeforeAll
    static void loadFixture() throws IOException {
        golden = EdgeDepthTableToolTest.class.getResourceAsStream("/edge-depth/golden.bin").readAllBytes();
    }

    private static String hash() {
        return new String(golden, 16, 64, StandardCharsets.UTF_8);
    }

    private record Outcome(int code, String out) {
    }

    private static Outcome run(String... args) {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        int code = EdgeDepthTableTool.run(args, new PrintStream(buffer, true, StandardCharsets.UTF_8));
        return new Outcome(code, buffer.toString(StandardCharsets.UTF_8));
    }

    @Test
    void readsTheLatestTableAndPrintsItsHeaderAndSomeDepths(@TempDir Path dir) throws Exception {
        LatestTableSourceTest.publish(dir, "20261001T000000.bin", golden);

        Outcome o = run(dir.toString(), "--graph-hash", hash());

        assertEquals(0, o.code(), o.out());
        assertTrue(o.out().contains("run=20261001T000000"), o.out());
        assertTrue(o.out().contains("edges=3000"), o.out());
        assertTrue(o.out().contains("steps=9"), o.out());
        assertTrue(o.out().contains("graph_hash=" + hash()), o.out());
        assertTrue(o.out().contains("edge=1 step=0 depth_cm=65535"), o.out());
        assertTrue(o.out().contains("PASS"), o.out());
    }

    @Test
    void aTableForAnotherGraphExitsWithOneAndNamesBothHashes(@TempDir Path dir) throws Exception {
        LatestTableSourceTest.publish(dir, "20261001T000000.bin", golden);
        String other = "0".repeat(64);

        Outcome o = run(dir.toString(), "--graph-hash", other);

        assertEquals(1, o.code(), o.out());
        assertTrue(o.out().contains(hash()), o.out());
        assertTrue(o.out().contains(other), o.out());
        assertTrue(o.out().contains("STALE"), o.out());
    }

    @Test
    void withoutAHashItReadsTheTableAnyway(@TempDir Path dir) throws Exception {
        LatestTableSourceTest.publish(dir, "20261001T000000.bin", golden);

        assertEquals(0, run(dir.toString()).code());
    }

    @Test
    void aFolderWithNoPointerExitsWithTwo(@TempDir Path dir) {
        Outcome o = run(dir.toString());

        assertEquals(2, o.code(), o.out());
        assertTrue(o.out().contains("latest"), o.out());
    }

    @Test
    void aDamagedTableExitsWithTwo(@TempDir Path dir) throws Exception {
        LatestTableSourceTest.publish(dir, "20261001T000000.bin", java.util.Arrays.copyOf(golden, golden.length - 1));

        Outcome o = run(dir.toString());

        assertEquals(2, o.code(), o.out());
        assertTrue(o.out().contains("body"), o.out());
    }

    @Test
    void noArgumentsPrintsUsage() {
        Outcome o = run();

        assertEquals(2, o.code());
        assertTrue(o.out().contains("usage"), o.out());
    }

    @Test
    void theGraphFolderOptionComparesWithTheHashOfThatGraph(@TempDir Path dir) throws Exception {
        LatestTableSourceTest.publish(dir, "20261001T000000.bin", golden);

        Outcome o = run(dir.toString(), "--graph-folder", dir.resolve("no-graph").toString());

        assertEquals(2, o.code(), o.out());
        assertTrue(o.out().contains("No graph folder"), o.out());
    }
}
