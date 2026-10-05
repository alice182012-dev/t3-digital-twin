package com.graphhopper.timeaware;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.DAType;
import com.graphhopper.storage.GHDirectory;
import com.graphhopper.storage.StorableProperties;
import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.util.FetchMode;
import com.graphhopper.util.PointList;
import java.io.BufferedWriter;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * Exports every edge of a built GraphHopper graph with its id and geometry, plus a hash of the graph (US-039).
 * <p>
 * Writes two files into the output folder:
 * <ul>
 *   <li>{@code edges.csv}: the header {@code edge_id,wkt}, then one row per edge in edge-id order. {@code wkt} is a
 *   LINESTRING in EPSG:4326, longitude first, through the base node, the shape points, and the adjacent node.</li>
 *   <li>{@code graph.json}: the graph hash, the edge and node counts, and the GraphHopper commit.</li>
 * </ul>
 * The graph is opened read-only, so the folder can be a read-only mount.
 * <p>
 * The hash is a SHA-256 over the node count, the edge count, and for each edge in id order its base node, its
 * adjacent node, its point count, and each point as latitude and longitude in 1e-7 degrees. It does not read file
 * timestamps, so two exports of one graph give one hash, and a re-import of the same OSM file gives it too.
 */
public final class ExportEdges {

    /** Bump when the columns, the geometry format, or the hash input change. */
    static final int FORMAT_VERSION = 1;

    private static final double SCALE = 1e7;

    public record Result(int edgeCount, int nodeCount, String graphHash) {
    }

    private ExportEdges() {
    }

    public static void main(String[] args) {
        if (args.length != 2) {
            System.err.println("usage: ExportEdges <graph-cache-folder> <output-folder>");
            System.exit(2);
        }
        Result result = export(Path.of(args[0]), Path.of(args[1]));
        System.out.printf("edges=%d nodes=%d graph_hash=%s%n", result.edgeCount(), result.nodeCount(), result.graphHash());
    }

    public static Result export(Path graphLocation, Path outputDir) {
        BaseGraph graph = openReadOnly(graphLocation);
        try {
            Files.createDirectories(outputDir);
            return write(graph, outputDir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } finally {
            graph.close();
        }
    }

    /**
     * Opens the graph store with memory-mapped, read-only files. GraphHopper's own load() is not used, because it
     * also needs a working routing profile, and the export needs only the edges. The flood graph has no elevation,
     * so it is opened as 2D.
     */
    private static BaseGraph openReadOnly(Path graphLocation) {
        // Check first: GHDirectory creates a missing folder, and a read-only mount must not be written to.
        if (!Files.isDirectory(graphLocation)) {
            throw new IllegalStateException("No graph folder at " + graphLocation + ". Import the OSM file first.");
        }
        GHDirectory directory = new GHDirectory(graphLocation.toString(), DAType.MMAP_RO);
        StorableProperties properties = new StorableProperties(directory);
        if (!properties.loadExisting()) {
            throw new IllegalStateException("No graph in " + graphLocation + ". Import the OSM file first.");
        }
        EncodingManager encodingManager = EncodingManager.fromProperties(properties);
        BaseGraph graph = new BaseGraph.Builder(encodingManager)
                .setDir(directory)
                .set3D(false)
                .withTurnCosts(encodingManager.needsTurnCostsSupport())
                .build();
        graph.loadExisting();
        return graph;
    }

    private static Result write(BaseGraph graph, Path outputDir) throws IOException {
        MessageDigest sha256 = sha256();
        int edgeCount = graph.getEdges();
        int nodeCount = graph.getNodes();
        try (BufferedWriter csv = Files.newBufferedWriter(outputDir.resolve("edges.csv"), StandardCharsets.UTF_8);
             DataOutputStream hashInput = new DataOutputStream(new DigestOutputStream(OutputStream.nullOutputStream(), sha256))) {
            csv.write("edge_id,wkt\n");
            hashInput.writeInt(nodeCount);
            hashInput.writeInt(edgeCount);
            AllEdgesIterator edges = graph.getAllEdges();
            int rows = 0;
            while (edges.next()) {
                PointList points = edges.fetchWayGeometry(FetchMode.ALL);
                csv.write(edges.getEdge() + ",\"" + lineString(points) + "\"\n");
                hashInput.writeInt(edges.getBaseNode());
                hashInput.writeInt(edges.getAdjNode());
                hashInput.writeInt(points.size());
                for (int i = 0; i < points.size(); i++) {
                    hashInput.writeLong(Math.round(points.getLat(i) * SCALE));
                    hashInput.writeLong(Math.round(points.getLon(i) * SCALE));
                }
                rows++;
            }
            if (rows != edgeCount) {
                throw new IllegalStateException("The graph reports " + edgeCount + " edges but " + rows + " were read");
            }
        }
        String hash = HexFormat.of().formatHex(sha256.digest());

        ObjectNode json = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT).createObjectNode();
        json.put("format_version", FORMAT_VERSION);
        json.put("graph_hash", hash);
        json.put("edge_count", edgeCount);
        json.put("node_count", nodeCount);
        json.put("graphhopper_commit", graphHopperCommit());
        Files.writeString(outputDir.resolve("graph.json"), json.toPrettyString() + "\n", StandardCharsets.UTF_8);
        return new Result(edgeCount, nodeCount, hash);
    }

    private static String lineString(PointList points) {
        StringBuilder wkt = new StringBuilder("LINESTRING (");
        for (int i = 0; i < points.size(); i++) {
            if (i > 0) wkt.append(", ");
            wkt.append(degrees(points.getLon(i))).append(' ').append(degrees(points.getLat(i)));
        }
        return wkt.append(')').toString();
    }

    /** Degrees to 7 decimals with no trailing zeros, so the text does not depend on the platform's formatting. */
    private static String degrees(double value) {
        return BigDecimal.valueOf(Math.round(value * SCALE)).movePointLeft(7).stripTrailingZeros().toPlainString();
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** The commit comes from the pom property graphhopper.commit, through resource filtering. */
    private static String graphHopperCommit() throws IOException {
        try (InputStream in = ExportEdges.class.getResourceAsStream("/graphhopper-commit.txt")) {
            if (in == null) throw new IllegalStateException("graphhopper-commit.txt is missing from the jar");
            return new String(in.readAllBytes(), StandardCharsets.UTF_8).trim();
        }
    }
}
