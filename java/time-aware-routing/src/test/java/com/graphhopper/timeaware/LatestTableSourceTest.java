package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The pointer-following reader of US-043: loads `latest`, refuses a table of another graph, reloads on a new pointer. */
class LatestTableSourceTest {

    static byte[] golden;
    static String goldenHash;
    static final Duration FAST = Duration.ofMillis(40);

    @BeforeAll
    static void loadFixture() throws IOException {
        golden = LatestTableSourceTest.class.getResourceAsStream("/edge-depth/golden.bin").readAllBytes();
        goldenHash = new ObjectMapper()
                .readTree(LatestTableSourceTest.class.getResourceAsStream("/edge-depth/golden.json"))
                .get("graph_hash").asText();
    }

    /** A copy of the fixture with the last character of the run name set to `mark` (same length, so same layout). */
    static byte[] withRunMark(char mark) {
        byte[] bytes = golden.clone();
        bytes[16 + 64 + 14] = (byte) mark;
        return bytes;
    }

    /** A copy of the fixture built for another graph. */
    static byte[] forOtherGraph() {
        byte[] bytes = golden.clone();
        bytes[16] = (byte) (bytes[16] == 'f' ? 'e' : 'f');
        return bytes;
    }

    static void publish(Path dir, String name, byte[] bytes) throws IOException {
        Files.write(dir.resolve(name), bytes);
        Path tmp = dir.resolve(".latest.tmp");
        Files.writeString(tmp, name + "\n", StandardCharsets.UTF_8);
        Files.move(tmp, dir.resolve("latest"), StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
    }

    @Test
    void withNoPointerThereIsNoTableAndNoError(@TempDir Path dir) {
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);

        assertEquals(Optional.empty(), source.current());
        assertFalse(source.refresh());
    }

    @Test
    void thePointedTableIsLoaded(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);

        EdgeDepthTable table = source.current().orElseThrow();
        assertEquals('1', table.runName().charAt(14));
        assertEquals(goldenHash, table.graphHash());
    }

    @Test
    void aTableForAnotherGraphIsRefusedAndNothingIsServed(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", forOtherGraph());
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);

        assertEquals(Optional.empty(), source.current());
        assertTrue(source.lastRefusal().orElseThrow().contains(goldenHash));
    }

    @Test
    void aRefusedNewTableKeepsTheValidCurrentOne(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);
        EdgeDepthTable first = source.current().orElseThrow();

        publish(dir, "20261001T010000.bin", forOtherGraph());
        assertFalse(source.refresh());

        assertSame(first, source.current().orElseThrow());
        assertTrue(source.lastRefusal().isPresent());
    }

    @Test
    void aCorruptNewTableKeepsTheValidCurrentOne(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);
        EdgeDepthTable first = source.current().orElseThrow();

        publish(dir, "20261001T010000.bin", java.util.Arrays.copyOf(golden, golden.length - 1));

        assertFalse(source.refresh());
        assertSame(first, source.current().orElseThrow());
        assertTrue(source.lastRefusal().orElseThrow().contains("body"));
    }

    @Test
    void aPointerToAMissingFileKeepsTheCurrentTable(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);
        EdgeDepthTable first = source.current().orElseThrow();

        Files.writeString(dir.resolve("latest"), "20261001T020000.bin\n");

        assertFalse(source.refresh());
        assertSame(first, source.current().orElseThrow());
    }

    @Test
    void aNewPointerLoadsTheNewTableAndARequestInFlightKeepsItsOwn(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);
        EdgeDepthTable inFlight = source.current().orElseThrow();

        publish(dir, "20261001T010000.bin", withRunMark('2'));
        Files.delete(dir.resolve("20261001T000000.bin")); // retention
        assertTrue(source.refresh());

        assertEquals('2', source.current().orElseThrow().runName().charAt(14));
        assertEquals('1', inFlight.runName().charAt(14));
        assertEquals(65535, inFlight.depthCm(1, 0));
    }

    @Test
    void anUnchangedPointerIsNotReloaded(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST);
        EdgeDepthTable first = source.current().orElseThrow();

        assertFalse(source.refresh());

        assertSame(first, source.current().orElseThrow());
    }

    @Test
    void theBackgroundPollPicksUpANewTableWithinTheInterval(@TempDir Path dir) throws Exception {
        publish(dir, "20261001T000000.bin", withRunMark('1'));
        try (LatestTableSource source = new LatestTableSource(dir, goldenHash, FAST)) {
            source.start();
            publish(dir, "20261001T010000.bin", withRunMark('2'));

            long deadline = System.nanoTime() + Duration.ofSeconds(5).toNanos();
            while (source.current().orElseThrow().runName().charAt(14) != '2' && System.nanoTime() < deadline) {
                Thread.sleep(10);
            }
            assertEquals('2', source.current().orElseThrow().runName().charAt(14));
        }
    }

    @Test
    void theDefaultIntervalIsWithinThirtySeconds(@TempDir Path dir) {
        LatestTableSource source = new LatestTableSource(dir, goldenHash);

        assertTrue(source.interval().compareTo(Duration.ofSeconds(30)) <= 0, source.interval().toString());
    }

    @Test
    void anIntervalOverThirtySecondsIsRefused(@TempDir Path dir) {
        assertThrows(IllegalArgumentException.class,
                () -> new LatestTableSource(dir, goldenHash, Duration.ofSeconds(31)));
        assertThrows(IllegalArgumentException.class, () -> new LatestTableSource(dir, goldenHash, Duration.ZERO));
    }
}
