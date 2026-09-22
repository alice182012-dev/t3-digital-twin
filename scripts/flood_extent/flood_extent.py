#!/usr/bin/env python3
"""Build flood-extent vector tiles from 3Di depth rasters.

This is the engine behind the map's flood layer. For one timestep it reclassifies the depth into
band codes, closes the small gaps between wet cells, polygonizes, dissolves by band, deletes small
holes and specks, and cuts vector tiles. It needs GDAL 3.3 or later (with the Python bindings) and
GRASS GIS 8 on the command line.

Every intermediate file (the GRASS project, the rasters, the GeoPackages) lives in a temporary
folder that is deleted when the build ends, whether it succeeds or fails. The tile folder is the
only thing left on disk, and it is swapped in only once it is complete.

Library use:

    build_flood_extent(depth_tif, tiles_dir)              # one timestep, straight to a local folder

For every depth_*.tif of one run, published to MinIO and the flood_extent_polygon audit table
(what the Airflow DAG actually does), see publish.py's publish_run — the worker and the frontend
run on separate hosts in production, so a local tiles_root can't reach the frontend on its own.

Command line, for one timestep:

    python3 flood_extent.py DEPTH_TIF TILES_DIR [--band 1] [--radius 8] [--min-area 20]
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from osgeo import gdal, ogr, osr

ogr.UseExceptions()

BAND_TABLE = [(0.05, 0), (0.1, 10), (0.2, 20), (0.3, 30), (0.4, 40), (0.5, 50), (0.6, 60)]
TOP_CODE = 600
DEPTH_NODATA = -9999
EXPECTED_CODES = {code for _, code in BAND_TABLE if code > 0} | {TOP_CODE}

DEPTH_FILE = re.compile(r"^depth_(\d{8})_(\d{6})\.tif$")
RUN_DIR = re.compile(r"^\d{8}T\d{6}$")


class FloodExtentError(RuntimeError):
    pass


@dataclass(frozen=True)
class FloodExtentResult:
    tile_count: int
    area_by_band: dict = field(default_factory=dict)  # band code -> m2
    polygons_4326: dict = field(default_factory=dict)  # band code -> WKB geometry, reprojected

    @property
    def is_empty(self):
        return not self.area_by_band


class Pipeline:
    def __init__(self, depth_tif, tiles_dir, band, radius, min_area, min_zoom, max_zoom,
                 tmp_root=None, verbose=False):
        self.depth_tif = Path(depth_tif)
        self.tiles_dir = Path(tiles_dir)
        self.band = band
        self.radius = radius
        self.min_area = min_area
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.tmp_root = tmp_root
        self.verbose = verbose

    def bind(self, work):
        self.work = Path(work)
        self.project = self.work / "grass_project"
        self.depth_bands = self.work / "re-classify_depth.tif"
        self.final_tif = self.work / "final.tif"
        self.poly = self.work / "poly.gpkg"
        self.dissolved = self.work / "dissolved.gpkg"
        self.cleaned = self.work / "cleaned.gpkg"
        self.tiles = self.work / "mvt"

    def say(self, message):
        if self.verbose:
            print(message, flush=True)

    @staticmethod
    def run(*args):
        result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
        if result.returncode != 0:
            command = " ".join(str(a) for a in args[:2])
            raise FloodExtentError(f"{command} failed ({result.returncode}): {result.stderr.strip()[-2000:]}")
        return result.stdout

    def grass(self, module, *args):
        self.run("grass", self.project / "PERMANENT", "--exec", module, *args, "--overwrite", "--quiet")

    def band_counts(self, raster):
        if self.verbose:
            print(self.run("grass", self.project / "PERMANENT", "--exec", "r.stats", "-c", "-n",
                           f"input={raster}"), flush=True)

    def reclassify_depth(self):
        expression = str(TOP_CODE)
        for limit, code in reversed(BAND_TABLE):
            expression = f"numpy.where(A<={limit},{code},{expression})"
        self.run("gdal_calc.py", "-A", self.depth_tif, f"--A_band={self.band}",
                 f"--outfile={self.depth_bands}", f"--calc={expression}",
                 f"--NoDataValue={DEPTH_NODATA}", "--type=Int16", "--co=COMPRESS=DEFLATE",
                 "--overwrite", "--quiet")

    def has_wet_cells(self):
        dataset = gdal.Open(str(self.depth_bands))
        if dataset is None:
            raise FloodExtentError(f"Cannot read the reclassified depth raster of {self.depth_tif}")
        data = dataset.GetRasterBand(1).ReadAsArray()
        return bool((data > 0).any())

    def close_bands(self):
        self.run("grass", "-c", self.depth_bands, self.project, "--exec", "r.in.gdal",
                 f"input={self.depth_bands}", "output=depth_bands", "-o", "--quiet")
        self.grass("g.region", "raster=depth_bands")
        self.band_counts("depth_bands")
        self.grass("r.mapcalc", "expression=wet_bands = if(depth_bands > 0, int(depth_bands), null())")
        self.grass("r.grow.distance", "input=wet_bands", "distance=dist1", "value=val1")
        self.grass("r.mapcalc", "expression=dilated = if(!isnull(wet_bands), wet_bands, "
                   f"if(dist1 <= {self.radius}, int(val1), null()))")
        self.grass("r.mapcalc", "expression=inv = if(isnull(dilated), 1, null())")
        self.grass("r.grow.distance", "input=inv", "distance=dist2")
        self.grass("r.mapcalc", f"expression=closed = if(dist2 <= {self.radius}, null(), dilated)")
        self.grass("r.mapcalc",
                   "expression=final = if(!isnull(closed), closed, if(depth_bands == 0, 0, null()))")
        self.band_counts("final")
        self.run("grass", self.project / "PERMANENT", "--exec", "r.out.gdal", "input=final",
                 f"output={self.final_tif}", "format=GTiff", "type=Int16", "nodata=-9999",
                 "createopt=COMPRESS=LZW", "--overwrite", "--quiet")

    def polygonize(self):
        self.run("gdal_polygonize.py", "-q", "-8", self.final_tif, "-f", "GPKG", self.poly, "poly", "DN")

    def dissolve(self):
        self.run("ogr2ogr", "-q", "-f", "GPKG", self.dissolved, self.poly, "-dialect", "SQLite",
                 "-sql", "SELECT DN, ST_Union(geom) AS geom FROM poly WHERE DN > 0 GROUP BY DN",
                 "-nln", "dissolved")

    def clean(self):
        src_ds = ogr.Open(str(self.dissolved))
        layer = src_ds.GetLayer()
        definition = layer.GetLayerDefn()
        dst_ds = ogr.GetDriverByName("GPKG").CreateDataSource(str(self.cleaned))
        out = dst_ds.CreateLayer("cleaned", srs=layer.GetSpatialRef(), geom_type=ogr.wkbMultiPolygon)
        for i in range(definition.GetFieldCount()):
            out.CreateField(definition.GetFieldDefn(i))
        for feature in layer:
            geom = clean_multipolygon(
                ogr.ForceToMultiPolygon(feature.GetGeometryRef().Clone()), self.min_area
            )
            if geom.IsEmpty():
                continue
            cleaned = ogr.Feature(out.GetLayerDefn())
            cleaned.SetFrom(feature)
            cleaned.SetGeometry(geom)
            out.CreateFeature(cleaned)

    def cleaned_feature_count(self):
        dataset = ogr.Open(str(self.cleaned))  # keep the dataset alive while its layer is read
        return dataset.GetLayer().GetFeatureCount()

    def cut_tiles(self):
        self.run("ogr2ogr", "-q", "-f", "MVT", self.tiles, self.cleaned,
                 "-dsco", "NAME=flood_extent", "-dsco", f"MINZOOM={self.min_zoom}",
                 "-dsco", f"MAXZOOM={self.max_zoom}", "-dsco", "COMPRESS=NO",
                 "-dsco", "SIMPLIFICATION=0", "-dsco", "MAX_SIZE=5000000",
                 "-dsco", "MAX_FEATURES=1000000",
                 "-dsco", f"TEMPORARY_DB={self.work / 'mvt_tmp.sqlite'}")

    def check(self):
        """Reads the cleaned polygons and the cut tiles back, and fails if they disagree."""
        dataset = ogr.Open(str(self.cleaned))
        layer = dataset.GetLayer()
        transform = reprojection_to_4326(layer.GetSpatialRef())
        areas, polygons = {}, {}
        for feature in layer:
            code = feature.GetField("DN")
            geom = feature.GetGeometryRef()
            areas[code] = geom.GetArea()
            geom_4326 = geom.Clone()
            if transform is not None:
                geom_4326.Transform(transform)
            polygons[code] = geom_4326.ExportToWkb()
        tile_count = sum(1 for _ in self.tiles.rglob("*.pbf")) if self.tiles.exists() else 0
        self.say(f"Area per band (m2): { {code: round(area) for code, area in sorted(areas.items())} }")
        self.say(f"Tiles: {tile_count}")
        unexpected = set(areas) - EXPECTED_CODES
        if unexpected:
            raise FloodExtentError(f"Unexpected band codes: {sorted(unexpected)}")
        if areas and tile_count == 0:
            raise FloodExtentError("Polygons exist but no tiles were written")
        return FloodExtentResult(tile_count=tile_count, area_by_band=areas, polygons_4326=polygons)

    def timed(self, label, step):
        start = time.time()
        step()
        self.say(f"{label}: {time.time() - start:.1f} s")

    def execute(self):
        with tempfile.TemporaryDirectory(prefix="flood_extent_", dir=self.tmp_root) as work:
            self.bind(work)
            self.timed("reclassify depth", self.reclassify_depth)
            if not self.has_wet_cells():
                self.say("No wet cells above 5 cm in this timestep, so there are no polygons or tiles.")
                remove_tiles(self.tiles_dir)
                return FloodExtentResult(tile_count=0)
            for label, step in [
                ("close bands", self.close_bands),
                ("polygonize", self.polygonize),
                ("dissolve", self.dissolve),
                ("clean", self.clean),
            ]:
                self.timed(label, step)
            if self.cleaned_feature_count() == 0:
                self.say("Every flooded patch was smaller than the minimum area, so there are no tiles.")
                remove_tiles(self.tiles_dir)
                return FloodExtentResult(tile_count=0)
            self.timed("cut tiles", self.cut_tiles)
            result = self.check()
            if result.is_empty:
                remove_tiles(self.tiles_dir)
            else:
                publish_tiles(self.tiles, self.tiles_dir)
            return result


def reprojection_to_4326(source_srs):
    """A transform from `source_srs` to EPSG:4326, or None if the source has no defined SRS.

    `flood_extent_polygon` stores geometry(Geometry,4326), so every polygon written there needs
    reprojecting from the depth raster's own CRS (typically a projected, metric one, since
    `Pipeline.check()`'s areas are already in m2).
    """
    if source_srs is None:
        return None
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return osr.CoordinateTransformation(source_srs, target_srs)


def ring_area(ring):
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)
    return polygon.GetArea()


def clean_multipolygon(geom, min_area):
    cleaned = ogr.Geometry(ogr.wkbMultiPolygon)
    for part in geom:
        kept = ogr.Geometry(ogr.wkbPolygon)
        kept.AddGeometry(part.GetGeometryRef(0))
        for i in range(1, part.GetGeometryCount()):
            hole = part.GetGeometryRef(i)
            if ring_area(hole) >= min_area:
                kept.AddGeometry(hole)
        if kept.GetArea() >= min_area:
            cleaned.AddGeometry(kept)
    return cleaned


def remove_tiles(tiles_dir):
    """A timestep with nothing flooded has no tiles, and must not keep an older build's tiles."""
    shutil.rmtree(tiles_dir, ignore_errors=True)


