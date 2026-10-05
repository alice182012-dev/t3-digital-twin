package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.config.Profile;
import com.graphhopper.json.Statement;
import com.graphhopper.util.CustomModel;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** The export of US-039, on a graph of 4 edges that src/test/resources/tiny.osm.xml makes. */
class ExportEdgesTest {

    private static final ObjectMapper JSON = new ObjectMapper();

    /** Imports an OSM file into a new graph folder, as the server does, and returns the folder. */
    private static Path importGraph(Path osm, Path graphDir) {
        CustomModel car = new CustomModel()
                .addToSpeed(Statement.If("true", Statement.Op.LIMIT, "car_average_speed"))
                .addToPriority(Statement.If("!car_access", Statement.Op.MULTIPLY, "0"));
        GraphHopperConfig config = new GraphHopperConfig()
                .putObject("datareader.file", osm.toString())
                .putObject("graph.location", graphDir.toString())
                .putObject("import.osm.ignored_highways", "")
                .putObject("graph.encoded_values", "car_access, car_average_speed")
                .setProfiles(List.of(new Profile("car").setCustomModel(car)));
        new TimeAwareGraphHopper().init(config).importOrLoad().close();
        return graphDir;
    }

    private static Path tinyOsm(Path dir, String name, String replaceFrom, String replaceTo) throws IOException {
        String xml = new String(ExportEdgesTest.class.getResourceAsStream("/tiny.osm.xml").readAllBytes(), StandardCharsets.UTF_8);
        Path file = dir.resolve(name);
        Files.writeString(file, xml.replace(replaceFrom, replaceTo));
        return file;
    }

    private static List<String> rows(Path csv) throws IOException {
        List<String> lines = Files.readAllLines(csv);
        return lines.subList(1, lines.size());
    }

    @Test
    void writesOneRowPerEdgeAndTheCountsMatchTheGraph(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.Result result = ExportEdges.export(graph, tmp.resolve("out"));

        assertEquals(4, result.edgeCount());
        assertEquals(5, result.nodeCount());
        List<String> lines = Files.readAllLines(tmp.resolve("out/edges.csv"));
        assertEquals("edge_id,wkt", lines.get(0));
        assertEquals(result.edgeCount(), rows(tmp.resolve("out/edges.csv")).size());
    }

    /** Measured before GraphHash was extracted. A change here breaks every table already built (edge-depth-table-format). */
    @Test
    void theHashOfTheTinyGraphIsPinned(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        assertEquals("3b4739134e8d9085da891153f88d9be5851a95c6896d9579241cd638f6afded1",
                ExportEdges.export(graph, tmp.resolve("out")).graphHash());
        assertEquals("3b4739134e8d9085da891153f88d9be5851a95c6896d9579241cd638f6afded1",
                GraphHash.of(graph));
    }

    @Test
    void rowsRunFromEdgeIdZeroUpInOrder(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.export(graph, tmp.resolve("out"));

        List<String> ids = new ArrayList<>();
        for (String row : rows(tmp.resolve("out/edges.csv"))) ids.add(row.substring(0, row.indexOf(',')));
        assertEquals(List.of("0", "1", "2", "3"), ids);
    }

    @Test
    void geometryIsALineStringWithLongitudeFirstAndKeepsShapePoints(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.export(graph, tmp.resolve("out"));

        List<Integer> pointCounts = new ArrayList<>();
        boolean sawShapePointEdge = false;
        for (String row : rows(tmp.resolve("out/edges.csv"))) {
            String wkt = row.substring(row.indexOf(',') + 1).replace("\"", "");
            assertTrue(wkt.startsWith("LINESTRING ("), wkt);
            String[] points = wkt.substring("LINESTRING (".length(), wkt.length() - 1).split(", ");
            pointCounts.add(points.length);
            for (String point : points) {
                String[] lonLat = point.split(" ");
                double lon = Double.parseDouble(lonLat[0]);
                double lat = Double.parseDouble(lonLat[1]);
                assertTrue(lon >= 105.7499 && lon <= 105.7521, "longitude first: " + point);
                assertTrue(lat >= 20.9999 && lat <= 21.0031, "latitude second: " + point);
            }
            if (wkt.contains("105.751 21.001")) sawShapePointEdge = true;
        }
        pointCounts.sort(Integer::compare);
        assertEquals(Arrays.asList(2, 2, 2, 3), pointCounts);
        assertTrue(sawShapePointEdge, "the shape point of way 12 must be in a row");
    }

    @Test
    void graphJsonHoldsTheHashCountsAndTheGraphHopperCommit(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.Result result = ExportEdges.export(graph, tmp.resolve("out"));

        JsonNode json = JSON.readTree(tmp.resolve("out/graph.json").toFile());
        assertEquals(result.graphHash(), json.get("graph_hash").asText());
        assertTrue(json.get("graph_hash").asText().matches("[0-9a-f]{64}"));
        assertEquals(4, json.get("edge_count").asInt());
        assertEquals(5, json.get("node_count").asInt());
        assertEquals("d7dc1b069d2d091c7cfdc007d99d1765c82e618d", json.get("graphhopper_commit").asText());
    }

