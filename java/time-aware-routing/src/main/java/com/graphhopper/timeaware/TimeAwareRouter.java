package com.graphhopper.timeaware;

import com.graphhopper.GHRequest;
import com.graphhopper.GHResponse;
import com.graphhopper.config.Profile;
import com.graphhopper.routing.FlexiblePathCalculator;
import com.graphhopper.routing.Path;
import com.graphhopper.routing.RoutingAlgorithm;
import com.graphhopper.routing.Router;
import com.graphhopper.routing.RouterConfig;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.lm.LandmarkStorage;
import com.graphhopper.routing.querygraph.QueryGraph;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.RoutingCHGraph;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.util.PMap;
import com.graphhopper.util.TranslationMap;
import com.graphhopper.util.details.PathDetailsBuilderFactory;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiConsumer;

/**
 * The router of US-050 and US-052. A request that carries the hint {@value #DEPARTURE_HINT} (epoch seconds) is
 * time-aware. It is routed with {@link TimeAwareDijkstra} over the current edge depth table when a table is available and
 * the profile has the hint {@value #LIMIT_HINT} (the vehicle's depth limit in cm). Otherwise it goes the stock way and
 * the response says `fallback` and why. A request without the departure hint is untouched and its response is unchanged.
 * <p>
 * GraphHopper makes a new router for every request, so the decision is made once and held in a field. That pins one
 * table for all the legs of the request. The response hints are {@value #STATUS_HINT} (`applied`, `unknown`, or
 * `fallback`), {@value #RUN_HINT}, {@value #DEPARTURE_RESPONSE_HINT}, {@value #LAST_STEP_HINT} (epoch seconds), and
 * {@value #REASON_HINT} for a fallback. A request with {@value #INFO_HINT} also gets {@value #GRAPH_HASH_HINT} and the run. A time-aware search cannot use landmarks or contraction hierarchies, because
 * their bounds and shortcuts do not know the time, so it always uses the flexible solver.
 * <p>
 * The two-option plan of decision D-021. The request is first planned with the profile's hard limit. When that route
 * enters a road whose depth reaches the precaution depth {@code P = fraction * limit} inside the sticky window, a second
 * search runs with the closure built at {@code P}. If it finds a route, the response has two paths: path 0 is the route
 * under {@code P} (recommended) and path 1 is the limit route. If it finds none, the response has the limit route only. The
 * fraction is the profile hint {@value #PRECAUTION_FRACTION_HINT}, read beside {@value #LIMIT_HINT} and 0.5 when absent. The
 * hint {@value #KINDS_HINT} lists one kind per path: `recommended` or `through_water`. {@value #LIMIT_CM_HINT} and
 * {@value #PRECAUTION_CM_HINT} are the two depths. A limit route clear of {@code P} is the only path and costs no second
 * search.
 */
public class TimeAwareRouter extends Router {

    public static final String DEPARTURE_HINT = "td_departure";
    public static final String LIMIT_HINT = "td_limit_cm";
    /** A profile hint: the share of the limit that makes the precaution depth. */
    public static final String PRECAUTION_FRACTION_HINT = "td_precaution_fraction";
    public static final double DEFAULT_PRECAUTION_FRACTION = 0.5;
    public static final String STATUS_HINT = "td.status";
    public static final String RUN_HINT = "td.run";
    public static final String DEPARTURE_RESPONSE_HINT = "td.departure";
    public static final String LAST_STEP_HINT = "td.last_step";
    public static final String REASON_HINT = "td.reason";
    public static final String KINDS_HINT = "td.kinds";
    public static final String LIMIT_CM_HINT = "td.limit_cm";
    public static final String PRECAUTION_CM_HINT = "td.precaution_cm";
    public static final String KIND_RECOMMENDED = "recommended";
    public static final String KIND_THROUGH_WATER = "through_water";
    /** A request with this hint gets the graph hash and the run in its response and is otherwise routed as before. */
    public static final String INFO_HINT = "td_info";
    public static final String GRAPH_HASH_HINT = "td.graph_hash";

    /** Counts the second searches of the whole process, so a test can check that a clear limit route costs none. */
    static final AtomicInteger precautionSearches = new AtomicInteger();

    /** A route that the search returned, with the weighting that made it. */
    record Leg(Path path, Weighting weighting) {
    }

    private final TableProvider tables;
    private final List<Leg> legs = new ArrayList<>();
    private Decision decision = Decision.NOT_REQUESTED;

