# syntax=docker/dockerfile:1
#
# The module, tested against the pinned GraphHopper commit, then laid over the stock image.
#
#   docker build --target test .      builds the pinned GraphHopper and runs the tests
#   docker build -t graphhopper-time-aware .
#
# The stock image is the one in compose.yml. Keep both digests the same.
ARG STOCK_IMAGE=israelhikingmap/graphhopper@sha256:3e79eb33862028cfc58f9d6c162630b68638d6aad790b5a698c854dbbaa7fe32

# GraphHopper 12.0-SNAPSHOT is not on Maven Central. Build the commit the stock image's jar came from.
FROM maven:3-eclipse-temurin-17 AS graphhopper
ARG GRAPHHOPPER_COMMIT=d7dc1b069d2d091c7cfdc007d99d1765c82e618d
RUN git init /graphhopper-src \
    && git -C /graphhopper-src fetch --depth 1 https://github.com/graphhopper/graphhopper.git ${GRAPHHOPPER_COMMIT} \
    && git -C /graphhopper-src checkout FETCH_HEAD
RUN cd /graphhopper-src \
    && mvn -B -q -DskipTests -Dmaven.javadoc.skip=true install -pl core,web-api,web-bundle,web -am \
    && rm -rf /graphhopper-src

FROM graphhopper AS test
WORKDIR /module
COPY pom.xml .
COPY src src
RUN mvn -B test

FROM test AS package
RUN mvn -B -DskipTests package

FROM ${STOCK_IMAGE}
COPY --from=package /module/target/time-aware-routing.jar /opt/time-aware/time-aware-routing.jar
COPY run-time-aware.sh /opt/time-aware/run-time-aware.sh
ENTRYPOINT ["/opt/time-aware/run-time-aware.sh"]
