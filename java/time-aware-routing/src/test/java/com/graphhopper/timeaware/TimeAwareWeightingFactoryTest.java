package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertSame;

import com.graphhopper.config.Profile;
import com.graphhopper.routing.WeightingFactory;
import com.graphhopper.routing.weighting.Weighting;
import com.graphhopper.util.PMap;
import java.lang.reflect.Proxy;
import org.junit.jupiter.api.Test;

class TimeAwareWeightingFactoryTest {

    @Test
    void returnsTheStockWeightingUnchanged() {
        Weighting stock = (Weighting) Proxy.newProxyInstance(
                Weighting.class.getClassLoader(), new Class<?>[]{Weighting.class}, (proxy, method, args) -> null);
        Profile profile = new Profile("motorbike");
        PMap hints = new PMap();
        WeightingFactory stockFactory = (p, h, disableTurnCosts) -> {
            assertSame(profile, p);
            assertSame(hints, h);
            return stock;
        };

        Weighting result = new TimeAwareWeightingFactory(stockFactory).createWeighting(profile, hints, false);

        assertSame(stock, result);
    }
}
