# time-aware-routing

Java module for the flood map's routing. It builds against GraphHopper commit `d7dc1b06` (version `12.0-SNAPSHOT`), the commit the server's stock image was built from.

What is here now (US-049, a skeleton):

- `TimeAwareGraphHopper` is a `GraphHopper` with its own `WeightingFactory`. Today it returns the stock weighting, so the stock profiles route as before.
- `com.graphhopper.http.GraphHopperManaged` is a shadow copy of GraphHopper's class of the same name. `GraphHopperBundle` calls `new GraphHopperManaged(...)`, and the web server has no setting to pick another class. The image puts this module's jar before `graphhopper-web.jar`, so the JVM loads this copy.
- `LandmarkLowerBoundTest` answers whether a weighting that only raises weights keeps the landmark (LM) lower bounds valid.

## Test

CI runs `mvn test` on every push to this folder. To run it yourself you need the pinned GraphHopper in `~/.m2`. The workflow shows how to build it, and so does the first stage of the `Dockerfile`.

```shell
docker build --target test java/time-aware-routing
```

## Run in the image

```shell
docker build -t graphhopper-time-aware java/time-aware-routing
```

The image starts from the stock image's digest and starts GraphHopper with `run-time-aware.sh`, which takes the same `-c` and `-o` options as the stock `graphhopper.sh`. On start the log has the line `TimeAwareGraphHopper active`. If that line is missing, the stock class loaded.

## Start the image beside the live service

`smoke-test.sh` builds the image on the server, starts it on port 8990 with its own graph cache, and compares routes with the live service on port 8989. Run it from the Mac in the repo root, and run `smoke-test.sh cleanup` after. The paths of the server's repo and OSM file are variables at the top of the script.
