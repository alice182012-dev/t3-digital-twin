/*
 *  Licensed to GraphHopper GmbH under one or more contributor
 *  license agreements. See the NOTICE file distributed with this work for
 *  additional information regarding copyright ownership.
 *
 *  GraphHopper GmbH licenses this file to you under the Apache License,
 *  Version 2.0 (the "License"); you may not use this file except in
 *  compliance with the License. You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package com.graphhopper.http;

import com.graphhopper.GraphHopper;
import com.graphhopper.GraphHopperConfig;
import com.graphhopper.timeaware.TimeAwareGraphHopper;
import io.dropwizard.lifecycle.Managed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Shadow copy of GraphHopper's {@code com.graphhopper.http.GraphHopperManaged} at commit d7dc1b06.
 * <p>
 * Changed from the original: it creates a {@link TimeAwareGraphHopper} instead of a {@code GraphHopper},
 * it drops the GTFS branch (the flood map has no public transport), and it logs which class it built.
 * <p>
 * {@code GraphHopperBundle} calls {@code new GraphHopperManaged(...)} and the web server has no setting to pick
 * another class. The image puts this module's jar before {@code graphhopper-web.jar} on the classpath, so the
 * JVM loads this copy instead of the original.
 */
public class GraphHopperManaged implements Managed {

    private final static Logger logger = LoggerFactory.getLogger(GraphHopperManaged.class);
    private final GraphHopper graphHopper;

    public GraphHopperManaged(GraphHopperConfig configuration) {
        if (configuration.has("gtfs.file")) {
            throw new IllegalArgumentException("gtfs.file is not supported by the time-aware GraphHopperManaged");
        }
        graphHopper = new TimeAwareGraphHopper();
        graphHopper.init(configuration);
    }

    @Override
    public void start() {
        graphHopper.importOrLoad();
        logger.info("TimeAwareGraphHopper active: {}", graphHopper.getClass().getName());
        logger.info("loaded graph at:{}, data_reader_file:{}, encoded values:{}, {} bytes for edge flags, {}",
                graphHopper.getGraphHopperLocation(), graphHopper.getOSMFile(),
                graphHopper.getEncodingManager().toEncodedValuesAsString(),
                graphHopper.getEncodingManager().getBytesForFlags(),
                graphHopper.getBaseGraph().toDetailsString());
    }

    public GraphHopper getGraphHopper() {
        return graphHopper;
    }

    @Override
    public void stop() {
        graphHopper.close();
    }
}
