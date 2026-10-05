package com.graphhopper.timeaware;

import com.graphhopper.routing.util.AllEdgesIterator;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.util.FetchMode;
import com.graphhopper.util.PointList;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.nio.file.Path;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * The graph hash that tags every edge depth table (US-039, US-043): a SHA-256 over the node count, the edge count, and
 * for each edge in id order its base node, its adjacent node, its point count and its points in 1e-7 degrees. The
 * export writes it to graph.json, the table builder copies it into the table header, and the reader compares it with
 * the hash of the graph it has loaded.
 */
public final class GraphHash {

    private GraphHash() {
    }

    public static String compute(BaseGraph graph) {
        MessageDigest sha256 = sha256();
        try (DataOutputStream in = new DataOutputStream(new DigestOutputStream(OutputStream.nullOutputStream(), sha256))) {
            in.writeInt(graph.getNodes());
            in.writeInt(graph.getEdges());
            AllEdgesIterator edges = graph.getAllEdges();
            while (edges.next()) {
                PointList points = edges.fetchWayGeometry(FetchMode.ALL);
                in.writeInt(edges.getBaseNode());
                in.writeInt(edges.getAdjNode());
                in.writeInt(points.size());
                for (int i = 0; i < points.size(); i++) {
                    in.writeLong(Math.round(points.getLat(i) * ExportEdges.SCALE));
                    in.writeLong(Math.round(points.getLon(i) * ExportEdges.SCALE));
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return HexFormat.of().formatHex(sha256.digest());
    }

    /** The hash of the graph folder, opened read-only as the export does. */
    public static String of(Path graphLocation) {
        BaseGraph graph = ExportEdges.openReadOnly(graphLocation);
        try {
            return compute(graph);
        } finally {
            graph.close();
        }
    }

    private static MessageDigest sha256() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
