package com.graphhopper.timeaware;

import com.graphhopper.GraphHopper;
import com.graphhopper.routing.DefaultWeightingFactory;
import com.graphhopper.routing.WeightingFactory;

/** GraphHopper with its own weighting factory. It is the only hook the web server lets us change. */
public class TimeAwareGraphHopper extends GraphHopper {

    @Override
    protected WeightingFactory createWeightingFactory() {
        return new TimeAwareWeightingFactory(new DefaultWeightingFactory(getBaseGraph(), getEncodingManager()));
    }
}
