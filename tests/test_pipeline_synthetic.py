"""End-to-end test of prep -> model -> ranking -> validation -> figures on SYNTHETIC inputs.

Uses the real district boundary and grid but random, smoothed layers instead of downloads,
so the processing code can be tested offline. Outputs go to outputs/<district>_synthetic and
must never be presented as results.
Run:  python -m tests.test_pipeline_synthetic kamrup
"""
import logging
import shutil
import sys

import geopandas as gpd
import numpy as np
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString, Point

from d13 import model, rank, report, validate
from d13.core import get_district, load_config, make_grid, save


def field(shape, rng, sigma=40, lo=0, hi=1):
    f = gaussian_filter(rng.standard_normal(shape), sigma)
    f = (f - f.min()) / (f.max() - f.min())
    return lo + f * (hi - lo)


def main(base="kamrup"):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()
    key = f"{base}_synthetic"
    cfg["districts"][key] = dict(cfg["districts"][base])
    d = get_district(key, cfg)
    shutil.rmtree(d.interim, ignore_errors=True)
    shutil.rmtree(d.out, ignore_errors=True)
    g = make_grid(d)
    rng = np.random.default_rng(0)
    sh = g.shape
    i = d.interim
    u = field(sh, rng, 25)
    wc = np.select([u < 0.18, u < 0.28, u < 0.36, u < 0.70, u < 0.74, u < 0.80, u < 0.85],
                   [10, 30, 20, 40, 50, 60, 80], 90).astype("uint8")
    save(g, wc, i / "worldcover_2021.tif", "uint8", 0)
    esri = np.select([wc == 10, wc == 40, wc == 50, wc == 80, wc == 90], [2, 5, 7, 1, 4], 11).astype("uint8")
    for y in cfg["fetch"]["esri_lulc_years"]:
        save(g, esri, i / f"esri_lulc_{y}.tif", "uint8", 0)
    save(g, field(sh, rng, 60, 0, 1500), i / "dem.tif")
    save(g, np.where(wc == 80, 95, field(sh, rng, 30, 0, 40)), i / "jrc_occurrence.tif")
    save(g, field(sh, rng, 150, 1600, 2600), i / "rain_annual_mm.tif")
    for p, lo, hi in [("soc", 4, 30), ("phh2o", 4.2, 6.8), ("nitrogen", 0.4, 2.5), ("cec", 4, 25),
                      ("clay", 10, 45), ("sand", 15, 60)]:
        save(g, field(sh, rng, 20, lo, hi), i / f"soil_{p}_0-30.tif")
    save(g, field(sh, rng, 15, 0.15, 0.85), i / "ndvi_kharif_peak.tif")
    save(g, field(sh, rng, 15, 0.1, 0.7), i / "ndvi_rabi_peak.tif")
    save(g, field(sh, rng, 40, 0, 0.9) ** 2, i / "flood_freq_s1.tif")
    b = g.bounds()
    (i / "osm").mkdir(exist_ok=True)
    xs = np.linspace(b[0], b[2], 8)
    ys = np.linspace(b[1], b[3], 8)
    roads = [LineString([(x, b[1]), (x, b[3])]) for x in xs[1:-1]] + [LineString([(b[0], y), (b[2], y)]) for y in ys[2:-2]]
    gpd.GeoDataFrame(geometry=roads, crs=g.crs).to_file(i / "osm" / "roads.gpkg")
    gpd.GeoDataFrame(geometry=[LineString([(b[0], ys[4]), (b[2], ys[5])])], crs=g.crs).to_file(i / "osm" / "rivers.gpkg")
    gpd.GeoDataFrame({"name": ["T1", "T2"]}, geometry=[Point(xs[2], ys[3]), Point(xs[5], ys[5])],
                     crs=g.crs).to_file(i / "osm" / "towns.gpkg")
    gpd.GeoDataFrame(geometry=[], crs=g.crs).to_file(i / "osm" / "protected.gpkg")

    model.preprocess(d)
    model.land_status(d)
    for p in cfg["profiles"]:
        res = model.suitability(d, p)
        patches = rank.run(d, p, res)
        v = validate.run(d, p, res)
        report.figures(d, p, res, patches)
        report.web_overlay(d, p, res)
        report.summary(d, p, patches)
        assert len(patches) > 0, "no patches produced"
        assert patches.reason.str.len().min() > 10
        assert 0 < v["sensitivity_min_rho"] <= 1
    print("SYNTHETIC TEST PASSED for", key)


if __name__ == "__main__":
    main(*(sys.argv[1:] or ["kamrup"]))
