package com.graphhopper.timeaware;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

/** The report that scenario-check.sh runs on the server prints one line per run and passes when all 16 match. */
class ScenarioReportTest {

    @Test
    void allSixteenRunsMatchTheStickyColumn() throws Exception {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();

        int code = ScenarioReport.run(new PrintStream(buffer, true, StandardCharsets.UTF_8));

        String out = buffer.toString(StandardCharsets.UTF_8);
        assertEquals(0, code, out);
        assertTrue(out.contains("PASS: 16 of 16"), out);
        assertEquals(1 + 16 + 1, out.strip().split("\n").length, out);
    }

    @Test
    void theBlockedScenariosCrossTheClosedRoadOnThePlainRoute() throws Exception {
        for (ScenarioReport.Scenario s : ScenarioReport.SCENARIOS) {
            ScenarioReport.Outcome o = ScenarioReport.outcome(s, 20, true);
            assertEquals(0, o.crossings(), s.name());
            assertEquals(s.blocked(), o.plainRouteCrossings() > 0, s.name());
        }
    }
}
