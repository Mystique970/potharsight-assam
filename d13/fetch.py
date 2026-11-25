"""Acquisition of open data. No login needed for any source below.

Each fetcher writes a GeoTIFF on the district's 30 m analysis grid into data/interim/<district>/
and appends a line to data/data_register.csv. Every fetcher is independent: re-run one with
`python run_all.py --district kamrup --steps fetch --only dem`.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time

import numpy as np
import requests
from rasterio.enums import Resampling
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, polygonize, unary_union

from .core import ROOT, District, Grid, load_grid, log, mosaic, save, warp_to_grid

UA = {"User-Agent": "d13-agri-suitability/1.0 (NESFIC 2026 research prototype; python-requests)",
      "Accept": "*/*"}


def register(d: District, name, source, url, licence, note=""):
    f = ROOT / d.cfg["project"]["data_dir"] / "data_register.csv"
    new = not f.exists()
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "district", "layer", "source", "url", "licence", "note"])
        w.writerow([dt.date.today().isoformat(), d.key, name, source, url, licence, note])


def _pc_client(signed: bool = True):
    import planetary_computer
    import pystac_client
    return pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace if signed else None)


def _fresh(item):
    """Sign a Planetary Computer item right before reading it (SAS tokens expire after ~1 h)."""
    href = next(iter(item.assets.values())).href
    if "blob.core.windows.net" not in href:
        return item
    import planetary_computer
    return planetary_computer.sign(item)


def _dedupe(items):
    """Drop reprocessed duplicates of the same acquisition (keep the newest processing)."""
    best = {}
    for it in items:
        k = it.id.rsplit("_", 1)[0] if it.id.count("_") >= 5 else it.id
        if k not in best or it.id > best[k].id:
            best[k] = it
    return list(best.values())


def _search(client, collection, bbox, datetime=None, query=None, limit=500):
    s = client.search(collections=[collection], bbox=bbox, datetime=datetime, query=query,
                      max_items=limit)
    return list(s.items())


def _warp_items(items, asset, g, resampling, default_nodata=None):
    out = None
    for it in items:
        if asset not in it.assets:
            continue
        try:
            a = warp_to_grid(it.assets[asset].href, g, resampling, default_nodata=default_nodata)
            out = mosaic(out, a)
        except Exception as e:  # keep going on a single bad tile
            log.warning("  skip %s: %s", it.id, e)
    return out


def _try_pc(fn_name, f):
    """Run f() against Planetary Computer; return None (and log) if PC is unavailable."""
    try:
        return f()
    except Exception as e:
        log.warning("  %s via Planetary Computer failed (%s); using direct download", fn_name, e)
        return None


def _tiles_direct(urls, g, resampling, default_nodata=None):
    out = None
    for u in urls:
        try:
            out = mosaic(out, warp_to_grid(u, g, resampling, default_nodata=default_nodata))
            log.info("  read %s", u.rsplit("/", 1)[-1])
        except Exception as e:
            log.info("  (no tile) %s: %s", u.rsplit("/", 1)[-1], str(e)[:80])
    return out


def _deg_tiles(g, step):
    w, s, e, n = g.lonlat_bbox()
    return [(la, lo) for la in range(int(math.floor(s / step) * step), int(math.ceil(n)), step)
            for lo in range(int(math.floor(w / step) * step), int(math.ceil(e)), step)]


# ---------------------------------------------------------------- land cover
def worldcover(d: District, g: Grid):
    a = _try_pc("WorldCover", lambda: _warp_items(
        _search(_pc_client(), "esa-worldcover", g.lonlat_bbox(), "2021-01-01/2021-12-31"),
        "map", g, Resampling.nearest, default_nodata=0))
    src = "https://planetarycomputer.microsoft.com/dataset/esa-worldcover"
    if a is None:
        urls = [d.cfg["sources"]["worldcover_tile"].format(lat=la, lon=lo) for la, lo in _deg_tiles(g, 3)]
        a = _tiles_direct(urls, g, Resampling.nearest, default_nodata=0)
        src = "https://esa-worldcover.org (AWS open data bucket)"
    if a is None:
        raise RuntimeError("WorldCover unavailable from all sources")
    save(g, a, d.interim / "worldcover_2021.tif", "uint8", 0)
    register(d, "worldcover_2021", "ESA WorldCover v200 2021", src, "CC BY 4.0")


def esri_lulc(d: District, g: Grid):
    stack = []
    pc_ok = True
    for y in d.cfg["fetch"]["esri_lulc_years"]:
        a = None
        if pc_ok:
            a = _try_pc(f"Esri LULC {y}", lambda: _warp_items(
                _search(_pc_client(), "io-lulc-annual-v02", g.lonlat_bbox(), f"{y}-01-01/{y}-12-31"),
                "data", g, Resampling.nearest, default_nodata=0))
            pc_ok = a is not None
        if a is None:
            urls = [d.cfg["sources"]["esri_lulc_tile"].format(year=y, y1=y + 1, zone=z)
                    for z in d.cfg["sources"]["esri_lulc_zones"]]
            a = _tiles_direct(urls, g, Resampling.nearest, default_nodata=0)
        if a is None:
            log.warning("  no Esri LULC for %s", y)
            continue
        save(g, a, d.interim / f"esri_lulc_{y}.tif", "uint8", 0)
        stack.append(y)
    if not stack:
        raise RuntimeError("Esri LULC unavailable (model will run without it)")
    register(d, "esri_lulc", f"Esri/Impact Observatory 10 m annual LULC {stack}",
             "https://livingatlas.arcgis.com/landcoverexplorer", "CC BY 4.0")


# ---------------------------------------------------------------- terrain
def dem(d: District, g: Grid):
    a = _try_pc("DEM", lambda: _warp_items(_search(_pc_client(), "cop-dem-glo-30", g.lonlat_bbox()),
                                         "data", g, Resampling.bilinear))
    src = "https://planetarycomputer.microsoft.com/dataset/cop-dem-glo-30"
    if a is None:
        urls = [d.cfg["sources"]["cop_dem_tile"].format(lat=la, lon=lo) for la, lo in _deg_tiles(g, 1)]
        a = _tiles_direct(urls, g, Resampling.bilinear)
        src = "https://registry.opendata.aws/copernicus-dem/"
    if a is None:
        raise RuntimeError("DEM unavailable from all sources")
    save(g, a, d.interim / "dem.tif")
    register(d, "dem", "Copernicus DEM GLO-30", src, "Copernicus DEM licence (free)")


# ---------------------------------------------------------------- water
def jrc_water(d: District, g: Grid):
    a = None
    try:
        c = _pc_client()
        items = _search(c, "jrc-gsw", g.lonlat_bbox())
        a = _warp_items(items, "occurrence", g, Resampling.nearest, default_nodata=255)
        src = "https://planetarycomputer.microsoft.com/dataset/jrc-gsw"
    except Exception as e:
        log.warning("  JRC via Planetary Computer failed (%s); trying Google Storage tiles", e)
    if a is None:
        w, s, e_, n = g.lonlat_bbox()
        tiles = {(int(math.floor(x / 10) * 10), int(math.ceil(y / 10) * 10))
                 for x in (w, e_) for y in (s, n)}
        for lon, lat in tiles:
            url = d.cfg["sources"]["jrc_tile"].format(lon=lon, lat=lat)
            a = mosaic(a, warp_to_grid(url, g, Resampling.nearest, default_nodata=255))
        src = "https://global-surface-water.appspot.com/download"
    save(g, a, d.interim / "jrc_occurrence.tif")
    register(d, "jrc_occurrence", "JRC Global Surface Water v1.4 occurrence", src, "Free (EC JRC)")


def chirps(d: District, g: Grid):
    acc, n, used = None, 0, ""
    templates = d.cfg["sources"]["chirps_annual"]
    templates = templates if isinstance(templates, list) else [templates]
    for y in d.cfg["fetch"]["chirps_years"]:
        for t in templates:
            url = t.format(year=y)
            try:
                a = warp_to_grid(url, g, Resampling.bilinear, default_nodata=-9999)
                a[a < 0] = np.nan
                acc = a if acc is None else acc + a
                n += 1
                used = url.rsplit("/", 1)[0]
                break
            except Exception as e:
                log.info("  CHIRPS %s not at %s (%s)", y, url, str(e)[:60])
    if n == 0:
        raise RuntimeError("CHIRPS unavailable (rainfall factor will be treated as non-limiting)")
    save(g, acc / n, d.interim / "rain_annual_mm.tif")
    register(d, "rain_annual_mm", f"CHIRPS annual mean of {n} years", used, "Public domain")


# ---------------------------------------------------------------- soil
SOIL_SCALE = {"soc": 0.1, "phh2o": 0.1, "nitrogen": 0.01, "cec": 0.1, "clay": 0.1, "sand": 0.1}
# SoilGrids mapped units -> soc g/kg, pH, N g/kg, CEC cmol(c)/kg, clay %, sand %


def soil(d: District, g: Grid):
    f = d.cfg["fetch"]
    thick = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    for prop in f["soil_props"]:
        acc, wsum = None, 0
        for depth in f["soil_depths"]:
            url = d.cfg["sources"]["soilgrids_vrt"].format(prop=prop, depth=depth)
            a = warp_to_grid(url, g, Resampling.bilinear, default_nodata=-32768) * SOIL_SCALE[prop]
            acc = a * thick[depth] if acc is None else acc + a * thick[depth]
            wsum += thick[depth]
        save(g, acc / wsum, d.interim / f"soil_{prop}_0-30.tif")
    register(d, "soil_0-30cm", "ISRIC SoilGrids 2.0 (soc, pH, N, CEC, clay, sand), depth-weighted 0-30 cm",
             "https://www.isric.org/explore/soilgrids", "CC BY 4.0")


# ---------------------------------------------------------------- Sentinel-2 NDVI
def _s2_items(c, g, start, end, maxcloud, per_tile):
    items = _search(c, "sentinel-2-l2a", g.lonlat_bbox(), f"{start}/{end}",
                    query={"eo:cloud_cover": {"lt": maxcloud}})
    by_tile = {}
    for it in _dedupe(items):
        key = it.properties.get("s2:mgrs_tile") or it.properties.get("grid:code") or "x"
        by_tile.setdefault(key, []).append(it)
    chosen = []
    for lst in by_tile.values():
        chosen += sorted(lst, key=lambda i: i.properties.get("eo:cloud_cover", 100))[:per_tile]
    return chosen


def _ndvi(it, g):
    it = _fresh(it)
    a = it.assets
    k = ("B04", "B08", "SCL") if "B04" in a else ("red", "nir", "scl")
    # 10 m bands: overview 1 = 40 m; 20 m SCL: overview 0 = 40 m. ~16x less data than full res.
    red = warp_to_grid(a[k[0]].href, g, Resampling.average, default_nodata=0, overview_level=1)
    nir = warp_to_grid(a[k[1]].href, g, Resampling.average, default_nodata=0, overview_level=1)
    scl = warp_to_grid(a[k[2]].href, g, Resampling.nearest, default_nodata=0, overview_level=0)
    pr = it.properties
    pb = str(pr.get("s2:processing_baseline", "00.00"))
    off = 1000.0 if pb >= "04.00" else 0.0  # BOA_ADD_OFFSET from baseline 04.00 (Jan 2022)
    if pr.get("earthsearch:boa_offset_applied"):
        off = 0.0
    red, nir = red - off, nir - off
    with np.errstate(all="ignore"):
        nd = (nir - red) / (nir + red)
    nd[~np.isin(scl, [4, 5, 6, 7])] = np.nan  # keep vegetation, bare, water, unclassified
    nd[(nd < -1) | (nd > 1)] = np.nan
    return nd


def _s2_client():
    """Planetary Computer first, Earth Search (AWS) as fallback."""
    try:
        c = _pc_client(signed=False)
        c.get_collection("sentinel-2-l2a")
        return c, "https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a"
    except Exception as e:
        log.warning("  Sentinel-2 via Planetary Computer failed (%s); using Earth Search", e)
        import pystac_client
        return (pystac_client.Client.open("https://earth-search.aws.element84.com/v1"),
                "https://earth-search.aws.element84.com/v1 (sentinel-2-l2a)")


def s2_ndvi(d: District, g: Grid):
    c, src = _s2_client()
    f = d.cfg["fetch"]
    seasons = {"rabi": ("11-01", "02-28", 1), "kharif": ("07-15", "10-31", 0)}
    for season, (s, e, yplus) in seasons.items():
        yearly = []
        for y in f["s2_years"]:
            items = _s2_items(c, g, f"{y}-{s}", f"{y + yplus}-{e}", f["s2_max_cloud"],
                              f["s2_items_per_tile_per_season"])
            log.info("  S2 %s %s: %d items", season, y, len(items))
            mx = None
            for it in items:
                try:
                    nd = _ndvi(it, g)
                    mx = nd if mx is None else np.fmax(mx, nd)
                except Exception as ex:
                    log.warning("  skip %s: %s", it.id, ex)
            if mx is not None:
                yearly.append(mx)
        if not yearly:
            raise RuntimeError(f"no Sentinel-2 data for {season}")
        with np.errstate(all="ignore"):
            out = np.nanmedian(np.stack(yearly), axis=0)
        save(g, out, d.interim / f"ndvi_{season}_peak.tif")
    register(d, "ndvi_peaks", f"Sentinel-2 L2A seasonal peak NDVI, median of {f['s2_years']}",
             src, "Copernicus free")


# ---------------------------------------------------------------- Sentinel-1 flood frequency
def _s1_db(href, g: Grid, factor=4):
    """Sentinel-1 GRD amplitude (dB, uncalibrated) on the grid. GRD COGs are GCP-referenced:
    read a decimated overview (~40 m), rescale the GCPs and warp."""
    import rasterio
    from rasterio.control import GroundControlPoint
    from rasterio.warp import reproject
    from .core import GDAL_ENV
    with rasterio.Env(**GDAL_ENV), rasterio.open(href) as ds:
        gcps, gcrs = ds.gcps
        dst = np.full(g.shape, np.nan, "float32")
        if gcps:
            h, w = ds.height // factor, ds.width // factor
            a = ds.read(1, out_shape=(h, w), resampling=Resampling.average).astype("float32")
            sx, sy = ds.width / w, ds.height / h
            g2 = [GroundControlPoint(row=p.row / sy, col=p.col / sx, x=p.x, y=p.y, z=p.z) for p in gcps]
            a[a <= 0] = np.nan
            reproject(a, dst, gcps=g2, src_crs=gcrs, dst_transform=g.transform, dst_crs=g.crs,
                      resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
        else:
            dst = warp_to_grid(href, g, Resampling.average, default_nodata=0)
            dst[dst <= 0] = np.nan
    with np.errstate(all="ignore"):
        return 20 * np.log10(dst)


def s1_flood(d: District, g: Grid):
    """Monsoon open-water frequency from Sentinel-1 GRD (anonymous access).
    Threshold is self-calibrated per scene: midway between the median backscatter of permanent
    water (JRC occurrence >= 90) and of never-water land (JRC occurrence == 0)."""
    from .core import read
    c = _pc_client(signed=False)
    f = d.cfg["fetch"]
    occ = read(d.interim / "jrc_occurrence.tif")
    wref, lref = np.nan_to_num(occ) >= 90, np.nan_to_num(occ, nan=-1) == 0
    water = np.zeros(g.shape, "float32")
    valid = np.zeros(g.shape, "float32")
    used = 0
    for y in f["s1_years"]:
        m0, m1 = min(f["s1_months"]), max(f["s1_months"])
        items = _search(c, "sentinel-1-grd", g.lonlat_bbox(), f"{y}-{m0:02d}-01/{y}-{m1:02d}-30",
                        query={"sar:instrument_mode": {"eq": "IW"}})
        items = [i for i in sorted(items, key=lambda i: i.datetime) if "vv" in i.assets]
        if len(items) > f["s1_max_items_per_year"]:
            idx = np.linspace(0, len(items) - 1, f["s1_max_items_per_year"]).astype(int)
            items = [items[i] for i in idx]
        log.info("  S1 %s: %d scenes", y, len(items))
        for it in items:
            try:
                db = _s1_db(_fresh(it).assets["vv"].href, g)
            except Exception as ex:
                log.warning("  skip %s: %s", it.id, ex)
                continue
            ok = np.isfinite(db)
            if (ok & wref).sum() < 200 or (ok & lref).sum() < 2000:
                continue
            thr = (np.median(db[ok & wref]) + np.median(db[ok & lref])) / 2
            valid += ok
            water += ok & (db < thr)
            used += 1
    if used == 0:
        raise RuntimeError("no usable Sentinel-1 scenes")
    with np.errstate(all="ignore"):
        freq = np.where(valid > 0, water / valid, np.nan)
    save(g, freq, d.interim / "flood_freq_s1.tif")
    save(g, valid, d.interim / "flood_obs_count.tif")
    register(d, "flood_freq_s1", f"Sentinel-1 GRD monsoon water frequency, {used} scenes {f['s1_years']}",
             "https://planetarycomputer.microsoft.com/dataset/sentinel-1-grd", "Copernicus free")


# ---------------------------------------------------------------- OpenStreetMap
def _overpass(d, q):
    last = None
    for url in d.cfg["sources"]["overpass"]:
        for attempt in range(3):
            try:
                r = requests.post(url, data={"data": q}, headers=UA, timeout=300)
                if r.status_code == 200:
                    return r.json()
                last = f"HTTP {r.status_code} from {url}"
                if r.status_code in (400, 403, 406):
                    break  # this mirror refuses us; try the next one
            except Exception as e:
                last = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Overpass failed: {last}")


def osm(d: District, g: Grid):
    w, s, e, n = g.lonlat_bbox()
    bb = f"{s},{w},{n},{e}"
    q_roads = f"""[out:json][timeout:300];
      way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|motorway_link|trunk_link|primary_link|secondary_link)$"]({bb});
      out geom;"""
    q_places = f"""[out:json][timeout:120];node["place"~"^(city|town)$"]({bb});out;"""
    q_rivers = f"""[out:json][timeout:300];way["waterway"~"^(river|canal)$"]({bb});out geom;"""
    q_pa = f"""[out:json][timeout:300];
      (way["boundary"="protected_area"]({bb});relation["boundary"="protected_area"]({bb});
       way["leisure"="nature_reserve"]({bb});relation["leisure"="nature_reserve"]({bb});
       way["landuse"="forest"]["designation"]({bb}););
      out geom;"""
    import geopandas as gpd

    def lines(js):
        geoms = []
        for el in js.get("elements", []):
            if "geometry" in el and len(el["geometry"]) > 1:
                geoms.append(LineString([(p["lon"], p["lat"]) for p in el["geometry"]]))
        return gpd.GeoDataFrame(geometry=geoms, crs=4326)

    def polys(js):
        geoms = []
        for el in js.get("elements", []):
            if el["type"] == "way" and "geometry" in el and len(el["geometry"]) > 3:
                ring = [(p["lon"], p["lat"]) for p in el["geometry"]]
                if ring[0] == ring[-1]:
                    geoms.extend(polygonize([LineString(ring)]))
            elif el["type"] == "relation":
                ls = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                      for m in el.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
                if ls:
                    geoms.extend(polygonize(linemerge(unary_union(ls))))
        return gpd.GeoDataFrame(geometry=geoms, crs=4326)

    out = d.interim / "osm"
    out.mkdir(exist_ok=True)
    lines(_overpass(d, q_roads)).to_file(out / "roads.gpkg")
    pl = _overpass(d, q_places)
    gpd.GeoDataFrame({"name": [el.get("tags", {}).get("name", "") for el in pl["elements"]],
                      "place": [el.get("tags", {}).get("place", "") for el in pl["elements"]]},
                     geometry=[Point(el["lon"], el["lat"]) for el in pl["elements"]],
                     crs=4326).to_file(out / "towns.gpkg")
    lines(_overpass(d, q_rivers)).to_file(out / "rivers.gpkg")
    polys(_overpass(d, q_pa)).to_file(out / "protected.gpkg")
    register(d, "osm", "OpenStreetMap via Overpass (roads, towns, rivers, protected areas)",
             "https://www.openstreetmap.org/copyright", "ODbL")


FETCHERS = {
    "worldcover": worldcover, "esri_lulc": esri_lulc, "dem": dem, "jrc": jrc_water,
    "chirps": chirps, "soil": soil, "osm": osm, "s2": s2_ndvi, "s1": s1_flood,
}


def run(d: District, only: list[str] | None = None, skip_existing: bool = True):
    g = load_grid(d)
    done_marker = d.interim / "fetch_status.json"
    status = json.loads(done_marker.read_text()) if done_marker.exists() else {}
    for name, fn in FETCHERS.items():
        if only and name not in only:
            continue
        if skip_existing and status.get(name) == "ok" and not only:
            log.info("[fetch] %s already done", name)
            continue
        log.info("[fetch] %s ...", name)
        t0 = time.time()
        try:
            fn(d, g)
            status[name] = "ok"
            log.info("[fetch] %s ok (%.0f s)", name, time.time() - t0)
        except Exception as e:
            status[name] = f"failed: {e}"
            log.error("[fetch] %s FAILED: %s", name, e)
        done_marker.write_text(json.dumps(status, indent=1))
    return status
