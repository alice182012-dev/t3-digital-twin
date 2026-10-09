---
date_drafted: 2026-09-29
type: user-story
us_id: "US-049"
story_label: "R4"
epic: "[[EP-18-time-aware-routing-engine]]"
status: Done
priority: P0
estimate: L
sprint: 6
subsystem: floodmap-backend, floodmap-frontend
related: ["[[EP-09-time-aware-routing-engine]]", "[[SP-02-routing-engine-foundations|sprint-plan-2]]"]
title: "Build the Java module skeleton, the image, and the CI job"
---

# US-049 Build the Java module skeleton, the image, and the CI job

As an engineer, I want a module that builds against the pinned GraphHopper version and runs in our image, so
the engine work has a place to live and a way to be tested.
Given the pinned version and the revision from Story R1, when CI runs, then the module builds, the image
starts with the stock profiles unchanged, and a unit test reports whether a weighting that only raises
weights keeps LM's lower bounds valid. If the test fails, the story records that the search must run
without LM.
Priority: P0. Status: Done. Estimate: L. Sprint: 6. Dependencies: Story R1.
Evidence: ![[us-049-image-smoke-test-output.png|700]]
Details:
1. What: a Java module in `java/time-aware-routing/` that builds against the pinned GraphHopper commit `d7dc1b06` (`12.0-SNAPSHOT`), an image that starts from the stock image's digest and runs the module, and a GitHub Actions job. `TimeAwareGraphHopper` returns the stock weighting for now.
2. How: a shadow copy of `GraphHopperManaged` makes the web server build `TimeAwareGraphHopper`. The stock `graphhopper.sh` starts with `java -jar`, which ignores the classpath, so `run-time-aware.sh` starts `GraphHopperApplication` from a classpath with the module jar first. Tests first (9). CI builds the pinned commit, then runs `mvn test` (run 1, commit `ef5ef4c`, passed in 1 minute 34 seconds). `smoke-test.sh` builds the image on the server, starts it on port 8990 with its own graph cache, and compares routes.
3. Why: the engine work needs a place to live and a way to be tested, and the web server has no setting to pick another GraphHopper class. The module also had to answer whether landmark (LM) lower bounds survive a weighting that only raises weights.
4. Effect: LM stays valid for a raise-only weighting, so the search can use LM ([[BL-011-routing-not-time-aware|routing-not-time-aware]]). `LandmarkLowerBoundTest` covers 10 random graphs, with a control that lowers weights and does break the bounds. On the server the image logged `TimeAwareGraphHopper active`, and 12 routes (4 profiles, 3 pairs inside the model border) matched the live service in distance, time, and point count. `US-039` and `US-050` can build on the module. The module was compiled for Java 17 and ran on the stock image's JRE.
5. Limits: the pairs are few and the flood changes the routes from run to run, so the comparison shows the stock profiles unchanged for these pairs and not for all. The test container `graphhopper-time-aware` stays on the server until `smoke-test.sh cleanup` runs. The rendered evidence is built from output the user pasted.