def publish_tiles(built, tiles_dir):
    """Puts a finished tile folder at `tiles_dir`, so a reader never sees a half-written one.

    The copy goes to a sibling folder first, since the build folder may be on another filesystem,
    and the rename that follows is what makes the new tiles appear.
    """
    tiles_dir = Path(tiles_dir)
    tiles_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = tiles_dir.with_name(f".{tiles_dir.name}.partial")
    previous = tiles_dir.with_name(f".{tiles_dir.name}.previous")
    for leftover in (staging, previous):
        shutil.rmtree(leftover, ignore_errors=True)
    shutil.copytree(built, staging)
    if tiles_dir.exists():
        tiles_dir.rename(previous)
    staging.rename(tiles_dir)
    shutil.rmtree(previous, ignore_errors=True)


def build_flood_extent(depth_tif, tiles_dir, *, band=1, radius=8, min_area=20,
                       min_zoom=10, max_zoom=16, tmp_root=None, verbose=False):
    """Builds the tiles of one depth raster timestep into `tiles_dir` and returns a summary.

    `tiles_dir` is replaced as a whole, or removed when nothing is flooded. `tmp_root` is where the
    temporary build folder goes (the system temp folder by default).
    """
    return Pipeline(depth_tif, tiles_dir, band, radius, min_area, min_zoom, max_zoom,
                    tmp_root=tmp_root, verbose=verbose).execute()


def stamp_key(depth_file):
    """depth_20260811_014000.tif -> '20260811T014000', the folder name for that timestep."""
    match = DEPTH_FILE.match(Path(depth_file).name)
    if not match:
        raise FloodExtentError(f"Not a depth_<date>_<time>.tif file: {depth_file}")
    return f"{match.group(1)}T{match.group(2)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("depth_tif", help="3Di depth raster")
    parser.add_argument("tiles_dir", help="folder the finished tiles are written to; the only output")
    parser.add_argument("--band", type=int, default=1, help="timestep band, counting from 1")
    parser.add_argument("--radius", type=int, default=8, help="closing radius in cells")
    parser.add_argument("--min-area", type=float, default=20, help="smallest hole or polygon in m2")
    parser.add_argument("--min-zoom", type=int, default=10)
    parser.add_argument("--max-zoom", type=int, default=16)
    args = parser.parse_args()
    try:
        build_flood_extent(args.depth_tif, args.tiles_dir, band=args.band, radius=args.radius,
                           min_area=args.min_area, min_zoom=args.min_zoom, max_zoom=args.max_zoom,
                           verbose=True)
    except FloodExtentError as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
