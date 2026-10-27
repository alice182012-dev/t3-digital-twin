package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.graphhopper.GHRequest;
import com.graphhopper.GHResponse;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.config.Profile;
import com.graphhopper.json.Statement;
import com.graphhopper.util.CustomModel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * US-052: TimeAwareGraphHopper reads the table folder from `time_aware.table_dir` after it loads the graph, hashes the
 * loaded graph, and follows `latest`. The hash of the loaded graph has to equal the hash the export wrote, or every
 * request falls back.
 */
class TimeAwareGraphHopperLoadTest {

    static final Instant T0 = Instant.parse("2026-10-05T10:00:00Z");

    private static GraphHopperConfig config(Path dir, Path osm, String tableDir) {
        CustomModel model = new CustomModel()
                .addToSpeed(Statement.If("true", Statement.Op.LIMIT, "car_average_speed"))
                .addToPriority(Statement.If("!car_access", Statement.Op.MULTIPLY, "0"));
        GraphHopperConfig config = new GraphHopperConfig()
                .putObject("datareader.file", osm.toString())
                .putObject("graph.location", dir.resolve("graph").toString())
                .putObject("import.osm.ignored_highways", "")
                .putObject("graph.encoded_values", "car_access, car_average_speed, osm_way_id")
                .setProfiles(List.of(new Profile("car").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 30)));
        if (tableDir != null) config.putObject("time_aware.table_dir", tableDir);
        return config;
    }

    private static Path osm(Path dir) throws Exception {
        Path osm = dir.resolve("corridor.osm.xml");
        Files.write(osm, TimeAwareGraphHopperLoadTest.class.getResourceAsStream("/corridor.osm.xml").readAllBytes());
        return osm;
    }

    private static GHRequest request() {
        GHRequest r = new GHRequest(21.0000, 105.7500, 21.0000, 105.7560).setProfile("car");
        r.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond());
        return r;
    }

    private static void publish(Path tables, String graphHash, int edges) throws Exception {
        Files.createDirectories(tables);
        TestTables.table(tables, "20261005T000000.bin", graphHash, edges, TestTables.quarterHours(T0, 8), (e, s) -> 0);
        Files.writeString(tables.resolve("latest"), "20261005T000000.bin\n");
    }

    @Test
    void theHashOfTheLoadedGraphEqualsTheHashOfTheExport(@TempDir Path dir) throws Exception {
        TimeAwareGraphHopper first = new TimeAwareGraphHopper();
        first.init(config(dir, osm(dir), null));
        first.importOrLoad();
        String loaded = GraphHash.compute(first.getBaseGraph());
        int edges = first.getBaseGraph().getEdges();
        first.close();

        assertEquals(loaded, ExportEdges.export(dir.resolve("graph"), dir.resolve("out")).graphHash());
        assertEquals(5, edges);
    }

    @Test
    void aTableForTheLoadedGraphIsFollowedAndAppliedToARequest(@TempDir Path dir) throws Exception {
        TimeAwareGraphHopper first = new TimeAwareGraphHopper();
        first.init(config(dir, osm(dir), null));
        first.importOrLoad();
        String hash = GraphHash.compute(first.getBaseGraph());
        int edges = first.getBaseGraph().getEdges();
        first.close();
        Path tables = dir.resolve("tables");
        publish(tables, hash, edges);

        TimeAwareGraphHopper hopper = new TimeAwareGraphHopper();
        hopper.init(config(dir, osm(dir), tables.toString()));
        hopper.importOrLoad();
        try {
            GHResponse r = hopper.route(request());

            assertFalse(r.hasErrors(), r.getErrors().toString());
            assertEquals("applied", r.getHints().getString("td.status", null));
            assertEquals("20261005T000000", r.getHints().getString("td.run", null));
        } finally {
            hopper.close();
        }
    }

    @Test
    void aTableForAnotherGraphIsAFallbackThatNamesBothHashes(@TempDir Path dir) throws Exception {
        TimeAwareGraphHopper first = new TimeAwareGraphHopper();
        first.init(config(dir, osm(dir), null));
        first.importOrLoad();
        String hash = GraphHash.compute(first.getBaseGraph());
        int edges = first.getBaseGraph().getEdges();
        first.close();
        Path tables = dir.resolve("tables");
        publish(tables, "f".repeat(64), edges);

        TimeAwareGraphHopper hopper = new TimeAwareGraphHopper();
        hopper.init(config(dir, osm(dir), tables.toString()));
        hopper.importOrLoad();
        try {
            GHResponse r = hopper.route(request());

            assertFalse(r.hasErrors(), r.getErrors().toString());
            assertEquals("fallback", r.getHints().getString("td.status", null));
            String reason = r.getHints().getString("td.reason", "");
            assertTrue(reason.contains(hash) && reason.contains("f".repeat(64)), reason);
        } finally {
            hopper.close();
        }
    }

    @Test
    void withNoTableFolderConfiguredARequestFallsBackAndSaysSo(@TempDir Path dir) throws Exception {
        TimeAwareGraphHopper hopper = new TimeAwareGraphHopper();
        hopper.init(config(dir, osm(dir), null));
        hopper.importOrLoad();
        try {
            GHResponse r = hopper.route(request());

            assertEquals("fallback", r.getHints().getString("td.status", null));
            assertTrue(r.getHints().getString("td.reason", "").contains("time_aware.table_dir"));
        } finally {
            hopper.close();
        }
    }

    @Test
    void anEmptyTableFolderIsAFallbackNotAnError(@TempDir Path dir) throws Exception {
        Path tables = Files.createDirectories(dir.resolve("tables"));
        TimeAwareGraphHopper hopper = new TimeAwareGraphHopper();
        hopper.init(config(dir, osm(dir), tables.toString()));
        hopper.importOrLoad();
        try {
            GHResponse r = hopper.route(request());

            assertFalse(r.hasErrors(), r.getErrors().toString());
            assertEquals("fallback", r.getHints().getString("td.status", null));
        } finally {
            hopper.close();
        }
    }
}
