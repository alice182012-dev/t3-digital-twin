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
import java.util.Optional;
import java.util.function.IntBinaryOperator;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
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

    /** Hands the router the table of the test, counts the calls, and says why there is none when there is none. */
    static final class FakeProvider implements TableProvider {
        int calls;
        String problem = "no table has been published";

        @Override
        public Optional<EdgeDepthTable> current() {
            calls++;
            return Optional.ofNullable(current);
        }

        @Override
        public Optional<String> problem() {
            return current == null ? Optional.of(problem) : Optional.empty();
        }

        @Override
        public Optional<String> graphHash() {
            return Optional.of(TestTables.HASH);
        }
    }

    static final FakeProvider provider = new FakeProvider();

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
                        new Profile("truck").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 35),
                        new Profile("foot").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 40),
                        new Profile("truck60").setCustomModel(model).putHint(TimeAwareRouter.LIMIT_HINT, 35)
                                .putHint(TimeAwareRouter.PRECAUTION_FRACTION_HINT, 0.6),
                        new Profile("plain").setCustomModel(model)));
        hopper = new TimeAwareGraphHopper();
        hopper.init(config);
        hopper.importOrLoad();
        hopper.setTableProvider(provider);
        corridorEdge = edgeNear(21.0001, 105.7530);
        leadEdge = edgeNear(21.0000, 105.7510);
        detourEdge = edgeNear(21.0015, 105.7515);
    }

    @BeforeEach
    void resetProvider() {
        provider.calls = 0;
        provider.problem = "no table has been published";
        current = null;
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

    /** The edges of the last path, which is the route planned with the vehicle's limit (the only path when there is one). */
    static List<Integer> edgeIds(GHResponse response) {
        List<Integer> ids = new ArrayList<>();
        var paths = response.getAll();
        for (PathDetail d : paths.get(paths.size() - 1).getPathDetails().get("edge_id")) ids.add((Integer) d.getValue());
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

    // The decision, the hints, and the departure step (US-052).

    static String hint(GHResponse r, String key) {
        return r.getHints().getString(key, null);
    }

    static long hintLong(GHResponse r, String key) {
        return r.getHints().getLong(key, -1);
    }

    @Test
    void aRequestWithoutADepartureCarriesNoTimeAwareHints(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("car", false, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertFalse(r.getHints().has("td.status"));
        assertFalse(r.getHints().has("td.run"));
        assertEquals(0, provider.calls, "the table is not read for a request that is not time-aware");
    }

    @Test
    void anAppliedRequestNamesTheRunAndTheLastStep(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertEquals("applied", hint(r, "td.status"));
        assertEquals("20261005T000000", hint(r, "td.run"));
        assertEquals(T0.getEpochSecond() + 7 * 900, hintLong(r, "td.last_step"));
        assertEquals(T0.getEpochSecond(), hintLong(r, "td.departure"));
    }

    @Test
    void withNoTableTheResponseSaysFallbackAndWhy() {
        provider.problem = "no table has been published in /tables";

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals("fallback", hint(r, "td.status"));
        assertTrue(hint(r, "td.reason").contains("no table has been published in /tables"), hint(r, "td.reason"));
        assertFalse(r.getHints().has("td.run"));
    }

    @Test
    void aTableForAnotherGraphIsAFallbackThatNamesBothHashes() {
        provider.problem = "stale edge depth table: run X was built for graph hash AAA, but the loaded graph has hash BBB";

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertEquals("fallback", hint(r, "td.status"));
        assertTrue(hint(r, "td.reason").contains("AAA") && hint(r, "td.reason").contains("BBB"), hint(r, "td.reason"));
    }

    @Test
    void aProfileWithNoDepthLimitIsAFallbackEvenWithATable(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        GHResponse r = hopper.route(request("plain", true, ORIGIN, DESTINATION));

        assertEquals("fallback", hint(r, "td.status"));
        assertTrue(hint(r, "td.reason").contains(TimeAwareRouter.LIMIT_HINT), hint(r, "td.reason"));
        assertTrue(edgeIds(r).contains(corridorEdge), "the stock search ignores the table");
    }

    @Test
    void aDepartureBetweenStepsCountsTheStepThatContainsIt(@TempDir Path dir) throws Exception {
        // The road is wet at the first step only. A departure 7 minutes in lies between the steps at 0 and 15 minutes,
        // and the step at 0 describes the road now, so it must close the road.
        IntBinaryOperator depth = (e, s) -> e == corridorEdge && s == 0 ? 50 : 0;
        current = TestTables.table(dir, "t.bin", hopper.getBaseGraph().getEdges(), TestTables.quarterHours(T0, 8), depth);
        GHRequest request = request("car", true, ORIGIN, DESTINATION);
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond() + 7 * 60);

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertFalse(edgeIds(r).contains(corridorEdge));
        assertEquals(T0.getEpochSecond(), hintLong(r, "td.departure"), "floored to the step that contains it");
    }

    @Test
    void arrivalsCountFromTheRequestedDepartureNotFromTheFlooredStep(@TempDir Path dir) throws Exception {
        // Requested at 899 s, floored to 0 s, the corridor wet from the step at 900 s. The real entry is after 899 s, so
        // the window reaches 900 s. Counted from 0 s it would reach 900 s only for a lead road of 300 s or more.
        flood(dir, corridorEdge, 50, 15);
        GHRequest request = request("car", true, ORIGIN, DESTINATION);
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond() + 899);

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertFalse(edgeIds(r).contains(corridorEdge));
        assertEquals(T0.getEpochSecond(), hintLong(r, "td.departure"), "the hint still names the floored step");
    }

    @Test
    void aTripThatEndsAfterTheLastStepIsUnknown(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 0, 0);
        GHRequest request = request("car", true, ORIGIN, DESTINATION);
        long lastStep = T0.getEpochSecond() + 7 * 900;
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, lastStep - 5);

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals("unknown", hint(r, "td.status"));
        assertEquals("20261005T000000", hint(r, "td.run"));
    }

    @Test
    void aTripThatEndsBeforeTheLastStepIsApplied(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 0, 0);
        GHRequest request = request("car", true, ORIGIN, DESTINATION);
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond() + 3600);

        assertEquals("applied", hint(hopper.route(request), "td.status"));
    }

    @Test
    void theHorizonEdgeIsKnown() {
        long last = 1_000_000L;
        assertFalse(TimeAwareRouter.endsAfterLastStep(last - 60_000, 60_000, last), "arrival exactly at the last step is known");
        assertTrue(TimeAwareRouter.endsAfterLastStep(last - 60_000, 60_001, last));
        assertFalse(TimeAwareRouter.endsAfterLastStep(0, 0, last));
    }

    @Test
    void oneRunIsPinnedForAWholeViaRequest(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);
        GHRequest request = new GHRequest(List.of(
                new com.graphhopper.util.shapes.GHPoint(ORIGIN[0], ORIGIN[1]),
                new com.graphhopper.util.shapes.GHPoint(21.0030, 105.7530),
                new com.graphhopper.util.shapes.GHPoint(DESTINATION[0], DESTINATION[1]))).setProfile("car");
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond());

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(1, provider.calls, "one read of the table per request, for every leg");
    }

    @Test
    void theDepthLimitHintIsReadFromTheProfileInTheYamlConfig() throws Exception {
        Path config = Path.of("../../floodmap/graphhopper-flood-road/graphhopper/config.yml");
        org.junit.jupiter.api.Assumptions.assumeTrue(java.nio.file.Files.exists(config), "the repo's config.yml is not in this build context");
        var mapper = new com.fasterxml.jackson.databind.ObjectMapper(new com.fasterxml.jackson.dataformat.yaml.YAMLFactory());
        var profiles = mapper.readTree(config.toFile()).get("graphhopper").get("profiles");
        java.util.Map<String, Integer> limits = new java.util.HashMap<>();
        for (var node : profiles) {
            Profile profile = mapper.treeToValue(node, Profile.class);
            if (profile.getHints().has(TimeAwareRouter.LIMIT_HINT)) {
                limits.put(profile.getName(), profile.getHints().getInt(TimeAwareRouter.LIMIT_HINT, -1));
            }
        }
        assertEquals(java.util.Map.of("motorbike", 20, "car", 30, "truck", 35, "foot", 40), limits);
        assertEquals(limits, ScenarioReport.VEHICLE_LIMITS_CM, "the server report must use the limits of config.yml");
    }

    @Test
    void theDepartureFieldOfAJsonBodyArrivesAsAHint(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);
        String body = "{\"points\": [[105.7500, 21.0000], [105.7560, 21.0000]], \"profile\": \"car\", "
                + "\"points_encoded\": false, \"td_departure\": " + T0.getEpochSecond() + "}";
        GHRequest request = com.graphhopper.jackson.Jackson.newObjectMapper().readValue(body, GHRequest.class);

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals("applied", hint(r, "td.status"));
        assertTrue(r.getBest().getDistance() > 800, "the detour is about 910 m, got " + r.getBest().getDistance());
    }

    @Test
    void eachOfTheFourVehiclesUsesItsOwnLimit(@TempDir Path dir) throws Exception {
        java.util.Map<String, Integer> limits = java.util.Map.of("motorbike", 20, "car", 30, "truck", 35, "foot", 40);
        int checked = 0;
        for (int depth : new int[] {15, 25, 32, 37, 45}) {
            flood(dir, corridorEdge, depth, 0);
            for (var vehicle : limits.entrySet()) {
                GHResponse r = hopper.route(request(vehicle.getKey(), true, ORIGIN, DESTINATION));

                assertFalse(r.hasErrors(), r.getErrors().toString());
                assertEquals("applied", hint(r, "td.status"), vehicle.getKey());
                boolean blocked = depth >= vehicle.getValue();
                assertEquals(!blocked, edgeIds(r).contains(corridorEdge),
                        vehicle.getKey() + " at " + depth + " cm, limit " + vehicle.getValue());
                checked++;
            }
        }
        assertEquals(20, checked);
    }

    @Test
    void aTdInfoRequestCarriesTheGraphHashAndTheRunAndDoesNotChangeTheRoute(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);
        GHRequest request = request("car", false, ORIGIN, DESTINATION);
        request.getHints().putObject(TimeAwareRouter.INFO_HINT, true);

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(TestTables.HASH, hint(r, "td.graph_hash"));
        assertEquals("20261005T000000", hint(r, "td.run"));
        assertFalse(r.getHints().has("td.status"), "no search ran");
        assertTrue(edgeIds(r).contains(corridorEdge), "the route is the stock route, which ignores the table");
    }

    @Test
    void aTdInfoRequestWithNoTableStillCarriesTheGraphHash() {
        provider.problem = "no table has been published";
        GHRequest request = request("car", false, ORIGIN, DESTINATION);
        request.getHints().putObject(TimeAwareRouter.INFO_HINT, true);

        GHResponse r = hopper.route(request);

        assertEquals(TestTables.HASH, hint(r, "td.graph_hash"));
        assertFalse(r.getHints().has("td.run"));
    }

    @Test
    void aRequestWithoutTdInfoCarriesNoGraphHash(@TempDir Path dir) throws Exception {
        flood(dir, corridorEdge, 50, 0);

        assertFalse(hopper.route(request("car", true, ORIGIN, DESTINATION)).getHints().has("td.graph_hash"));
    }

    // The two-option plan of D-021: a recommended route under the precaution depth and the limit route.

    /** The table with depth `cm` on each of `edges` at every step, and dry elsewhere. */
    static void floodAll(Path dir, int cm, int... edges) throws Exception {
        IntBinaryOperator depth = (e, s) -> {
            for (int flooded : edges) if (e == flooded) return cm;
            return 0;
        };
        current = TestTables.table(dir, "t" + System.nanoTime() + ".bin", hopper.getBaseGraph().getEdges(),
                TestTables.quarterHours(T0, 8), depth);
    }

    @Test
    void aDryRouteIsOnePathAndRecommended(@TempDir Path dir) throws Exception {
        floodAll(dir, 0, corridorEdge);
        int before = TimeAwareRouter.precautionSearches.get();

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(1, r.getAll().size());
        assertEquals("recommended", hint(r, "td.kinds"));
        assertEquals(30, hintLong(r, "td.limit_cm"));
        assertEquals(15, hintLong(r, "td.precaution_cm"));
        assertEquals(before, TimeAwareRouter.precautionSearches.get(), "no road reaches the precaution depth, so no second search");
    }

    @Test
    void aRoadBetweenTheTwoDepthsGivesTheDryDetourFirstAndTheLimitRouteSecond(@TempDir Path dir) throws Exception {
        floodAll(dir, 20, corridorEdge);
        int before = TimeAwareRouter.precautionSearches.get();

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(2, r.getAll().size());
        assertEquals("recommended,through_water", hint(r, "td.kinds"));
        assertFalse(r.getAll().get(0).getPathDetails().get("edge_id").stream().anyMatch(d -> d.getValue().equals(corridorEdge)),
                "path 0 is the detour");
        assertTrue(r.getAll().get(1).getPathDetails().get("edge_id").stream().anyMatch(d -> d.getValue().equals(corridorEdge)),
                "path 1 is the limit route through the corridor");
        assertTrue(r.getAll().get(0).getDistance() > r.getAll().get(1).getDistance());
        assertEquals("applied", hint(r, "td.status"));
        assertEquals(before + 1, TimeAwareRouter.precautionSearches.get());
    }

    @Test
    void withNoDetourTheLimitRouteIsTheOnlyPathAndIsThroughWater(@TempDir Path dir) throws Exception {
        floodAll(dir, 20, corridorEdge, detourEdge);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(1, r.getAll().size());
        assertEquals("through_water", hint(r, "td.kinds"));
        assertTrue(edgeIds(r).contains(corridorEdge));
        assertEquals(30, hintLong(r, "td.limit_cm"));
        assertEquals(15, hintLong(r, "td.precaution_cm"));
    }

    @Test
    void aRoadAtTheLimitStillClosesTheLimitRoute(@TempDir Path dir) throws Exception {
        floodAll(dir, 30, corridorEdge);

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(1, r.getAll().size());
        assertEquals("recommended", hint(r, "td.kinds"));
        assertFalse(edgeIds(r).contains(corridorEdge));
    }

    @Test
    void theFractionComesFromTheProfile(@TempDir Path dir) throws Exception {
        floodAll(dir, 20, corridorEdge);
        // truck: limit 35, so 0.5 gives 18 cm and a 20 cm road is over it. 0.6 gives 21 cm and the road is under it.
        assertEquals("recommended,through_water", hint(hopper.route(request("truck", true, ORIGIN, DESTINATION)), "td.kinds"));
        assertEquals(18, hintLong(hopper.route(request("truck", true, ORIGIN, DESTINATION)), "td.precaution_cm"));
        assertEquals(21, hintLong(hopper.route(request("truck60", true, ORIGIN, DESTINATION)), "td.precaution_cm"));
        assertEquals("recommended", hint(hopper.route(request("truck60", true, ORIGIN, DESTINATION)), "td.kinds"));
    }

    @Test
    void aViaRequestWithAShallowRoadGivesTheDryDetourFirstAndTheLimitRouteSecond(@TempDir Path dir) throws Exception {
        floodAll(dir, 20, corridorEdge);
        int before = TimeAwareRouter.precautionSearches.get();
        GHRequest request = new GHRequest(List.of(
                new com.graphhopper.util.shapes.GHPoint(ORIGIN[0], ORIGIN[1]),
                new com.graphhopper.util.shapes.GHPoint(21.0000, 105.7540),
                new com.graphhopper.util.shapes.GHPoint(DESTINATION[0], DESTINATION[1]))).setProfile("car");
        request.setPathDetails(List.of("edge_id"));
        request.getHints().putObject(TimeAwareRouter.DEPARTURE_HINT, T0.getEpochSecond());

        GHResponse r = hopper.route(request);

        assertFalse(r.hasErrors(), r.getErrors().toString());
        assertEquals(2, r.getAll().size());
        assertEquals("recommended,through_water", hint(r, "td.kinds"));
        assertFalse(r.getAll().get(0).getPathDetails().get("edge_id").stream().anyMatch(d -> d.getValue().equals(corridorEdge)),
                "path 0 reaches the via point by the detour");
        assertTrue(r.getAll().get(1).getPathDetails().get("edge_id").stream().anyMatch(d -> d.getValue().equals(corridorEdge)),
                "path 1 crosses the corridor");
        assertTrue(r.getAll().get(0).getDistance() > r.getAll().get(1).getDistance());
        assertEquals(before + 1, TimeAwareRouter.precautionSearches.get(), "one second search for the whole request");
        assertEquals(1, provider.calls, "one read of the table per request, for every leg and both searches");
    }

    @Test
    void aFallbackCarriesNoKinds() {
        provider.problem = "no table has been published";

        GHResponse r = hopper.route(request("car", true, ORIGIN, DESTINATION));

        assertEquals("fallback", hint(r, "td.status"));
        assertFalse(r.getHints().has("td.kinds"));
        assertEquals(1, r.getAll().size());
    }

    @Test
    void aRequestWithoutADepartureCarriesNoKinds(@TempDir Path dir) throws Exception {
        floodAll(dir, 20, corridorEdge);

        GHResponse r = hopper.route(request("car", false, ORIGIN, DESTINATION));

        assertFalse(r.getHints().has("td.kinds"));
        assertEquals(1, r.getAll().size());
    }
}
