package com.graphhopper.timeaware;

import com.graphhopper.GHRequest;
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
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.RoutingCHGraph;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.util.PMap;
import com.graphhopper.util.details.PathDetailsBuilderFactory;
import com.graphhopper.util.TranslationMap;
import java.util.Map;
import java.util.function.Supplier;

/**
 * The router of US-050. A request that carries the hint {@value #DEPARTURE_HINT} (epoch seconds), on a profile that has
 * the hint {@value #LIMIT_HINT} (the vehicle's depth limit in cm), is routed with {@link TimeAwareDijkstra} over the
 * current edge depth table. Every other request goes the stock way, so nothing changes for it. The time-aware search
 * cannot use landmarks or contraction hierarchies, because their bounds and shortcuts do not know the time, so such a
 * request always uses the flexible solver.
 * <p>
 * The server flag, the request clock, and the fallback response flag are US-052.
 */
public class TimeAwareRouter extends Router {

    public static final String DEPARTURE_HINT = "td_departure";
    public static final String LIMIT_HINT = "td_limit_cm";

    private final Supplier<EdgeDepthTable> tables;

    public TimeAwareRouter(BaseGraph graph, EncodingManager encodingManager, LocationIndex locationIndex,
                           Map<String, Profile> profilesByName, PathDetailsBuilderFactory pathDetailsBuilderFactory,
                           TranslationMap translationMap, RouterConfig routerConfig, WeightingFactory weightingFactory,
                           Map<String, RoutingCHGraph> chGraphs, Map<String, LandmarkStorage> landmarks,
                           Supplier<EdgeDepthTable> tables) {
        super(graph, encodingManager, locationIndex, profilesByName, pathDetailsBuilderFactory, translationMap, routerConfig,
                weightingFactory, chGraphs, landmarks);
        this.tables = tables;
    }

    /** The closure rule of a request, or null when the request is not time-aware or no table is available. */
    StickyClosure closureFor(GHRequest request) {
        PMap hints = request.getHints();
        if (!hints.has(DEPARTURE_HINT)) return null;
        Profile profile = profilesByName.get(request.getProfile());
        if (profile == null || !profile.getHints().has(LIMIT_HINT)) return null;
        EdgeDepthTable table = tables.get();
        if (table == null) return null;
        return new StickyClosure(table, profile.getHints().getInt(LIMIT_HINT, -1), hints.getLong(DEPARTURE_HINT, 0) * 1000L,
                StickyClosure.DEFAULT_MARGIN_MS);
    }

    @Override
    protected Solver createSolver(GHRequest request) {
        StickyClosure closure = closureFor(request);
        if (closure == null) return super.createSolver(request);
        return new TimeAwareFlexSolver(request, profilesByName, routerConfig, encodingManager, weightingFactory, graph,
                locationIndex, closure);
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
