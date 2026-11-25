"""Config, analysis grid, raster I/O and warping helpers."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import yaml
from rasterio import features
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT

ROOT = Path(__file__).resolve().parents[1]
log = logging.getLogger("d13")

GDAL_ENV = dict(
    GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.tiff,.vrt",
    GDAL_HTTP_MAX_RETRY="5",
    GDAL_HTTP_RETRY_DELAY="2",
    GDAL_HTTP_TIMEOUT="120",
    VSI_CACHE="TRUE",
    GDAL_CACHEMAX=512,
)


def load_config(path: str | Path = ROOT / "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class District:
    key: str
    cfg: dict
    dcfg: dict

    @property
    def interim(self) -> Path:
        p = ROOT / self.cfg["project"]["data_dir"] / "interim" / self.key
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def out(self) -> Path:
        p = ROOT / self.cfg["project"]["output_dir"] / self.key
        p.mkdir(parents=True, exist_ok=True)
        return p

    def boundary(self, level: str = "districts") -> gpd.GeoDataFrame:
        b = self.cfg["boundaries"]
        g = gpd.read_file(ROOT / b[level])
        crs = self.cfg["project"]["crs"]
        if level == "districts":
            g = g[g[b["name_field"]] == self.dcfg["boundary_name"]]
            if g.empty:
                raise ValueError(f"District '{self.dcfg['boundary_name']}' not found in {b[level]}")
            return g.to_crs(crs)
        aoi = self.boundary("districts").to_crs(crs)
        g = g.to_crs(crs)
        pts = g.copy()
        pts["geometry"] = g.representative_point()
        inside = pts.within(aoi.geometry.union_all())
        return g[inside].reset_index(drop=True)


def get_district(key: str, cfg: dict | None = None) -> District:
    cfg = cfg or load_config()
    if key not in cfg["districts"]:
        raise KeyError(f"Unknown district '{key}'. Add it to config.yaml -> districts.")
    return District(key, cfg, cfg["districts"][key])


@dataclass
class Grid:
    crs: str
    transform: rasterio.Affine
    width: int
    height: int

    @property
    def shape(self):
        return (self.height, self.width)

    @property
    def res(self) -> float:
        return self.transform.a

    def bounds(self):
        t = self.transform
        return (t.c, t.f + t.e * self.height, t.c + t.a * self.width, t.f)

    def profile(self, dtype="float32", nodata=np.nan, count=1):
        return dict(driver="GTiff", crs=self.crs, transform=self.transform, width=self.width,
                    height=self.height, count=count, dtype=dtype, nodata=nodata,
                    compress="deflate", tiled=True, blockxsize=256, blockysize=256)

    def lonlat_bbox(self, pad=0.01):
        b = gpd.GeoSeries.from_xy([self.bounds()[0], self.bounds()[2]],
                                  [self.bounds()[1], self.bounds()[3]], crs=self.crs).to_crs(4326)
        return [b.x.min() - pad, b.y.min() - pad, b.x.max() + pad, b.y.max() + pad]


def make_grid(d: District) -> Grid:
    p = d.cfg["project"]
    res, buf = p["resolution_m"], p["buffer_m"]
    minx, miny, maxx, maxy = d.boundary().total_bounds
    minx, miny = np.floor((minx - buf) / res) * res, np.floor((miny - buf) / res) * res
    maxx, maxy = np.ceil((maxx + buf) / res) * res, np.ceil((maxy + buf) / res) * res
    w, h = int(round((maxx - minx) / res)), int(round((maxy - miny) / res))
    g = Grid(p["crs"], from_origin(minx, maxy, res, res), w, h)
    (d.interim / "grid.json").write_text(json.dumps(
        dict(crs=g.crs, transform=list(g.transform)[:6], width=w, height=h)))
    return g


def load_grid(d: District) -> Grid:
    f = d.interim / "grid.json"
    if not f.exists():
        return make_grid(d)
    j = json.loads(f.read_text())
    return Grid(j["crs"], rasterio.Affine(*j["transform"]), j["width"], j["height"])


def aoi_mask(d: District, g: Grid) -> np.ndarray:
    geom = d.boundary().geometry
    return features.geometry_mask(geom, out_shape=g.shape, transform=g.transform, invert=True)


def save(g: Grid, arr: np.ndarray, path: Path, dtype="float32", nodata=None, descriptions=None):
    arr = np.asarray(arr)
    if arr.ndim == 2:
        arr = arr[None]
    if nodata is None:
        nodata = np.nan if np.dtype(dtype).kind == "f" else 0
    prof = g.profile(dtype=dtype, nodata=nodata, count=arr.shape[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as dst:
        out = arr.astype(dtype) if np.dtype(dtype).kind == "f" else np.nan_to_num(arr, nan=nodata).astype(dtype)
        dst.write(out)
        if descriptions:
            for i, s in enumerate(descriptions, 1):
                dst.set_band_description(i, s)


def read(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(band).astype("float32")
        if src.nodata is not None and not np.isnan(src.nodata):
            a[a == src.nodata] = np.nan
    return a


def warp_to_grid(src: str, g: Grid, resampling=Resampling.bilinear, band: int = 1,
                 default_nodata=None, overview_level=None, retries: int = 2) -> np.ndarray:
    """Read any raster (local path, URL, /vsicurl/) resampled onto the analysis grid.
    overview_level=k reads the k-th internal overview (much less data for 10 m imagery).
    Returns float32 with NaN where there is no data. Retries transient network errors."""
    last = None
    for attempt in range(retries + 1):
        try:
            return _warp_once(src, g, resampling, band, default_nodata, overview_level)
        except Exception as e:  # noqa: BLE001
            last = e
            if "403" in str(e) or "404" in str(e):
                break
            if overview_level is not None and "overview" in str(e).lower():
                overview_level = None
    raise last


def _warp_once(src, g, resampling, band, default_nodata, overview_level):
    if src.startswith("http"):
        src = "/vsicurl/" + src
    with rasterio.Env(**GDAL_ENV):
        kw_open = {} if overview_level is None else {"overview_level": overview_level}
        with rasterio.open(src, **kw_open) as ds:
            nod = ds.nodata if ds.nodata is not None else default_nodata
            kw = dict(crs=g.crs, transform=g.transform, width=g.width, height=g.height,
                      resampling=resampling)
            if nod is not None and not (isinstance(nod, float) and np.isnan(nod)):
                kw.update(src_nodata=nod, nodata=nod)
            else:
                kw.update(add_alpha=True)
                nod = None
            with WarpedVRT(ds, **kw) as vrt:
                a = vrt.read(band).astype("float32")
                if nod is not None:
                    a[a == nod] = np.nan
                    m = vrt.read_masks(band)
                else:
                    m = vrt.dataset_mask()
                a[m == 0] = np.nan
    return a


def mosaic(base: np.ndarray | None, new: np.ndarray) -> np.ndarray:
    if base is None:
        return new
    return np.where(np.isnan(base), new, base)


def ramp(x, lo, hi):
    """Linear 0..1 score: 0 at lo, 1 at hi (lo>hi gives a decreasing ramp)."""
    return np.clip((x - lo) / (hi - lo), 0, 1)


def trapezoid(x, limits, optimum):
    lo0, hi0 = limits
    lo1, hi1 = optimum
    up = np.clip((x - lo0) / (lo1 - lo0), 0, 1)
    down = np.clip((hi0 - x) / (hi0 - hi1), 0, 1)
    return np.minimum(up, down)
