(function exposePointDepth(root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.FloodPointDepth = api;
})(typeof globalThis !== "undefined" ? globalThis : window, () => {
  const EPSILON = 1e-10;

  function depthMeters(properties = {}) {
    const meters = Number(properties.depth_m);
    if (Number.isFinite(meters)) return meters;
    const centimeters = Number(properties.depth_cm);
    return Number.isFinite(centimeters) ? centimeters / 100 : 0;
  }

  function pointOnSegment(point, start, end) {
    const [x, y] = point;
    const [x1, y1] = start;
    const [x2, y2] = end;
    const cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1);
    if (Math.abs(cross) > EPSILON) return false;
    return (
      x >= Math.min(x1, x2) - EPSILON &&
      x <= Math.max(x1, x2) + EPSILON &&
      y >= Math.min(y1, y2) - EPSILON &&
      y <= Math.max(y1, y2) + EPSILON
    );
  }

  function pointInRing(point, ring) {
    if (!Array.isArray(ring) || ring.length < 3) return false;
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
      const currentPoint = ring[index];
      const previousPoint = ring[previous];
      if (pointOnSegment(point, previousPoint, currentPoint)) return true;
      const [x, y] = point;
      const [xi, yi] = currentPoint;
      const [xj, yj] = previousPoint;
      const crosses = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
      if (crosses) inside = !inside;
    }
    return inside;
  }

  function pointInPolygon(point, rings) {
    if (!Array.isArray(rings) || !pointInRing(point, rings[0])) return false;
    return !rings.slice(1).some((hole) => pointInRing(point, hole));
  }

  function geometryContainsPoint(geometry, point) {
    if (!geometry || !Array.isArray(geometry.coordinates)) return false;
    if (geometry.type === "Polygon") return pointInPolygon(point, geometry.coordinates);
    if (geometry.type === "MultiPolygon") {
      return geometry.coordinates.some((polygon) => pointInPolygon(point, polygon));
    }
    return false;
  }

  function pointDepthAt(latlng, geojson) {
    const point = [Number(latlng.lng), Number(latlng.lat)];
    const features = Array.isArray(geojson?.features) ? geojson.features : [];
    let match = null;
    features.forEach((feature) => {
      if (!geometryContainsPoint(feature?.geometry, point)) return;
      const properties = feature.properties || {};
      const candidateDepth = Math.max(0, depthMeters(properties));
      if (!match || candidateDepth > match.depthM) {
        match = {
          depthM: candidateDepth,
          depthCm: candidateDepth * 100,
          flooded: candidateDepth > 0,
          roadName: properties.road_name || "",
          time: properties.time || "",
        };
      }
    });
    return match || {
      depthM: 0,
      depthCm: 0,
      flooded: false,
      roadName: "",
      time: "",
    };
  }

  return {
    geometryContainsPoint,
    pointDepthAt,
    pointInRing,
  };
});
