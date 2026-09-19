#!/usr/bin/env python3
"""Build a flood-extent layer from one timestep of a 3Di depth raster.

Runs the same steps as flood_extent.ipynb, end to end: reclassify the depth into band codes,
close the small gaps between wet cells, polygonize, dissolve by band, delete small holes and
specks, and cut vector tiles. It needs GDAL 3.3 or later (with the Python bindings) and GRASS GIS 8
on the command line.

    python3 flood_extent.py DEPTH_TIF OUT_DIR [--band 1] [--radius 8] [--min-area 20]

`OUT_DIR` holds every intermediate file, the GRASS project, `cleaned.gpkg`, and the `mvt` tile
folder. Rerunning deletes the GRASS project, the intermediate layers, and the tiles.
"""

import argparse
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from osgeo import ogr

ogr.UseExceptions()

BAND_TABLE = [(0.05, 0), (0.1, 10), (0.2, 20), (0.3, 30), (0.4, 40), (0.5, 50), (0.6, 60)]
TOP_CODE = 600
DEPTH_NODATA = -9999
EXPECTED_CODES = {code for _, code in BAND_TABLE if code > 0} | {TOP_CODE}


class Pipeline:
    def __init__(self, depth_tif, out_dir, band, radius, min_area, min_zoom, max_zoom):
        self.depth_tif = Path(depth_tif)
        self.band = band
        self.radius = radius
        self.min_area = min_area
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.work = Path(out_dir).resolve()
        self.project = self.work / "grass_project"
        self.depth_bands = self.work / "re-classify_depth.tif"
        self.final_tif = self.work / "final.tif"
        self.poly = self.work / "poly.gpkg"
        self.dissolved = self.work / "dissolved.gpkg"
        self.cleaned = self.work / "cleaned.gpkg"
        self.tiles = self.work / "mvt"

    @contextmanager
    def timed(self, label):
        start = time.time()
        yield
        print(f"{label}: {time.time() - start:.1f} s", flush=True)

    @staticmethod
    def run(*args):
        subprocess.run([str(a) for a in args], check=True)

    def grass(self, module, *args):
        self.run("grass", self.project / "PERMANENT", "--exec", module, *args, "--overwrite", "--quiet")

    def band_counts(self, raster):
        out = subprocess.run(
            ["grass", str(self.project / "PERMANENT"), "--exec", "r.stats", "-c", "-n", f"input={raster}"],
            check=True, capture_output=True, text=True,
        ).stdout
        print(out, flush=True)

    def reset(self):
        self.work.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(self.project, ignore_errors=True)
        shutil.rmtree(self.tiles, ignore_errors=True)
        for path in (self.depth_bands, self.final_tif, self.poly, self.dissolved, self.cleaned):
            path.unlink(missing_ok=True)

    def reclassify_depth(self):
        expression = str(TOP_CODE)
        for limit, code in reversed(BAND_TABLE):
            expression = f"numpy.where(A<={limit},{code},{expression})"
        self.run("gdal_calc.py", "-A", self.depth_tif, f"--A_band={self.band}",
                 f"--outfile={self.depth_bands}", f"--calc={expression}",
                 f"--NoDataValue={DEPTH_NODATA}", "--type=Int16", "--co=COMPRESS=DEFLATE",
                 "--overwrite", "--quiet")

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

    def cut_tiles(self):
        self.run("ogr2ogr", "-q", "-f", "MVT", self.tiles, self.cleaned,
                 "-dsco", "NAME=flood_extent", "-dsco", f"MINZOOM={self.min_zoom}",
                 "-dsco", f"MAXZOOM={self.max_zoom}", "-dsco", "COMPRESS=NO",
                 "-dsco", "SIMPLIFICATION=0", "-dsco", "MAX_SIZE=5000000",
                 "-dsco", "MAX_FEATURES=1000000",
                 "-dsco", f"TEMPORARY_DB={self.work / 'mvt_tmp.sqlite'}")
        (self.work / "mvt_tmp.sqlite").unlink(missing_ok=True)

    def check(self):
        dataset = ogr.Open(str(self.cleaned))
        layer = dataset.GetLayer()
        areas = {feature.GetField("DN"): feature.GetGeometryRef().GetArea() for feature in layer}
        tile_count = sum(1 for _ in self.tiles.rglob("*.pbf"))
        print("Area per band (m2):", {code: round(area) for code, area in sorted(areas.items())})
        print(f"Tiles: {tile_count} in {self.tiles}")
        unexpected = set(areas) - EXPECTED_CODES
        if unexpected:
            raise SystemExit(f"Unexpected band codes: {sorted(unexpected)}")
        if areas and tile_count == 0:
            raise SystemExit("Polygons exist but no tiles were written")
        if not areas:
            print("No wet cells above 5 cm in this timestep, so there are no polygons or tiles.")

    def execute(self):
        self.reset()
        steps = [
            ("reclassify depth", self.reclassify_depth),
            ("close bands", self.close_bands),
            ("polygonize", self.polygonize),
            ("dissolve", self.dissolve),
            ("clean", self.clean),
            ("cut tiles", self.cut_tiles),
        ]
        total = time.time()
        for label, step in steps:
            with self.timed(label):
                step()
        print(f"total: {time.time() - total:.1f} s", flush=True)
        self.check()


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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("depth_tif", help="3Di depth raster, one band per timestep")
    parser.add_argument("out_dir", help="working folder for every intermediate and final file")
    parser.add_argument("--band", type=int, default=1, help="timestep band, counting from 1")
    parser.add_argument("--radius", type=int, default=8, help="closing radius in cells")
    parser.add_argument("--min-area", type=float, default=20, help="smallest hole or polygon in m2")
    parser.add_argument("--min-zoom", type=int, default=10)
    parser.add_argument("--max-zoom", type=int, default=16)
    args = parser.parse_args()
    Pipeline(args.depth_tif, args.out_dir, args.band, args.radius, args.min_area,
             args.min_zoom, args.max_zoom).execute()


if __name__ == "__main__":
    main()
