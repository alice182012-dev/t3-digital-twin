const assert = require("node:assert/strict");
const test = require("node:test");

const { geometryContainsPoint, pointDepthAt, pointInRing } = require("../frontend/point_depth.js");

const square = [
  [105.0, 21.0],
  [105.1, 21.0],
  [105.1, 21.1],
  [105.0, 21.1],
  [105.0, 21.0],
];

test("point-in-ring includes interior and boundary points", () => {
  assert.equal(pointInRing([105.05, 21.05], square), true);
  assert.equal(pointInRing([105.0, 21.05], square), true);
  assert.equal(pointInRing([105.2, 21.05], square), false);
});

test("polygon holes and multipolygons are respected", () => {
  const hole = [
    [105.04, 21.04],
    [105.06, 21.04],
    [105.06, 21.06],
    [105.04, 21.06],
    [105.04, 21.04],
  ];
  assert.equal(
    geometryContainsPoint({ type: "Polygon", coordinates: [square, hole] }, [105.05, 21.05]),
    false,
  );
  assert.equal(
    geometryContainsPoint({ type: "MultiPolygon", coordinates: [[[...square]]] }, [105.02, 21.02]),
    true,
  );
});

test("point depth returns the deepest overlapping flood polygon", () => {
  const geojson = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [square] },
        properties: { depth_m: 0.18, road_name: "Road A", time: "2026-07-23T20:00:00" },
      },
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [square] },
        properties: { depth_cm: 42, road_name: "Road B", time: "2026-07-23T20:00:00" },
      },
    ],
  };
  assert.deepEqual(pointDepthAt({ lat: 21.05, lng: 105.05 }, geojson), {
    depthM: 0.42,
    depthCm: 42,
    flooded: true,
    roadName: "Road B",
    time: "2026-07-23T20:00:00",
  });
  assert.deepEqual(pointDepthAt({ lat: 22, lng: 106 }, geojson), {
    depthM: 0,
    depthCm: 0,
    flooded: false,
    roadName: "",
    time: "",
  });
});
