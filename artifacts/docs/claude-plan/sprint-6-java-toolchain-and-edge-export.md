---
date: 2026-10-02
type: plan
branch: front-end-according-to-mock-up
status: active
tags: [plan, sprint-6, java, graphhopper, routing, us-049, us-039]
related: ["[[sprint-plan-2]]", "[[time-aware-routing-engine]]", "[[time-aware-routing-engine-stories]]", "[[edge-depth-table]]", "[[edge-depth-table-stories]]", "[[edge-depth-table-format]]", "[[graphhopper-backend]]", "[[routing-not-time-aware]]", "[[us-063-realistic-rain-replay-for-us-037-and-us-034]]"]
---

# Plan: Sprint 6, the Java module and the edge export

## Context

Sprint 6 of [[sprint-plan-2]] has two rows. `US-049` (Story R4, P0, L) builds a Java module against the pinned GraphHopper version, an image that runs it, and a CI job. `US-039` (Story E1, P0, M) exports every edge of the graph with its id, its geometry, and a graph hash. Nothing else in Sprints 7 and 8 can start without them, because the depth table, the Java reader, and the engine all read the module or the export.

The planned dates are 2026-10-26 to 2026-11-01. Sprints 3 to 5 started early, and Sprint 6 can start as soon as the three open rows of Sprint 5 are `Done`, which is after 16:00 +07 on 2026-10-04. The actual start goes in the timeline table when it happens. No blocker stops either row, and the three gates of the routing engine were cleared on 2026-10-02.

## What is known today

Everything here was read on 2026-10-02 with no change to the server.

1. The Mac has no Java, Maven, or Gradle. The repo has no `.github/workflows` and no other CI file. The CI job of `US-049` starts from nothing.
2. The repo is on GitHub (`alice182012-dev/t3-digital-twin`), so GitHub Actions is available.
3. The server runs the stock image `israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32`. `US-046` found that its jar comes from GraphHopper commit `d7dc1b069d2d091c7cfdc007d99d1765c82e618d`, version `12.0-SNAPSHOT`.
4. At that commit the root `pom.xml` targets Java 17 and lists the modules `core`, `web-bundle`, `web-api`, `web`, and others. A `12.0-SNAPSHOT` jar is not on Maven Central, so the module must get its dependency from a source build or from the image.
5. `GraphHopper.createWeightingFactory()` in `core` is `protected`, so a subclass can return its own `WeightingFactory`. `createWeighting` is `public final` and calls that hook. `Router` takes a `WeightingFactory` in its constructor.
6. `Weighting.calcMinWeightPerDistance()` is the value that the landmark (LM) lower bounds depend on. A weighting that only raises weights must leave that value valid. A unit test settles it ([[time-aware-routing-engine]], assumption 5).
7. The web server does not let a configuration pick the subclass. `GraphHopperManaged` calls `new GraphHopper()` itself, `GraphHopperBundle` creates the managed object inside its `run` method, and `GraphHopperApplication` is `final`. So the image needs our own application class and bundle that build a `TimeAwareGraphHopper`. This is the largest unknown of `US-049`, and the plan proves it first.

## Decisions the user makes

1. **A JDK on the Mac.** Installing a JDK 17 and Maven (`brew install openjdk@17 maven`) gives a test loop of seconds. Without it every Java test waits for a CI run after a push. Recommended: install. This changes the Mac, so it needs the user's yes.
2. **Where CI runs.** GitHub Actions in this repo is the proposal. The first run needs a push, and the user approves each push.
3. **When Sprint 6 starts.** Proposed: when `US-034`, `US-037`, and `US-063` are `Done`. The offline tasks marked "day 0" below can start earlier, which is the user's call.

Proposals that need no answer unless the user objects:

- The module lives in `java/time-aware-routing/`, with Maven and Java 17.
- The export is two files: `edges.csv` with `edge_id,wkt` (one LINESTRING in EPSG:4326 per edge, in id order) and `graph.json` with the hash, the edge count, the node count, and the GraphHopper commit.
- The graph hash is a SHA-256 over the node count, the edge count, and, for each edge in id order, its two node ids and its geometry. It does not read file timestamps, so two exports of one graph give one hash. The hash algorithm is the export's, as [[edge-depth-table-format]] leaves it.

## Steps for US-049

