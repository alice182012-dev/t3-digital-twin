package com.graphhopper.timeaware;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.nio.file.Path;
import java.time.Duration;

/**
 * Reads the table that `latest` names with the production reader (US-043), for the check on the server.
 *
 * <pre>
 * EdgeDepthTableTool &lt;table-folder&gt; [--graph-hash H | --graph-folder DIR] [--watch SECONDS]
 * </pre>
 *
 * Prints the header and a few depths. With a hash (given, or computed from a graph folder opened read-only) it also
 * checks that the table was built for that graph. Exit code 0 is a pass, 1 is a stale table, 2 is anything else
 * (usage, no pointer, a damaged file, no graph folder). With --watch it then follows the pointer for that many
 * seconds with {@link LatestTableSource} and prints each table it loads.
 */
public final class EdgeDepthTableTool {

    private EdgeDepthTableTool() {
    }

    public static void main(String[] args) {
        System.exit(run(args, System.out));
    }

    static int run(String[] args, PrintStream out) {
        if (args.length == 0) {
            out.println("usage: EdgeDepthTableTool <table-folder> [--graph-hash H | --graph-folder DIR] [--watch SECONDS]");
            return 2;
        }
        Path folder = Path.of(args[0]);
        String graphHash = null;
        long watchSeconds = 0;
        try {
            for (int i = 1; i < args.length; i++) {
                switch (args[i]) {
                    case "--graph-hash" -> graphHash = args[++i];
                    case "--graph-folder" -> graphHash = GraphHash.of(Path.of(args[++i]));
                    case "--watch" -> watchSeconds = Long.parseLong(args[++i]);
                    default -> {
                        out.println("unknown option " + args[i]);
                        return 2;
                    }
                }
            }
        } catch (ArrayIndexOutOfBoundsException | NumberFormatException e) {
            out.println("usage: an option is missing its value");
            return 2;
        } catch (IllegalStateException e) {
            out.println(e.getMessage());
            return 2;
        }

        EdgeDepthTable table;
        try {
            Path pointer = folder.resolve("latest");
            String name = Files.readString(pointer).strip();
            table = EdgeDepthTable.open(folder.resolve(name));
            out.println("table=" + name);
        } catch (NoSuchFileException e) {
            out.println("cannot read " + e.getFile() + ": no such file (is `latest` in " + folder + "?)");
            return 2;
        } catch (IOException | TableFormatException e) {
            out.println("cannot read the table: " + e.getMessage());
            return 2;
        }

        out.println("run=" + table.runName() + " edges=" + table.edgeCount() + " steps=" + table.stepCount());
        out.println("graph_hash=" + table.graphHash());
        out.println("first_step=" + table.stepTimes().get(0) + " last_step=" + table.stepTimes().get(table.stepCount() - 1));
        printDepths(table, out);

        if (graphHash != null) {
            try {
                table.requireGraphHash(graphHash);
                out.println("graph hash matches: " + graphHash);
            } catch (StaleTableException e) {
                out.println("STALE: " + e.getMessage());
                return 1;
            }
        }

        if (watchSeconds > 0) {
            return watch(folder, graphHash == null ? table.graphHash() : graphHash, watchSeconds, out);
        }
        out.println("PASS");
        return 0;
    }

    private static void printDepths(EdgeDepthTable table, PrintStream out) {
        int wet = 0;
        int deepest = 0;
        int deepestEdge = -1;
        int step = 0;
        for (int edge = 0; edge < table.edgeCount(); edge++) {
            int d = table.depthCm(edge, step);
            if (d > 0) wet++;
            if (d > deepest) {
                deepest = d;
                deepestEdge = edge;
            }
        }
        out.println("step 0: wet_edges=" + wet + " deepest_cm=" + deepest + " at_edge=" + deepestEdge);
        for (int edge = 0; edge < Math.min(3, table.edgeCount()); edge++) {
            out.println("edge=" + edge + " step=0 depth_cm=" + table.depthCm(edge, 0));
        }
    }

    private static int watch(Path folder, String graphHash, long seconds, PrintStream out) {
        out.println("watching " + folder + " for " + seconds + " s, polling every " + LatestTableSource.DEFAULT_INTERVAL.toSeconds() + " s");
        try (LatestTableSource source = new LatestTableSource(folder, graphHash, Duration.ofSeconds(1))) {
            source.start();
            String seen = source.currentName().orElse("none");
            out.println("serving table=" + seen);
            long deadline = System.nanoTime() + Duration.ofSeconds(seconds).toNanos();
            while (System.nanoTime() < deadline) {
                Thread.sleep(200);
                String now = source.currentName().orElse("none");
                if (!now.equals(seen)) {
                    out.println("serving table=" + now + " (loaded from the pointer without a restart)");
                    seen = now;
                }
            }
            out.println("PASS");
            return 0;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return 2;
        }
    }
}
