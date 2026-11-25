"""Priority patches (parcel proxy) and block / revenue-circle prioritisation."""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio import features
from scipy import ndimage
from shapely.geometry import shape

from .core import District, load_grid, log
from .model import CANDIDATE, CLASS_NAMES, FACTOR_LABEL, FACTORS, STATUS, reason_text


def _units(d: District, g, level: str):
    u = d.boundary(level)
    u = u.reset_index(drop=True)
    u["uid"] = np.arange(1, len(u) + 1)
    ras = features.rasterize(zip(u.geometry, u.uid), out_shape=g.shape, transform=g.transform,
                             fill=0, dtype="int32")
    return u, ras


def patches(d: District, profile: str, res: dict) -> gpd.GeoDataFrame:
    g = load_grid(d)
    pix_ha = g.res * g.res / 1e4
    st, cls, score, stack, lim = res["status"], res["cls"], res["score"], res["stack"], res["limiting"]
    cand = np.isin(st, CANDIDATE) & np.isin(cls, [1, 2])
    lab, n = ndimage.label(cand, structure=np.ones((3, 3)))
    if n == 0:
        log.warning("[rank] no S1/S2 candidate patches")
        return gpd.GeoDataFrame()
    idx = np.arange(1, n + 1)
    npx = ndimage.sum(cand, lab, idx)
    keep = idx[npx * pix_ha >= d.cfg["availability"]["min_patch_ha"]]
    lab = np.where(np.isin(lab, keep), lab, 0)
    idx = keep
    df = pd.DataFrame({"pid": idx})
    df["area_ha"] = ndimage.sum(lab > 0, lab, idx) * pix_ha
    df["mean_score"] = ndimage.mean(np.nan_to_num(score), lab, idx)
    for k, f in enumerate(FACTORS):
        df[f"f_{f}"] = ndimage.mean(stack[k] * 100, lab, idx)
    df["share_S1"] = ndimage.mean(cls == 1, lab, idx)
    for s in CANDIDATE:
        df[f"_st{s}"] = ndimage.sum(st == s, lab, idx)
    df["land_status"] = df[[f"_st{s}" for s in CANDIDATE]].values.argmax(1) + 1
    df = df.drop(columns=[f"_st{s}" for s in CANDIDATE])
    df["class"] = np.where(df.share_S1 >= 0.5, 1, 2)
    w = d.cfg["profiles"][profile]["weights"]
    df["limiting"] = [max(FACTORS, key=lambda f: (100 - r[f"f_{f}"]) * w[f]) for _, r in df.iterrows()]
    df["contributing"] = [max(FACTORS, key=lambda f: r[f"f_{f}"] * w[f]) for _, r in df.iterrows()]
    df["priority"] = 0.8 * df.mean_score + 20 * np.minimum(df.area_ha, 10) / 10
    df["class_name"] = df["class"].map(CLASS_NAMES)
    df["status_name"] = df.land_status.map(STATUS)
    df["reason"] = [reason_text(int(r["class"]), {f: r[f"f_{f}"] for f in FACTORS}, r.limiting, r.contributing)
                    for _, r in df.iterrows()]

    geoms = {}
    for geom, val in features.shapes(lab.astype("int32"), mask=lab > 0, transform=g.transform):
        geoms.setdefault(int(val), []).append(shape(geom))
    from shapely.ops import unary_union
    df["geometry"] = [unary_union(geoms[i]) for i in df.pid]
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=g.crs)

    for level, col in [("blocks", "block"), ("circles", "circle")]:
        u = d.boundary(level)[["name", "geometry"]].rename(columns={"name": col})
        pts = gdf[["pid", "geometry"]].copy()
        pts["geometry"] = gdf.representative_point()
        j = gpd.sjoin(pts, u, predicate="within", how="left").drop_duplicates("pid")
        gdf[col] = gdf.pid.map(j.set_index("pid")[col]).fillna("outside block layer")
    gdf["rank_district"] = gdf.priority.rank(ascending=False, method="first").astype(int)
    gdf["rank_in_block"] = gdf.groupby("block").priority.rank(ascending=False, method="first").astype(int)
    gdf = gdf.sort_values("rank_district")
    num = gdf.select_dtypes("number").columns
    gdf[num] = gdf[num].round(2)
    return gdf


def aggregate(d: District, profile: str, res: dict, level: str) -> gpd.GeoDataFrame:
    g = load_grid(d)
    pix_ha = g.res * g.res / 1e4
    u, ras = _units(d, g, level)
    st, cls, score, lim = res["status"], res["cls"], res["score"], res["limiting"]
    ids = u.uid.values
    cand = np.isin(st, CANDIDATE)
    out = u[["name", "geometry"]].copy()
    out["area_ha"] = ndimage.sum(ras > 0, ras, ids) * pix_ha
    out["candidate_ha"] = ndimage.sum(cand, ras, ids) * pix_ha
    for s, nm in [(1, "vacant_ha"), (2, "long_fallow_ha"), (3, "rabi_fallow_ha")]:
        out[nm] = ndimage.sum(st == s, ras, ids) * pix_ha
    for c, nm in [(1, "S1_ha"), (2, "S2_ha"), (3, "S3_ha")]:
        out[nm] = ndimage.sum(cand & (cls == c), ras, ids) * pix_ha
    out["constrained_ha"] = ndimage.sum(cand & (cls == 5), ras, ids) * pix_ha
    with np.errstate(all="ignore"):
        out["mean_score"] = ndimage.sum(np.where(cand, np.nan_to_num(score), 0), ras, ids) / np.maximum(
            ndimage.sum(cand, ras, ids), 1)
    dom = []
    for i in ids:
        m = (ras == i) & cand & (lim > 0)
        dom.append(FACTOR_LABEL[FACTORS[np.bincount(lim[m], minlength=7)[1:].argmax()]] if m.any() else "")
    out["main_limitation"] = dom
    out["priority_index"] = (out.S1_ha + 0.5 * out.S2_ha) * out.mean_score / 100
    out["rank"] = out.priority_index.rank(ascending=False, method="min").astype(int)
    out = out.sort_values("rank")
    num = out.select_dtypes("number").columns
    out[num] = out[num].round(1)
    return out


def run(d: District, profile: str, res: dict):
    od = d.out / profile
    (od / "vectors").mkdir(parents=True, exist_ok=True)
    (od / "tables").mkdir(parents=True, exist_ok=True)
    p = patches(d, profile, res)
    if len(p):
        p.to_file(od / "vectors" / "priority_patches.gpkg", driver="GPKG")
        p.to_crs(4326).to_file(od / "vectors" / "priority_patches.geojson", driver="GeoJSON")
        (od / "vectors" / "shp").mkdir(exist_ok=True)
        p.rename(columns=lambda c: c[:10]).to_file(od / "vectors" / "shp" / "priority_patches.shp")
        p.drop(columns="geometry").to_csv(od / "tables" / "priority_patches.csv", index=False)
    for level in ["blocks", "circles"]:
        a = aggregate(d, profile, res, level)
        a.to_file(od / "vectors" / f"{level}_ranking.gpkg", driver="GPKG")
        a.to_crs(4326).to_file(od / "vectors" / f"{level}_ranking.geojson", driver="GeoJSON")
        a.drop(columns="geometry").to_csv(od / "tables" / f"{level}_ranking.csv", index=False)
    log.info("[rank] %s/%s: %d priority patches, %.0f ha", d.key, profile, len(p),
             p.area_ha.sum() if len(p) else 0)
    return p
