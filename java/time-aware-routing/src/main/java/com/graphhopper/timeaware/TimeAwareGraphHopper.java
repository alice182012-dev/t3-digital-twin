package com.graphhopper.timeaware;

import com.graphhopper.GraphHopper;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.config.Profile;
import com.graphhopper.routing.DefaultWeightingFactory;
import com.graphhopper.routing.Router;
import com.graphhopper.routing.RouterConfig;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.lm.LandmarkStorage;
import com.graphhopper.routing.util.EncodingManager;
import com.graphhopper.storage.BaseGraph;
import com.graphhopper.storage.RoutingCHGraph;
import com.graphhopper.storage.index.LocationIndex;
import com.graphhopper.util.TranslationMap;
import com.graphhopper.util.details.PathDetailsBuilderFactory;
import java.nio.file.Path;
import java.util.Map;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * GraphHopper with its own weighting factory and its own router. The web server builds this class (through the shadowed
 * GraphHopperManaged), so it is where the time-aware search is hooked in (US-050).
 * <p>
 * The config key {@value #TABLE_DIR_KEY} names the folder of edge depth tables (US-052). After the graph is loaded, this
 * class hashes it and follows the folder's `latest` pointer, refusing a table of another graph. With no folder the
 * time-aware requests fall back, and the response says why.
 */
public class TimeAwareGraphHopper extends GraphHopper {

    public static final String TABLE_DIR_KEY = "time_aware.table_dir";
    private static final Logger logger = LoggerFactory.getLogger(TimeAwareGraphHopper.class);

    private static final TableProvider NO_FOLDER = new TableProvider() {
        @Override
        public Optional<EdgeDepthTable> current() {
            return Optional.empty();
        }

        @Override
        public Optional<String> problem() {
            return Optional.of("no table folder is configured (" + TABLE_DIR_KEY + ")");
        }
    };

    private volatile TableProvider tables = NO_FOLDER;
    private String tableDir = "";
    private LatestTableSource source;

    @Override
    public GraphHopper init(GraphHopperConfig ghConfig) {
        tableDir = ghConfig.getString(TABLE_DIR_KEY, "");
        return super.init(ghConfig);
    }

    /** Where the router gets the depth table of a time-aware request. Tests set it. `importOrLoad` sets it from the config. */
    public TimeAwareGraphHopper setTableProvider(TableProvider tables) {
        this.tables = tables;
        return this;
    }

    @Override
    public GraphHopper importOrLoad() {
        GraphHopper loaded = super.importOrLoad();
        if (!tableDir.isBlank()) {
            String hash = GraphHash.compute(getBaseGraph());
            source = new LatestTableSource(Path.of(tableDir), hash);
            source.start();
            tables = source;
            logger.info("time-aware routing: following {} for graph hash {}", tableDir, hash);
        }
        return loaded;
    }

    @Override
    public void close() {
        if (source != null) source.close();
        super.close();
    }

    @Override
    protected WeightingFactory createWeightingFactory() {
        return new TimeAwareWeightingFactory(new DefaultWeightingFactory(getBaseGraph(), getEncodingManager()));
    }

    @Override
    protected Router doCreateRouter(BaseGraph baseGraph, EncodingManager encodingManager, LocationIndex locationIndex,
                                    Map<String, Profile> profilesByName, PathDetailsBuilderFactory pathBuilderFactory,
                                    TranslationMap trMap, RouterConfig routerConfig, WeightingFactory weightingFactory,
                                    Map<String, RoutingCHGraph> chGraphs, Map<String, LandmarkStorage> landmarks) {
        return new TimeAwareRouter(baseGraph, encodingManager, locationIndex, profilesByName, pathBuilderFactory, trMap,
                routerConfig, weightingFactory, chGraphs, landmarks, tables);
    }
}
