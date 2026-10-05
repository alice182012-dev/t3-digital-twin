package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The Java reader of the edge depth table on the shared fixture of US-043 (golden.bin and golden.json, written by
 * scripts/edge_depth/golden_fixture.py and read by the Python reader too), and on damaged copies of it.
 */
class EdgeDepthTableTest {

    static byte[] golden;
    static JsonNode expected;

    @BeforeAll
    static void loadFixture() throws IOException {
        golden = EdgeDepthTableTest.class.getResourceAsStream("/edge-depth/golden.bin").readAllBytes();
        expected = new ObjectMapper().readTree(EdgeDepthTableTest.class.getResourceAsStream("/edge-depth/golden.json"));
    }

    /** Writes the fixture, with edits, into a new file and returns its path. */
    static Path write(Path dir, String name, byte[] bytes) throws IOException {
        Path file = dir.resolve(name);
        Files.write(file, bytes);
        return file;
    }

    @Test
    void theHeaderIsTheOneThePythonWriterWrote(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));

        assertEquals(expected.get("graph_hash").asText(), table.graphHash());
        assertEquals(expected.get("run_name").asText(), table.runName());
        assertEquals(expected.get("edge_count").asInt(), table.edgeCount());
        assertEquals(expected.get("step_count").asInt(), table.stepCount());
        List<Instant> times = new ArrayList<>();
        for (JsonNode seconds : expected.get("step_times_epoch")) times.add(Instant.ofEpochSecond(seconds.asLong()));
        assertEquals(times, table.stepTimes());
    }

    @Test
    void everyEdgeAndStepReturnsTheValueThePythonReaderReturns(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));
        JsonNode depths = expected.get("depths_cm");

        int checked = 0;
        for (int edge = 0; edge < table.edgeCount(); edge++) {
            for (int step = 0; step < table.stepCount(); step++) {
                assertEquals(depths.get(edge).get(step).asInt(), table.depthCm(edge, step), "edge " + edge + " step " + step);
                checked++;
            }
        }
        assertEquals(3000 * 9, checked);
    }

    @Test
    void valuesAboveTheSignedRangeAreNotNegative(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));

        assertEquals(65535, table.depthCm(1, 0));
        assertEquals(32768, table.depthCm(2, 7));
        assertEquals(255, table.depthCm(2, 2));
        assertEquals(256, table.depthCm(2, 3));
    }

    @Test
    void anEdgeOrStepOutsideTheTableIsAnError(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));

        IndexOutOfBoundsException edge = assertThrows(IndexOutOfBoundsException.class, () -> table.depthCm(3000, 0));
        assertTrue(edge.getMessage().contains("edge 3000"), edge.getMessage());
        assertThrows(IndexOutOfBoundsException.class, () -> table.depthCm(-1, 0));
        IndexOutOfBoundsException step = assertThrows(IndexOutOfBoundsException.class, () -> table.depthCm(0, 9));
        assertTrue(step.getMessage().contains("step 9"), step.getMessage());
        assertThrows(IndexOutOfBoundsException.class, () -> table.depthCm(0, -1));
    }

    @Test
    void aMissingFileIsAnIoError(@TempDir Path tmp) {
        assertThrows(NoSuchFileException.class, () -> EdgeDepthTable.open(tmp.resolve("none.bin")));
    }

    @Test
    void aMappedTableStaysReadableWhenRetentionDeletesItsFile(@TempDir Path tmp) throws Exception {
        Path file = write(tmp, "golden.bin", golden);
        EdgeDepthTable table = EdgeDepthTable.open(file);

        Files.delete(file);

        assertEquals(65535, table.depthCm(1, 0));
    }

    // Damaged files. A reader tells a damaged file (a bug) from an old table (a re-import not finished).

    private static byte[] copy() {
        return golden.clone();
    }

    private void assertFormatError(Path tmp, byte[] bytes, String contains) throws IOException {
        Path file = write(tmp, "bad.bin", bytes);
        TableFormatException e = assertThrows(TableFormatException.class, () -> EdgeDepthTable.open(file));
        assertTrue(e.getMessage().contains(contains), e.getMessage());
    }

    @Test
    void aWrongMagicIsRefused(@TempDir Path tmp) throws Exception {
        byte[] bytes = copy();
        bytes[0] = 'X';

        assertFormatError(tmp, bytes, "magic");
    }

    @Test
    void aWrongVersionIsRefused(@TempDir Path tmp) throws Exception {
        byte[] bytes = copy();
        bytes[4] = 2;

        assertFormatError(tmp, bytes, "version 2");
    }

    @Test
    void aFileShorterThanTheFixedHeaderIsRefused(@TempDir Path tmp) throws Exception {
        assertFormatError(tmp, java.util.Arrays.copyOf(golden, 10), "header is cut off");
    }

    @Test
    void aHeaderCutOffInTheHashIsRefused(@TempDir Path tmp) throws Exception {
        assertFormatError(tmp, java.util.Arrays.copyOf(golden, 16 + 20), "header is cut off");
    }

    @Test
    void aBodyThatIsOneByteShortIsRefused(@TempDir Path tmp) throws Exception {
        assertFormatError(tmp, java.util.Arrays.copyOf(golden, golden.length - 1), "body");
    }

    @Test
    void aBodyWithAnExtraByteIsRefused(@TempDir Path tmp) throws Exception {
        assertFormatError(tmp, java.util.Arrays.copyOf(golden, golden.length + 1), "body");
    }

    @Test
    void stepTimesThatDoNotIncreaseAreRefused(@TempDir Path tmp) throws Exception {
        byte[] bytes = copy();
        int timesAt = 16 + 64 + 15;
        // Copy the first step time over the second.
        System.arraycopy(bytes, timesAt, bytes, timesAt + 8, 8);

        assertFormatError(tmp, bytes, "increase");
    }

    @Test
    void textThatIsNotUtf8IsRefused(@TempDir Path tmp) throws Exception {
        byte[] bytes = copy();
        bytes[16] = (byte) 0xFF;

        assertFormatError(tmp, bytes, "UTF-8");
    }

    @Test
    void aTableWithNoStepsIsRefused(@TempDir Path tmp) throws Exception {
        byte[] bytes = copy();
        bytes[6] = 0;
        bytes[7] = 0;

        Path file = write(tmp, "bad.bin", bytes);

        assertThrows(TableFormatException.class, () -> EdgeDepthTable.open(file));
    }

    // The refusal of a table for another graph.

    @Test
    void aTableForTheLoadedGraphPasses(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));

        assertSame(table, table.requireGraphHash(table.graphHash()));
    }

    @Test
    void aTableForAnotherGraphIsRefusedAndBothHashesAreNamed(@TempDir Path tmp) throws Exception {
        EdgeDepthTable table = EdgeDepthTable.open(write(tmp, "golden.bin", golden));
        String other = "f".repeat(64);

        StaleTableException e = assertThrows(StaleTableException.class, () -> table.requireGraphHash(other));

        String message = e.getMessage();
        assertTrue(message.contains(table.graphHash()), message);
        assertTrue(message.contains(other), message);
        assertTrue(message.contains(table.runName()), message);
        assertTrue(message.contains("graph-reimport-procedure"), message);
        assertNotNull(e.tableGraphHash());
        assertEquals(other, e.loadedGraphHash());
    }

    @Test
    void anOldTableIsNotADamagedFile() {
        assertFalse(TableFormatException.class.isAssignableFrom(StaleTableException.class));
        assertFalse(StaleTableException.class.isAssignableFrom(TableFormatException.class));
        assertEquals(StandardCharsets.UTF_8.name(), "UTF-8");
    }
}
