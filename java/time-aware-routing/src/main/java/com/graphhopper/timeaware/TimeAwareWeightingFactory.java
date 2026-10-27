package com.graphhopper.timeaware;

import com.graphhopper.config.Profile;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.util.PMap;

/**
 * Builds the weighting of a profile. For now it returns what the stock factory returns, so the stock
 * profiles route as before. The time-aware wrapper (US-050) is added here.
 */
public class TimeAwareWeightingFactory implements WeightingFactory {

    private final WeightingFactory delegate;

    public TimeAwareWeightingFactory(WeightingFactory delegate) {
        this.delegate = delegate;
    }

    @Override
    public Weighting createWeighting(Profile profile, PMap hints, boolean disableTurnCosts) {
        return delegate.createWeighting(profile, hints, disableTurnCosts);
    }
}