1. **Day 0, no JDK needed.** Clone GraphHopper at commit `d7dc1b06` into the scratch folder `marie-curie/` and read the parts the module touches: `GraphHopperBundle.run`, `GraphHopperManaged`, `GraphHopperApplication`, and the LM code. Write down the smallest application class and bundle that build a `TimeAwareGraphHopper`.
2. **Skeleton.** `java/time-aware-routing/pom.xml` (Java 17), the subclass `TimeAwareGraphHopper` that overrides `createWeightingFactory()` and returns a factory that delegates to `DefaultWeightingFactory`, and our application class and bundle. No behavior change yet.
3. **LM admissibility test.** On a small graph, build landmarks with the base weighting. Wrap the weighting in a decorator that only raises edge weights, run A* with the landmark heuristic, and compare every result with Dijkstra on the same wrapped weighting over random pairs. A pass means the lower bounds stay valid. A fail means the search must run without LM, and the story records that.
4. **Dependency source.** Build GraphHopper at the pinned commit in CI with `mvn -DskipTests install -pl core,web-api,web-bundle,web -am`, cache `~/.m2`, and compile the module against it. Proposed over extracting the jar from the image, because it needs no Docker in CI. The image check in step 6 uses the real image.
5. **CI job.** `.github/workflows/java-module.yml` sets up Java 17, builds the pinned GraphHopper, and runs `mvn test` for the module. The acceptance criterion reads "when CI runs", so a green run is part of the evidence.
6. **Image.** A `Dockerfile` that starts `FROM` the pinned digest, adds the module jar to the classpath, and starts our application class with the same `config.yml`. It builds and runs on the server, as a second container on another port. The live GraphHopper service keeps running and `compose.yml` does not change in this sprint. The check is that the stock profiles of the live service (`motorbike`, `car`, `truck`, and `foot`) give the same `POST /route` answers on the second container as on the live one, for a fixed set of requests. The pairs of `scripts/backend_soak/` can supply them.
7. **Evidence.** A screenshot of the green CI run, and rendered output from the server of the image starting and of the known-answer check. Record the LM test result in [[routing-not-time-aware]].

## Steps for US-039

1. **Command.** A main class `ExportEdges` in the module. It loads the graph cache read-only, walks every edge in id order, and writes `edges.csv` and `graph.json`.
2. **Tests first.** A tiny OSM file in the test resources, imported in a unit test. The test checks the row count against the graph's edge count, the geometry order, and that two exports of one graph give one hash and a changed graph gives another.
3. **Run on the server.** `docker run --rm` with the new image and the `graphhopper-graph-cache` volume mounted read-only. The expected row count is 67,833, the edge count recorded by `US-046` in [[routing-not-time-aware]].
4. **Evidence.** Rendered output of the export on the server: the row count, the first rows, the hash, and the two exports giving the same hash. Update [[edge-depth-table-format]] with the hash algorithm, and [[graphhopper-backend]] with the export.

## Order and what runs where

| Task | Needs a JDK | Needs the server | Needs a push |
| ---- | ----------- | ---------------- | ------------ |
| Day 0 reading of the pinned source | No | No | No |
| Skeleton and LM test | Yes, or CI | No | Only for CI |
| CI job | No (runs on GitHub) | No | Yes |
| Image build and stock-profile check | No | Yes | Yes, to pull the files |
| Export tests | Yes, or CI | No | Only for CI |
| Export run and evidence | No | Yes | Yes |

`US-039` starts after the module builds, because the export is a class in it.

## Risks

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Our application class cannot replace the stock one without copying much of `GraphHopperBundle` | The module carries a copy of about 300 lines that must follow the pinned version | The version is pinned by digest, so the copy never drifts. Step 1 measures the size before the skeleton starts. If it is too large, fall back to Tier A-prime and revise [[sprint-plan-2]] |
| The LM test fails | The search runs without LM and latency rises | The story records it. `US-055` measures the real latency against the factor of 2 |
| A source build of the pinned commit is slow or fails in CI | CI takes minutes per run, or never goes green | Cache `~/.m2`. If the build fails, extract the jars from the pinned image instead |
| The second container on the server loads the same graph cache | Memory pressure on the server | The graph has 67,833 edges and is small. Mount the cache read-only and stop the container after the check |
| `US-049` is sized L and the Java work is new to the project | The sprint slips | `US-039` is the only row behind it. Slips move to Sprint 7, which holds the depth table and has its own dependency on `US-039` |

## Evidence and Definition of done

Each row follows the Definition of done in [[sprint-plan-2]]: the acceptance criteria pass where they say, tests pass, the concept page is updated with `last_updated` bumped, and rendered output or a screenshot plus numbered details are in the epic file and the sprint plan. `US-049` needs a new concept page or a section in [[graphhopper-backend]] for the module and the image.

## Status history

- **2026-10-02, active.** Planned at the user's request, with no server change. The plan found that the stock web server cannot be told to use a `GraphHopper` subclass, so step 1 of `US-049` measures the size of our own application class before anything else is built.