    /**
     * What this request gets. Not requested: no hints. Fallback: the stock search, with a reason. Applied: the closure at
     * the limit, and the closure at the precaution depth for the second search.
     */
    record Decision(StickyClosure closure, StickyClosure precaution, String fallbackReason, long requestedDepartureMs) {
        static final Decision NOT_REQUESTED = new Decision(null, null, null, 0);

        boolean requested() {
            return closure != null || fallbackReason != null;
        }
    }

    public TimeAwareRouter(BaseGraph graph, EncodingManager encodingManager, LocationIndex locationIndex,
                           Map<String, Profile> profilesByName, PathDetailsBuilderFactory pathDetailsBuilderFactory,
                           TranslationMap translationMap, RouterConfig routerConfig, WeightingFactory weightingFactory,
                           Map<String, RoutingCHGraph> chGraphs, Map<String, LandmarkStorage> landmarks,
                           TableProvider tables) {
        super(graph, encodingManager, locationIndex, profilesByName, pathDetailsBuilderFactory, translationMap, routerConfig,
                weightingFactory, chGraphs, landmarks);
        this.tables = tables;
    }

    /** Decides once per request. The table is read here and nowhere else, so every leg uses the same run. */
    Decision decide(GHRequest request) {
        PMap hints = request.getHints();
        if (!hints.has(DEPARTURE_HINT)) return Decision.NOT_REQUESTED;
        Profile profile = profilesByName.get(request.getProfile());
        if (profile == null || !profile.getHints().has(LIMIT_HINT)) {
            return new Decision(null, null,
                    "the profile '" + request.getProfile() + "' has no depth limit (" + LIMIT_HINT + ")", 0);
        }
        double fraction = profile.getHints().getDouble(PRECAUTION_FRACTION_HINT, DEFAULT_PRECAUTION_FRACTION);
        if (!(fraction > 0 && fraction <= 1)) {
            return new Decision(null, null, "the profile '" + request.getProfile() + "' has " + PRECAUTION_FRACTION_HINT
                    + " " + fraction + ", which is not above 0 and at most 1", 0);
        }
        Optional<EdgeDepthTable> table = tables.current();
        if (table.isEmpty()) {
            return new Decision(null, null, tables.problem().orElse("no depth table is available"), 0);
        }
        long requestedMs = hints.getLong(DEPARTURE_HINT, 0) * 1000L;
        int limitCm = profile.getHints().getInt(LIMIT_HINT, -1);
        long windowStartMs = floorToStep(table.get(), requestedMs);
        return new Decision(
                new StickyClosure(table.get(), limitCm, windowStartMs, requestedMs, StickyClosure.DEFAULT_MARGIN_MS),
                new StickyClosure(table.get(), precautionCm(limitCm, fraction), windowStartMs, requestedMs,
                        StickyClosure.DEFAULT_MARGIN_MS),
                null, requestedMs);
    }

    /** Depths are whole cm, so a depth reaches fraction * limit exactly when it reaches the next whole cm up. */
    static int precautionCm(int limitCm, double fraction) {
        return (int) Math.ceil(fraction * limitCm);
    }

    /**
     * The latest forecast step at or before the departure. A step describes the roads from its time until the next step,
     * so the step that contains the departure is the state of the roads now, and the closure rule must count it. A
     * departure before the first step stays as it is.
     */
    static long floorToStep(EdgeDepthTable table, long departureMs) {
        long floored = departureMs;
        long best = Long.MIN_VALUE;
        for (Instant step : table.stepTimes()) {
            long ms = step.toEpochMilli();
            if (ms <= departureMs && ms > best) best = ms;
        }
        return best == Long.MIN_VALUE ? floored : best;
    }

    /** A trip is unknown when it ends after the last forecast step. Arrival exactly at the last step is known. */
    static boolean endsAfterLastStep(long departureMs, long routeMs, long lastStepMs) {
        return departureMs + routeMs > lastStepMs;
    }

    @Override
    public GHResponse route(GHRequest request) {
        decision = decide(request);
        GHResponse response = search(request);
        String kinds = null;
        if (decision.closure != null && !response.hasErrors()) {
            Planned planned = planOptions(request, response);
            response = planned.response;
            kinds = planned.kinds;
        }
        if (decision.requested()) annotate(response, kinds);
        if (request.getHints().has(INFO_HINT)) annotateInfo(response);
        return response;
    }

    private GHResponse search(GHRequest request) {
        legs.clear();
        return super.route(request);
    }

    private record Planned(GHResponse response, String kinds) {
    }

