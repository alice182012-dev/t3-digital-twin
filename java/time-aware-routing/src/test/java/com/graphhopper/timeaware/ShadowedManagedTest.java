package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.graphhopper.GraphHopperConfig;
import com.graphhopper.http.GraphHopperBundle;
import com.graphhopper.http.GraphHopperManaged;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * GraphHopperBundle calls {@code new GraphHopperManaged(...)}. These tests fail if the stock class is the one
 * that loads, so a silent fallback to the stock GraphHopper cannot pass.
 */
class ShadowedManagedTest {

    private static Path locationOf(Class<?> type) throws URISyntaxException {
        return Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI());
    }

    @Test
    void theClassTheBundleCallsComesFromThisModule() throws Exception {
        assertEquals(locationOf(TimeAwareGraphHopper.class), locationOf(GraphHopperManaged.class));
        assertNotEquals(locationOf(GraphHopperBundle.class), locationOf(GraphHopperManaged.class));
    }

    @Test
    void itBuildsATimeAwareGraphHopper(@TempDir Path graphDir) {
        GraphHopperConfig config = new GraphHopperConfig()
                .putObject("graph.location", graphDir.toString())
                .putObject("import.osm.ignored_highways", "");

        GraphHopperManaged managed = new GraphHopperManaged(config);

        assertInstanceOf(TimeAwareGraphHopper.class, managed.getGraphHopper());
    }

    @Test
    void itRefusesAGtfsConfiguration(@TempDir Path graphDir) throws Exception {
        Path gtfs = Files.createFile(graphDir.resolve("feed.zip"));
        GraphHopperConfig config = new GraphHopperConfig().putObject("gtfs.file", gtfs.toString());

        assertThrows(IllegalArgumentException.class, () -> new GraphHopperManaged(config));
    }
}
