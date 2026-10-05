package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.graphhopper.GHRequest;
import com.graphhopper.GHResponse;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.config.Profile;
import com.graphhopper.routing.util.EdgeFilter;
import com.graphhopper.util.CustomModel;
import com.graphhopper.util.details.PathDetail;
import com.graphhopper.json.Statement;
import com.graphhopper.storage.index.Snap;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntBinaryOperator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * US-050 through GraphHopper's own route() call, on a hand-made corridor with a detour (src/test/resources/corridor.osm.xml).
 * The exact-minute scenarios are in TimeAwareDijkstraTest. These tests check the wiring: the hints, the profile limit,
 * the fallback to the stock search, and the edge ids of snaps in the middle of a road.
 */
class TimeAwareRouterTest {

    static final Instant T0 = Instant.parse("2026-10-05T10:00:00Z");
    static final double[] ORIGIN = {21.0000, 105.7500};
    static final double[] DESTINATION = {21.0000, 105.7560};

    static TimeAwareGraphHopper hopper;
    static int corridorEdge;
    static int leadEdge;
    static int detourEdge;
    static EdgeDepthTable current;

    @BeforeAll
    static void importGraph(@TempDir Path tmp) throws Exception {
        CustomModel model = new CustomModel()
                .addToSpeed(Statement.If("true", Statement.Op.LIMIT, "car_average_speed"))
                .addToPriority(Statement.If("!car_access", Statement.Op.MULTIPLY, "0"));
        Path osm = tmp.resolve("corridor.osm.xml");
        java.nio.file.Files.write(osm, TimeAwareRouterTest.class.getResourceAsStream("/corridor.osm.xml").readAllBytes());
        GraphHopperConfig config = new GraphHopperConfig()
                .putObject("datareader.file", osm.toString())
                .putObject("graph.location", tmp.resolve("graph").toString())
                .putObject("import.osm.ignored_highways", "")
                .putObject("graph.encoded_values", "car_access, car_average_speed")
                .setProfiles(List.of(
                        new Profile("motorbike").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 20),
                        new Profile("car").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 30),
                        new Profile("plain").setCustomModel(model)));
        hopper = new TimeAwareGraphHopper();
        hopper.init(config);
        hopper.importOrLoad();
        hopper.setTableSupplier(() -> current);
        corridorEdge = edgeNear(21.0001, 105.7530);
        leadEdge = edgeNear(21.0000, 105.7510);
        detourEdge = edgeNear(21.0015, 105.7515);
    }

    static int edgeNear(double lat, double lon) {
        Snap snap = hopper.getLocationIndex().findClosest(lat, lon, EdgeFilter.ALL_EDGES);
        assertTrue(snap.isValid(), lat + "," + lon);
        return snap.getClosestEdge().getEdge();
    }

    /** The table with depth `cm` on `edge` at the steps from minute `fromMinute`, and dry elsewhere. */
    static void flood(Path dir, int edge, int cm, int fromMinute) throws Exception {
        IntBinaryOperator depth = (e, s) -> e == edge && s * 15 >= fromMinute ? cm : 0;
        current = TestTables.table(dir, "t" + System.nanoTime() + ".bin", hopper.getBaseGraph().getEdges(),
                TestTables.quarterHours(T0, 8), depth);
    }

    static GHRequest request(String profile, boolean timeAware, double[] from, double[] to) {
        GHRequest r = new GHRequest(from[0], from[1], to[0], to[1]).setProfile(profile);
        r.setPathDetails(List.of("edge_id"));
        if (timeAware) r.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond());
        return r;
    }

    static List<Integer> edgeIds(GHResponse response) {
        List<Integer> ids = new ArrayList<>();
        for (PathDetail d : response.getBest().getPathDetails().get("edge_id")) ids.add((Integer) d.getValue());
        return ids;
    }

    @Test
    void theGraphHasTheThreeRoadsTheTestsNeed() {
        assertEquals(5, hopper.getBaseGraph().getEdges());
        assertNotNull(corridorEdge);
        assertTrue(corridorEdge != leadEdge && leadEdge != detourEdge && corridorEdge != detourEdge);
    }

    @Test
    void aRequestWithoutADepartureIsRoutedAsBefore(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("car", false, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertTrue(edgeIds(r).contains(corridorEdge), "the stock search ignores the table");
    }

    @Test
    void aRequestWithADepartureAvoidsARoadThatFloodsBeforeArrival(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertFalse(edgeIds(r).contains(corridorEdge));
        assertTrue(r.getBest().getDistance() > 800, "the detour is about 910 m, got " + r.getBest().getDistance());
    }

    @Test
    void aRoadThatFloodsAfterTheTripStaysOnTheRoute(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 60);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertTrue(edgeIds(r).contains(corridorEdge));
    }

    @Test
    void theVehicleLimitComesFromTheProfile(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 25, 0);

        assertFalse(edgeIds(hopper.route(request("motorbike", true, ORIGIN, DESTINATION))).contains(corridorEdge),
                "25 cm is over the motorbike limit of 20");
        assertTrue(edgeIds(hopper.route(request("car", true, ORIGIN, DESTINATION))).contains(corridorEdge),
                "25 cm is under the car limit of 30");
    }

    @Test
    void aProfileWithoutALimitIsRoutedAsBefore(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("plain", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertTrue(edgeIds(r).contains(corridorEdge));
    }

    @Test
    void withNoTableTheRequestIsRoutedAsBefore() {
        current = null;

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertTrue(edgeIds(r).contains(corridorEdge));
    }

    @Test
    void whenEveryRouteIsClosedThereIsNoConnection(@TempDir Path dir) throws Exception {
        // Both ways out of the origin are flooded: the lead road and the detour road.
        IntBinaryOperator depth = (e, s) -> e == leadEdge || e == detourEdge ? 50 : 0;
        current = TestTables.table(dir, "t.bin", hopper.getBaseGraph().getEdges(), TestTables.quarterHours(T0, 8), depth);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertTrue(r.hasErrors());
        assertTrue(r.getErrors().get(0).getMessage().contains("Connection between locations not found"), r.getErrors().toString());
    }

    @Test
    void aSnapInTheMiddleOfAFloodedRoadReadsTheDepthOfThatRoad(@TempDir Path dir) throws Exception {
        // The origin is half way along the lead road. Both halves are virtual edges of it, and the road is flooded.
        double[] middleOfLead = {21.0000, 105.7510};
        flood(dir, leadEdge, 50, 0);
        GHResponse flooded = hopper.route(request("car", true, middleOfLead, DESTINATION));
        assertTrue(flooded.hasErrors(), "both ways out of a flooded road are closed");

        flood(dir, corridorEdge, 0, 0);
        GHResponse dry = hopper.route(request("car", true, middleOfLead, DESTINATION));
        assertFalse(dry.hasErrors(), dry.getErrors().toString());
    }
}
