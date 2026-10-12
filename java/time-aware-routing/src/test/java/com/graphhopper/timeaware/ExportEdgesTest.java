package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.config.Profile;
import com.graphhopper.json.Statement;
import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.storage.BaseGraph;
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

    private static final String ENCODED_VALUES = "car_access, car_average_speed, osm_way_id";

    /** Imports an OSM file into a new graph folder, as the server does, and returns the folder. */
    private static Path importGraph(Path osm, Path graphDir) {
        return importGraph(osm, graphDir, ENCODED_VALUES);
    }

    private static Path importGraph(Path osm, Path graphDir, String encodedValues) {
        CustomModel car = new CustomModel()
                .addToSpeed(Statement.If("true", Statement.Op.LIMIT, "car_average_speed"))
                .addToPriority(Statement.If("!car_access", Statement.Op.MULTIPLY, "0"));
        GraphHopperConfig config = new GraphHopperConfig()
                .putObject("datareader.file", osm.toString())
                .putObject("graph.location", graphDir.toString())
                .putObject("import.osm.ignored_highways", "")
                .putObject("graph.encoded_values", encodedValues)
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
        assertEquals("edge_id,wkt,base_node,adj_node,edge_key", lines.get(0));
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
            String wkt = row.substring(row.indexOf('"') + 1, row.lastIndexOf('"'));
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
        assertEquals(3, json.get("format_version").asInt());
    }

    /** The node ids are the GraphHopper ids that GraphHash reads, so a reader can join an edge to its nodes. */
    @Test
    void eachRowHoldsTheBaseAndAdjacentNodeIdOfItsEdgeBeforeTheKey(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.export(graph, tmp.resolve("out"));

        List<String> expected = new ArrayList<>();
        BaseGraph opened = ExportEdges.openReadOnly(graph);
        try {
            AllEdgesIterator edges = opened.getAllEdges();
            while (edges.next()) expected.add(edges.getEdge() + "," + edges.getBaseNode() + "," + edges.getAdjNode());
        } finally {
            opened.close();
        }
        List<String> actual = new ArrayList<>();
        for (String row : rows(tmp.resolve("out/edges.csv"))) {
            String[] tail = row.substring(row.lastIndexOf('"') + 2).split(",");
            assertEquals(3, tail.length, row);
            actual.add(row.substring(0, row.indexOf(',')) + "," + tail[0] + "," + tail[1]);
        }
        assertEquals(4, actual.size());
        assertEquals(expected, actual);
    }

    private static List<String> keys(Path csv) throws IOException {
        List<String> keys = new ArrayList<>();
        for (String row : rows(csv)) keys.add(row.substring(row.lastIndexOf(',') + 1));
        return keys;
    }

    /** Way 10 is split at the junction node 2, so its two edges are positions 0 and 1. Ways 11 and 12 are one edge each. */
    @Test
    void theKeyIsTheOsmWayIdAndThePositionAlongTheWay(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"));

        ExportEdges.export(graph, tmp.resolve("out"));

        List<String> keys = keys(tmp.resolve("out/edges.csv"));
        assertEquals(List.of("10:0", "10:1", "11:0", "12:0"), keys.stream().sorted().toList());
        assertTrue(keys.indexOf("10:0") < keys.indexOf("10:1"), "position 0 is the edge with the lower id: " + keys);
    }

    @Test
    void noTwoEdgesShareAKey(@TempDir Path tmp) throws Exception {
        Path extra = tinyOsm(tmp, "b.osm.xml", "</osm>",
                "<way id=\"13\"><nd ref=\"4\"/><nd ref=\"6\"/><tag k=\"highway\" v=\"residential\"/></way></osm>");
        Path graph = importGraph(extra, tmp.resolve("graph-b"));

        ExportEdges.export(graph, tmp.resolve("out"));

        List<String> keys = keys(tmp.resolve("out/edges.csv"));
        assertEquals(5, keys.size());
        assertEquals(keys.size(), keys.stream().distinct().count());
    }

    /** The point of the key: it must survive a re-import of the same file, where edge ids may change. */
    @Test
    void twoImportsOfOneOsmFileGiveTheSameKeyForEachEdge(@TempDir Path tmp) throws Exception {
        Path osm = tinyOsm(tmp, "a.osm.xml", "x", "x");

        ExportEdges.export(importGraph(osm, tmp.resolve("graph-1")), tmp.resolve("out1"));
        ExportEdges.export(importGraph(osm, tmp.resolve("graph-2")), tmp.resolve("out2"));

        assertEquals(keys(tmp.resolve("out1/edges.csv")), keys(tmp.resolve("out2/edges.csv")));
    }

    /** An extra way adds its own key and leaves the keys of the other ways as they were. */
    @Test
    void anExtraWayAddsOneKeyAndKeepsTheOthers(@TempDir Path tmp) throws Exception {
        Path same = tinyOsm(tmp, "a.osm.xml", "x", "x");
        Path extra = tinyOsm(tmp, "b.osm.xml", "</osm>",
                "<way id=\"13\"><nd ref=\"4\"/><nd ref=\"6\"/><tag k=\"highway\" v=\"residential\"/></way></osm>");

        ExportEdges.export(importGraph(same, tmp.resolve("graph-a")), tmp.resolve("out1"));
        ExportEdges.export(importGraph(extra, tmp.resolve("graph-b")), tmp.resolve("out2"));

        List<String> before = keys(tmp.resolve("out1/edges.csv")).stream().sorted().toList();
        List<String> after = keys(tmp.resolve("out2/edges.csv")).stream().sorted().toList();
        List<String> expected = new ArrayList<>(before);
        expected.add("13:0");
        assertEquals(expected.stream().sorted().toList(), after);
    }

    @Test
    void aGraphWithoutTheOsmWayIdValueIsAnErrorThatNamesTheFixAndWritesNothing(@TempDir Path tmp) throws Exception {
        Path graph = importGraph(tinyOsm(tmp, "a.osm.xml", "x", "x"), tmp.resolve("graph-a"), "car_access, car_average_speed");

        IllegalStateException error = org.junit.jupiter.api.Assertions.assertThrows(IllegalStateException.class,
                () -> ExportEdges.export(graph, tmp.resolve("out")));

        assertTrue(error.getMessage().contains("osm_way_id"), error.getMessage());
        assertTrue(error.getMessage().contains("re-import"), error.getMessage());
        assertTrue(Files.notExists(tmp.resolve("out")));
    }

    /** Adding osm_way_id changes the stored edge data, not the nodes or the geometry, so every table already built stays valid. */
    @Test
    void theHashDoesNotDependOnWhetherTheWayIdIsStored(@TempDir Path tmp) throws Exception {
        Path osm = tinyOsm(tmp, "a.osm.xml", "x", "x");

        String without = GraphHash.of(importGraph(osm, tmp.resolve("graph-1"), "car_access, car_average_speed"));
        String with = GraphHash.of(importGraph(osm, tmp.resolve("graph-2")));

        assertEquals(without, with);
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
