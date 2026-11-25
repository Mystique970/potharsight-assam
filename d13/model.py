"""Derived layers, land status (availability), constraints, factor scores, suitability and reasons."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
from rasterio import features
from scipy import ndimage

from .core import District, Grid, aoi_mask, load_grid, log, ramp, read, save, trapezoid

# ---------------------------------------------------------------- land status codes
STATUS = {
    0: "Excluded (built-up, water, forest, wetland, protected)",
    1: "Vacant open land (grass, scrub, bare)",
    2: "Long fallow / under-used cropland",
    3: "Seasonal (rabi) fallow cropland",
    4: "Active double-cropped land",
}
CANDIDATE = (1, 2, 3)
FACTORS = ["soil", "water", "flood", "terrain", "productivity", "access"]
FACTOR_LABEL = {
    "soil": "soil fertility", "water": "water availability", "flood": "flood safety",
    "terrain": "gentle terrain", "productivity": "vegetation productivity", "access": "road/market access",
}
CLASS_NAMES = {1: "S1 Highly suitable", 2: "S2 Moderately suitable", 3: "S3 Marginally suitable",
               4: "N Not suitable", 5: "N Constrained (slope/flood)"}


def _opt(d, name):
    p = d.interim / name
    return read(p) if p.exists() else None


def _dist(g: Grid, gdf: gpd.GeoDataFrame | None, extra: np.ndarray | None = None) -> np.ndarray:
    m = np.zeros(g.shape, bool)
    if gdf is not None and len(gdf):
        gg = gdf.to_crs(g.crs)
        m |= features.rasterize(((geom, 1) for geom in gg.geometry if geom is not None),
                                out_shape=g.shape, transform=g.transform, all_touched=True).astype(bool)
    if extra is not None:
        m |= extra
    if not m.any():  # layer missing: distance unknown -> factor treated as neutral later
        return np.full(g.shape, np.nan, "float32")
    return (ndimage.distance_transform_edt(~m) * g.res).astype("float32")


def _gpkg(d, name):
    p = d.interim / "osm" / name
    return gpd.read_file(p) if p.exists() else None


# ---------------------------------------------------------------- preprocess
def preprocess(d: District):
    g = load_grid(d)
    dem = read(d.interim / "dem.tif")
    gy, gx = np.gradient(dem, g.res)
    slope = np.hypot(gx, gy) * 100
    save(g, slope, d.interim / "slope_pct.tif")

    occ = _opt(d, "jrc_occurrence.tif")
    perm_water = (occ >= d.cfg["availability"]["permanent_water_occurrence"]) if occ is not None else None
    if perm_water is not None:
        perm_water = np.nan_to_num(perm_water).astype(bool)
    save(g, _dist(g, _gpkg(d, "rivers.gpkg"), perm_water), d.interim / "dist_water_m.tif")
    save(g, _dist(g, _gpkg(d, "roads.gpkg")), d.interim / "dist_road_m.tif")
    save(g, _dist(g, _gpkg(d, "towns.gpkg")), d.interim / "dist_town_m.tif")

    pa = _gpkg(d, "protected.gpkg")
    pam = np.zeros(g.shape, bool)
    if pa is not None and len(pa):
        pam = features.rasterize(((geom, 1) for geom in pa.to_crs(g.crs).geometry),
                                 out_shape=g.shape, transform=g.transform).astype(bool)
    save(g, pam, d.interim / "protected_mask.tif", "uint8", 255)

    # flood frequency: Sentinel-1 if available, else proxy from JRC + Esri LULC water/flooded veg
    ff = _opt(d, "flood_freq_s1.tif")
    # quality gate: ordinary cropland should not look flooded in most monsoon scenes; if it does, the radar
    # water threshold has picked up waterlogged paddy / wet soil and the layer is not trusted
    qa_max = d.cfg.get("availability", {}).get("s1_qa_max_cropland_flood", 0.3)
    if ff is not None and not np.isnan(ff).all():
        wc = read(d.interim / "worldcover_2021.tif")
        crop_med = float(np.nanmedian(ff[wc == 40])) if (wc == 40).any() else 0.0
        log.info("  S1 flood QA: median flood frequency on WorldCover cropland = %.2f (max %.2f)", crop_med, qa_max)
        (d.interim / "flood_qa.json").write_text(
            f'{{"s1_median_cropland_flood_freq": {crop_med:.3f}, "qa_max": {qa_max}, "s1_used": {str(crop_med <= qa_max).lower()}}}')
        if crop_med > qa_max:
            log.warning("  S1 flood layer failed QA; falling back to JRC/Esri flood proxy")
            ff = None
    if ff is None or np.isnan(ff).all():
        log.warning("  no Sentinel-1 flood layer; using JRC/Esri flood proxy")
        prox = np.zeros(g.shape, "float32")
        if occ is not None:
            prox = np.fmax(prox, np.nan_to_num(occ) / 100)
        yrs = sorted(d.interim.glob("esri_lulc_*.tif"))
        if yrs:
            wet = np.mean([np.isin(read(p), [1, 4]) for p in yrs], axis=0)
            prox = np.fmax(prox, wet.astype("float32"))
        ff = prox
    else:
        if occ is not None:  # remove permanent water from "flooding"
            ff = np.where(np.nan_to_num(occ) >= 90, 1.0, ff)
    save(g, ff, d.interim / "flood_freq.tif")
    log.info("[prep] slope, distances, protected mask, flood frequency written")


# ---------------------------------------------------------------- land status
def land_status(d: District) -> np.ndarray:
    g = load_grid(d)
    a = d.cfg["availability"]
    wc = read(d.interim / "worldcover_2021.tif")
    yrs = sorted(d.interim.glob("esri_lulc_*.tif"))
    esri = np.stack([read(p) for p in yrs]) if yrs else None
    occ = _opt(d, "jrc_occurrence.tif")
    pam = read(d.interim / "protected_mask.tif") == 1
    k = _opt(d, "ndvi_kharif_peak.tif")
    r = _opt(d, "ndvi_rabi_peak.tif")

    excl = np.isin(wc, [10, 50, 80, 90, 95]) | pam
    if occ is not None:
        excl |= np.nan_to_num(occ) >= a["permanent_water_occurrence"]
    if esri is not None:
        recent = esri[-3:]
        excl |= (recent == 7).any(0)                    # built in any recent year
        excl |= (recent == 2).all(0)                    # stable trees
        excl |= (recent == 1).all(0)                    # stable water
        # shifting river channels / sandbars: water in several of the yearly maps
        excl |= (esri == 1).sum(0) >= a.get("esri_water_years_exclude", 99)

    open_land = np.isin(wc, a.get("open_land_worldcover", [20, 30, 60, 100]))
    crop = wc == 40
    if esri is not None:
        latest = esri[-1]
        open_land |= np.isin(latest, a.get("open_land_esri", [8, 11])) & ~crop
        crop |= latest == 5
        ever_crop = (esri == 5).any(0)
        under = a.get("undercropped_esri_classes", [8, 11])
        recently_abandoned = (ever_crop | (wc == 40)) & np.isin(latest, under)
    else:
        recently_abandoned = np.zeros(g.shape, bool)

    st = np.full(g.shape, 4, "uint8")
    kk = np.nan_to_num(k, nan=1.0) if k is not None else np.ones(g.shape)
    rr = np.nan_to_num(r, nan=1.0) if r is not None else np.ones(g.shape)
    long_fallow = (crop & (kk < a["fallow_kharif_ndvi_max"])) | recently_abandoned
    rabi_fallow = crop & ~long_fallow & (rr < a["fallow_rabi_ndvi_max"])
    st[rabi_fallow] = 3
    st[open_land & ~crop] = 1
    st[long_fallow] = 2
    st[~(open_land | crop)] = 0
    st[excl] = 0
    st[~aoi_mask(d, g)] = 255
    save(g, st, d.interim / "land_status.tif", "uint8", 255)
    return st


# ---------------------------------------------------------------- factor scores
def factor_scores(d: District) -> dict[str, np.ndarray]:
    s = d.cfg["scoring"]
    i = d.interim
    soc, ph = read(i / "soil_soc_0-30.tif"), read(i / "soil_phh2o_0-30.tif")
    n, cec = read(i / "soil_nitrogen_0-30.tif"), read(i / "soil_cec_0-30.tif")
    clay = read(i / "soil_clay_0-30.tif")
    sw = s.get("soil_weights", {"ph": 0.25, "soc": 0.30, "nitrogen": 0.15, "cec": 0.15, "clay": 0.15})
    soil = (sw["soc"] * ramp(soc, *s["soc_gkg"]) + sw["ph"] * trapezoid(ph, s["ph_limits"], s["ph_optimum"])
            + sw["nitrogen"] * ramp(n, *s["nitrogen_gkg"]) + sw["cec"] * ramp(cec, *s["cec_cmolkg"])
            + sw["clay"] * trapezoid(clay, s["clay_limits"], s["clay_optimum"])) / sum(sw.values())
    rain = _opt(d, "rain_annual_mm.tif")
    if rain is None:
        rain_s = 1.0  # Assam rainfall is rarely limiting
    elif "rain_optimum" in s:
        rain_s = trapezoid(rain, s["rain_limits"], s["rain_optimum"])
    else:
        rain_s = ramp(rain, *s["rain_mm"])
    dw = read(i / "dist_water_m.tif")
    dw_s = ramp(dw, s["dist_water_m"][1], s["dist_water_m"][0])
    water = 0.4 * rain_s + 0.6 * np.where(np.isnan(dw_s), 0.5, dw_s)
    ff = read(i / "flood_freq.tif")
    flood = ramp(ff, s["flood_freq"][1], s["flood_freq"][0])
    slope = read(i / "slope_pct.tif")
    terrain = ramp(slope, s["slope_pct"][1], s["slope_pct"][0])
    k, r = _opt(d, "ndvi_kharif_peak.tif"), _opt(d, "ndvi_rabi_peak.tif")
    peak = np.fmax(k, r) if k is not None and r is not None else (k if k is not None else r)
    productivity = ramp(peak, *s["ndvi_peak"]) if peak is not None else np.full(slope.shape, 0.5)
    dr, dt_ = read(i / "dist_road_m.tif"), read(i / "dist_town_m.tif")
    ra = ramp(dr, s["dist_road_m"][1], s["dist_road_m"][0])
    ta = ramp(dt_, s["dist_town_m"][1], s["dist_town_m"][0])
    access = 0.6 * np.where(np.isnan(ra), 0.5, ra) + 0.4 * np.where(np.isnan(ta), 0.5, ta)
    out = dict(soil=soil, water=water, flood=flood, terrain=terrain, productivity=productivity, access=access)
    # gap-fill coarse layers (soil/rain edges) with district median so one gap doesn't null a cell
    for kf, v in out.items():
        v = np.broadcast_to(np.asarray(v, "float32"), slope.shape)
        med = np.nanmedian(v) if np.isfinite(v).any() else 0.5
        out[kf] = np.where(np.isnan(v), med, v).astype("float32")
    return out


# ---------------------------------------------------------------- suitability
def suitability(d: District, profile: str):
    g = load_grid(d)
    prof = d.cfg["profiles"][profile]
    w = prof["weights"]
    st = read(d.interim / "land_status.tif")
    fs = factor_scores(d)
    stack = np.stack([fs[f] for f in FACTORS])
    wv = np.array([w[f] for f in FACTORS], "float32")[:, None, None]
    score = (stack * wv).sum(0) / wv.sum() * 100

    slope = read(d.interim / "slope_pct.tif")
    ff = read(d.interim / "flood_freq.tif")
    constrained = (slope > prof["max_slope_pct"]) | (np.nan_to_num(ff) > prof["max_flood_freq"])
    c = d.cfg["classes"]
    cls = np.select([score >= c["S1"], score >= c["S2"], score >= c["S3"]], [1, 2, 3], 4).astype("uint8")
    weakest = stack.min(0) * 100
    if "cap_S2_if_any_factor_below" in c:
        cls = np.where((weakest < c["cap_S2_if_any_factor_below"]) & (cls == 1), 2, cls).astype("uint8")
    if "cap_S3_if_any_factor_below" in c:
        cls = np.where((weakest < c["cap_S3_if_any_factor_below"]) & (cls < 3), 3, cls).astype("uint8")
    cls[constrained] = 5
    outside = np.isnan(st) | (st == 255)
    score[outside] = np.nan
    cls[outside] = 0

    # reasons: weighted shortfall decides the limiting factor; weighted strength the contributing one
    shortfall = (1 - stack) * wv
    strength = stack * wv
    limiting = (np.argmax(shortfall, 0) + 1).astype("uint8")
    contributing = (np.argmax(strength, 0) + 1).astype("uint8")
    limiting[constrained & (slope > prof["max_slope_pct"])] = FACTORS.index("terrain") + 1
    limiting[constrained & (np.nan_to_num(ff) > prof["max_flood_freq"])] = FACTORS.index("flood") + 1
    limiting[outside] = 0
    contributing[outside] = 0

    od = d.out / profile / "maps"
    save(g, score, od / "suitability_score.tif")
    save(g, cls, od / "suitability_class.tif", "uint8", 0)
    save(g, limiting, od / "limiting_factor.tif", "uint8", 0)
    save(g, contributing, od / "contributing_factor.tif", "uint8", 0)
    fac = (stack * 100).round()
    fac[:, outside] = 255
    save(g, fac, od / "factor_scores.tif", "uint8", 255, descriptions=FACTORS)
    save(g, np.where(outside, 255, st), od / "land_status.tif", "uint8", 255)
    log.info("[model] %s/%s: score mean %.1f on candidate land", d.key, profile,
             np.nanmean(score[np.isin(st, CANDIDATE)]) if np.isin(st, CANDIDATE).any() else float("nan"))
    return dict(score=score, cls=cls, limiting=limiting, contributing=contributing, stack=stack, status=st)


def reason_text(cls: int, factors: dict, limiting: str, contributing: str) -> str:
    good = [FACTOR_LABEL[f] for f, v in sorted(factors.items(), key=lambda x: -x[1]) if v >= 70][:2]
    weak = [FACTOR_LABEL[f] for f, v in sorted(factors.items(), key=lambda x: x[1]) if v < 50][:2]
    s = CLASS_NAMES.get(cls, "")
    parts = [s + "."]
    if good:
        parts.append("Strong: " + ", ".join(good) + ".")
    if weak:
        parts.append("Weak: " + ", ".join(weak) + ".")
    parts.append(f"Main limitation: {FACTOR_LABEL.get(limiting, limiting)}.")
    return " ".join(parts)
