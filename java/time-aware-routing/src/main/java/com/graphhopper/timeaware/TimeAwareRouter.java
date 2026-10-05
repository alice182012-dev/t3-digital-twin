package com.graphhopper.timeaware;

import com.graphhopper.GHRequest;
import com.graphhopper.GHResponse;
import com.graphhopper.config.Profile;
import com.graphhopper.routing.FlexiblePathCalculator;
import com.graphhopper.routing.RoutingAlgorithm;
import com.graphhopper.routing.Router;
import com.graphhopper.routing.RouterConfig;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.ev.EncodedValueLookup;
import com.graphhopper.routing.lm.LandmarkStorage;
import com.graphhopper.routing.querygraph.QueryGraph;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.RoutingCHGraph;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.util.PMap;
import com.graphhopper.util.TranslationMap;
import com.graphhopper.util.details.PathDetailsBuilderFactory;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * The router of US-050 and US-052. A request that carries the hint {@value #DEPARTURE_HINT} (epoch seconds) is
 * time-aware. It is routed with {@link TimeAwareDijkstra} over the current edge depth table when a table is available and
 * the profile has the hint {@value #LIMIT_HINT} (the vehicle's depth limit in cm). Otherwise it goes the stock way and
 * the response says `fallback` and why. A request without the departure hint is untouched and its response is unchanged.
 * <p>
 * GraphHopper makes a new router for every request, so the decision is made once and held in a field. That pins one
 * table for all the legs of the request. The response hints are {@value #STATUS_HINT} (`applied`, `unknown`, or
 * `fallback`), {@value #RUN_HINT}, {@value #DEPARTURE_RESPONSE_HINT}, {@value #LAST_STEP_HINT} (epoch seconds), and
 * {@value #REASON_HINT} for a fallback. A time-aware search cannot use landmarks or contraction hierarchies, because
 * their bounds and shortcuts do not know the time, so it always uses the flexible solver.
 */
public class TimeAwareRouter extends Router {

    public static final String DEPARTURE_HINT = "td_departure";
    public static final String LIMIT_HINT = "td_limit_cm";
    public static final String STATUS_HINT = "td.status";
    public static final String RUN_HINT = "td.run";
    public static final String DEPARTURE_RESPONSE_HINT = "td.departure";
    public static final String LAST_STEP_HINT = "td.last_step";
    public static final String REASON_HINT = "td.reason";

    private final TableProvider tables;
    private Decision decision = Decision.NOT_REQUESTED;

    /** What this request gets. Not requested: no hints. Fallback: the stock search, with a reason. Applied: the closure. */
    record Decision(StickyClosure closure, String fallbackReason, long requestedDepartureMs) {
        static final Decision NOT_REQUESTED = new Decision(null, null, 0);

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
            return new Decision(null, "the profile '" + request.getProfile() + "' has no depth limit (" + LIMIT_HINT + ")", 0);
        }
        Optional<EdgeDepthTable> table = tables.current();
        if (table.isEmpty()) {
            return new Decision(null, tables.problem().orElse("no depth table is available"), 0);
        }
        long requestedMs = hints.getLong(DEPARTURE_HINT, 0) * 1000L;
        long departureMs = floorToStep(table.get(), requestedMs);
        return new Decision(new StickyClosure(table.get(), profile.getHints().getInt(LIMIT_HINT, -1), departureMs,
                StickyClosure.DEFAULT_MARGIN_MS), null, requestedMs);
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
        GHResponse response = super.route(request);
        if (decision.requested()) annotate(response);
        return response;
    }

    private void annotate(GHResponse response) {
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
        response.getHints().putObject(DEPARTURE_RESPONSE_HINT, decision.closure.departureEpochMs() / 1000);
        response.getHints().putObject(LAST_STEP_HINT, lastStepMs / 1000);
    }

    @Override
    protected Solver createSolver(GHRequest request) {
        if (decision.closure == null) return super.createSolver(request);
        return new TimeAwareFlexSolver(request, profilesByName, routerConfig, encodingManager, weightingFactory, graph,
                locationIndex, decision.closure);
    }

    /** The flexible solver with the time-aware search in place of the stock one. */
    static final class TimeAwareFlexSolver extends FlexSolver {
        private final StickyClosure closure;

        TimeAwareFlexSolver(GHRequest request, Map<String, Profile> profilesByName, RouterConfig routerConfig,
                            EncodedValueLookup lookup, WeightingFactory weightingFactory, BaseGraph graph,
                            LocationIndex locationIndex, StickyClosure closure) {
            super(request, profilesByName, routerConfig, lookup, weightingFactory, graph, locationIndex);
            this.closure = closure;
        }

        @Override
        protected FlexiblePathCalculator createPathCalculator(QueryGraph queryGraph) {
            return new FlexiblePathCalculator(queryGraph, (g, w, opts) -> {
                RoutingAlgorithm algo = new TimeAwareDijkstra(g, g.wrapWeighting(w), opts.getTraversalMode(), closure);
                algo.setMaxVisitedNodes(opts.getMaxVisitedNodes());
                algo.setTimeoutMillis(opts.getTimeoutMillis());
                return algo;
            }, weighting, getAlgoOpts());
        }
    }
}