    @Test
    void twoExportsOfOneGraphGiveOneHash(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        String first = ExportEdges.export(graph, tmp.resolve("out1")).graphHash();
        String second = ExportEdges.export(graph, tmp.resolve("out2")).graphHash();

        assertEquals(first, second);
        assertEquals(Files.readString(tmp.resolve("out1/edges.csv")), Files.readString(tmp.resolve("out2/edges.csv")));
    }

    @Test
    void twoImportsOfOneOsmFileGiveOneHash(@TempDir Path tmp) throws Exception {
        Path osm = tinyOsm(tmp, "a.osm.xml", "x", "x");

        String first = ExportEdges.export(importGraph(osm, tmp.resolve("graph-1")), tmp.resolve("out1")).graphHash();
        String second = ExportEdges.export(importGraph(osm, tmp.resolve("graph-2")), tmp.resolve("out2")).graphHash();

        assertEquals(first, second);
    }

    @Test
    void aMovedNodeChangesTheHash(@TempDir Path tmp) throws Exception {
        Path same = tinyOsm(tmp, "a.osm.xml", "x", "x");
        Path moved = tinyOsm(tmp, "b.osm.xml", "lat=\"21.0030\" lon=\"105.7510\"", "lat=\"21.0031\" lon=\"105.7510\"");

        String before = ExportEdges.export(importGraph(same, tmp.resolve("graph-a")), tmp.resolve("out1")).graphHash();
        String after = ExportEdges.export(importGraph(moved, tmp.resolve("graph-b")), tmp.resolve("out2")).graphHash();

        assertNotEquals(before, after);
    }

    @Test
    void anExtraWayChangesTheHash(@TempDir Path tmp) throws Exception {
        Path same = tinyOsm(tmp, "a.osm.xml", "x", "x");
        Path extra = tinyOsm(tmp, "b.osm.xml", "</osm>",
                "<way id=\"13\"><nd ref=\"4\"/><nd ref=\"6\"/><tag k=\"highway\" v=\"residential\"/></way></osm>");

        ExportEdges.Result before = ExportEdges.export(importGraph(same, tmp.resolve("graph-a")), tmp.resolve("out1"));
        ExportEdges.Result after = ExportEdges.export(importGraph(extra, tmp.resolve("graph-b")), tmp.resolve("out2"));

        assertEquals(5, after.edgeCount());
        assertNotEquals(before.graphHash(), after.graphHash());
    }

    /** Every file of the folder with its size, last-modified time, and bytes, so any write shows up. */
    private static List<String> fingerprint(Path dir) throws IOException {
        try (var files = Files.walk(dir)) {
            return files.filter(Files::isRegularFile).sorted().map(file -> {
                try {
                    return dir.relativize(file) + " " + Files.size(file) + " " + Files.getLastModifiedTime(file).toMillis()
                            + " " + Arrays.hashCode(Files.readAllBytes(file));
                } catch (IOException e) {
                    throw new java.io.UncheckedIOException(e);
                }
            }).toList();
        }
    }

    @Test
    void theGraphFolderIsNotChanged(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));
        List<String> before = fingerprint(graph);

        ExportEdges.export(graph, tmp.resolve("out"));

        assertEquals(before, fingerprint(graph));
    }

    /**
     * The server mounts the live graph cache read-only. A root user can write to files marked read-only, so this test
     * only means something for a normal user, as on CI, and it is skipped for root (as in the Docker build).
     */
    @Test
    void worksOnAFolderThatCannotBeWritten(@TempDir Path tmp) throws Exception {
        org.junit.jupiter.api.Assumptions.assumeFalse("root".equals(System.getProperty("user.name")),
                "root can write to read-only files");
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));
        try (var files = Files.walk(graph)) {
            files.forEach(file -> file.toFile().setWritable(false));
        }
        try {
            ExportEdges.Result result = ExportEdges.export(graph, tmp.resolve("out"));

            assertEquals(4, result.edgeCount());
        } finally {
            try (var files = Files.walk(graph)) {
                files.forEach(file -> file.toFile().setWritable(true));
            }
        }
    }

    @Test
    void anEmptyFolderIsAnErrorAndWritesNothing(@TempDir Path tmp) {
        Path missing = Paths.get(tmp.toString(), "no-graph");

        org.junit.jupiter.api.Assertions.assertThrows(IllegalStateException.class,
                () -> ExportEdges.export(missing, tmp.resolve("out")));
        assertTrue(Files.notExists(tmp.resolve("out/edges.csv")));
    }
}
