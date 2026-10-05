package com.graphhopper.timeaware;

import com.graphhopper.GraphHopper;
import com.graphhopper.config.Profile;
import com.graphhopper.routing.DefaultWeightingFactory;
import com.graphhopper.routing.Router;
import com.graphhopper.routing.RouterConfig;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.lm.LandmarkStorage;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.RoutingCHGraph;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.util.details.PathDetailsBuilderFactory;
import com.graphhopper.util.TranslationMap;
import java.util.Map;
import java.util.function.Supplier;

/**
 * GraphHopper with its own weighting factory and its own router. The web server builds this class (through the shadowed
 * GraphHopperManaged), so it is where the time-aware search is hooked in (US-050).
 */
public class TimeAwareGraphHopper extends GraphHopper {

    private volatile Supplier<EdgeDepthTable> tables = () -> null;

    /** Where the router gets the depth table of a time-aware request. US-052 sets it to follow the `latest` pointer. */
    public TimeAwareGraphHopper setTableSupplier(Supplier<EdgeDepthTable> tables) {
        this.tables = tables;
        return this;
    }

    @Override
    protected Router doCreateRouter(BaseGraph baseGraph, EncodingManager encodingManager, LocationIndex locationIndex,
                                    Map<String, Profile> profilesByName, PathDetailsBuilderFactory pathBuilderFactory,
                                    TranslationMap trMap, RouterConfig routerConfig, WeightingFactory weightingFactory,
                                    Map<String, RoutingCHGraph> chGraphs, Map<String, LandmarkStorage> landmarks) {
        return new TimeAwareRouter(baseGraph, encodingManager, locationIndex, profilesByName, pathBuilderFactory, trMap,
                routerConfig, weightingFactory, chGraphs, landmarks, tables);
    }

    @Override
    protected WeightingFactory createWeightingFactory() {
        return new TimeAwareWeightingFactory(new DefaultWeightingFactory(getBaseGraph(), getEncodingManager()));
    }
}