    /**
     * The limit route is in hand. When it enters no road at the precaution depth it is the answer. Otherwise a second
     * search runs under the precaution depth, and its route goes first when it exists.
     */
    private Planned planOptions(GHRequest request, GHResponse limitResponse) {
        boolean touches = false;
        for (Leg leg : legs) {
            if (!StickyChecker.findCrossings(leg.path(), leg.weighting(), decision.precaution).isEmpty()) touches = true;
        }
        if (!touches) return new Planned(limitResponse, KIND_RECOMMENDED);

        precautionSearches.incrementAndGet();
        Decision atLimit = decision;
        decision = new Decision(atLimit.precaution, null, null, atLimit.requestedDepartureMs);
        GHResponse precautionResponse;
        try {
            precautionResponse = search(request);
        } finally {
            decision = atLimit;
        }
        if (precautionResponse.hasErrors()) return new Planned(limitResponse, KIND_THROUGH_WATER);
        precautionResponse.add(limitResponse.getBest());
        return new Planned(precautionResponse, KIND_RECOMMENDED + "," + KIND_THROUGH_WATER);
    }

    /**
     * The graph hash and the run, for a client that reads the depth table itself (the departures endpoint of US-053). The
     * client compares the hash with the table's, so a stale table is refused. No search runs for this.
     */
    private void annotateInfo(GHResponse response) {
        tables.graphHash().ifPresent(hash -> response.getHints().putObject(GRAPH_HASH_HINT, hash));
        tables.current().ifPresent(table -> response.getHints().putObject(RUN_HINT, table.runName()));
    }

    private void annotate(GHResponse response, String kinds) {
        if (decision.closure == null) {
            response.getHints().putObject(STATUS_HINT, "fallback");
            response.getHints().putObject(REASON_HINT, decision.fallbackReason);
            return;
        }
        EdgeDepthTable table = decision.closure.table();
        long lastStepMs = table.stepTimes().get(table.stepTimes().size() - 1).toEpochMilli();
        boolean unknown = !response.hasErrors()
                && endsAfterLastStep(decision.requestedDepartureMs, response.getBest().getTime(), lastStepMs);
        response.getHints().putObject(STATUS_HINT, unknown ? "unknown" : "applied");
        response.getHints().putObject(RUN_HINT, table.runName());
        response.getHints().putObject(DEPARTURE_RESPONSE_HINT, decision.closure.windowStartEpochMs() / 1000);
        response.getHints().putObject(LAST_STEP_HINT, lastStepMs / 1000);
        response.getHints().putObject(LIMIT_CM_HINT, decision.closure.limitCm());
        response.getHints().putObject(PRECAUTION_CM_HINT, decision.precaution.limitCm());
        if (kinds != null) response.getHints().putObject(KINDS_HINT, kinds);
    }

    @Override
    protected Solver createSolver(GHRequest request) {
        if (decision.closure == null) return super.createSolver(request);
        return new TimeAwareFlexSolver(request, profilesByName, routerConfig, encodingManager, weightingFactory, graph,
                locationIndex, decision.closure, (path, weighting) -> legs.add(new Leg(path, weighting)));
    }

    /** The flexible solver with the time-aware search in place of the stock one. */
    static final class TimeAwareFlexSolver extends FlexSolver {
        private final StickyClosure closure;
        private final BiConsumer<Path, Weighting> onPath;

        TimeAwareFlexSolver(GHRequest request, Map<String, Profile> profilesByName, RouterConfig routerConfig,
                            EncodedValueLookup lookup, WeightingFactory weightingFactory, BaseGraph graph,
                            LocationIndex locationIndex, StickyClosure closure, BiConsumer<Path, Weighting> onPath) {
            super(request, profilesByName, routerConfig, lookup, weightingFactory, graph, locationIndex);
            this.closure = closure;
            this.onPath = onPath;
        }

        @Override
        protected FlexiblePathCalculator createPathCalculator(QueryGraph queryGraph) {
            return new FlexiblePathCalculator(queryGraph, (g, w, opts) -> {
                RoutingAlgorithm algo = new TimeAwareDijkstra(g, g.wrapWeighting(w), opts.getTraversalMode(), closure) {
                    @Override
                    public Path calcPath(int from, int to) {
                        Path path = super.calcPath(from, to);
                        if (path.isFound()) onPath.accept(path, weighting);
                        return path;
                    }
                };
                algo.setMaxVisitedNodes(opts.getMaxVisitedNodes());
                algo.setTimeoutMillis(opts.getTimeoutMillis());
                return algo;
            }, weighting, getAlgoOpts());
        }
    }
}
