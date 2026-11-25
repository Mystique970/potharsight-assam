"""Static figures (PNG) and a markdown summary per district/profile."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from .core import District, load_grid
from .model import CLASS_NAMES, STATUS

CLASS_COL = {1: "#1a9850", 2: "#91cf60", 3: "#fee08b", 4: "#d9d9d9", 5: "#bdbdbd"}
STATUS_COL = {0: "#f0f0f0", 1: "#e6a032", 2: "#c2523c", 3: "#f2d16b", 4: "#7fb77e"}


def _extent(g):
    b = g.bounds()
    return [b[0], b[2], b[1], b[3]]


def _base(d, ax):
    d.boundary("blocks").boundary.plot(ax=ax, color="#555", lw=0.4)
    d.boundary().boundary.plot(ax=ax, color="black", lw=1.0)
    ax.set_axis_off()


def figures(d: District, profile: str, res: dict, patches: gpd.GeoDataFrame):
    g = load_grid(d)
    fd = d.out / profile / "figures"
    fd.mkdir(parents=True, exist_ok=True)
    ext = _extent(g)
    title = f"{d.dcfg['boundary_name']} — {d.cfg['profiles'][profile]['label']}"

    cls = res["cls"].astype(float)
    cls[cls == 0] = np.nan
    cls[~np.isin(res["status"], [1, 2, 3])] = np.nan
    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    ax.imshow(cls, cmap=ListedColormap([CLASS_COL[i] for i in range(1, 6)]), vmin=0.5, vmax=5.5,
              extent=ext, interpolation="nearest")
    _base(d, ax)
    ax.legend(handles=[Patch(color=CLASS_COL[i], label=CLASS_NAMES[i]) for i in range(1, 6)],
              loc="lower left", fontsize=8, frameon=True)
    ax.set_title(f"Suitability of available land\n{title}", fontsize=11)
    fig.savefig(fd / "suitability_class.png", bbox_inches="tight")
    plt.close(fig)

    st = res["status"].astype(float)
    st[st == 255] = np.nan
    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    ax.imshow(st, cmap=ListedColormap([STATUS_COL[i] for i in range(5)]), vmin=-0.5, vmax=4.5,
              extent=ext, interpolation="nearest")
    _base(d, ax)
    ax.legend(handles=[Patch(color=STATUS_COL[i], label=STATUS[i]) for i in range(5)],
              loc="lower left", fontsize=7.5)
    ax.set_title(f"Land availability status — {d.dcfg['boundary_name']}", fontsize=11)
    fig.savefig(fd / "land_status.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 8), dpi=150)
    im = ax.imshow(res["score"], cmap="RdYlGn", vmin=20, vmax=90, extent=ext)
    _base(d, ax)
    fig.colorbar(im, ax=ax, shrink=0.6, label="Suitability score (0-100)")
    ax.set_title(f"Biophysical suitability score\n{title}", fontsize=11)
    fig.savefig(fd / "suitability_score.png", bbox_inches="tight")
    plt.close(fig)

    br = pd.read_csv(d.out / profile / "tables" / "blocks_ranking.csv").head(15)
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    ax.barh(br.name[::-1], br.S1_ha[::-1], color=CLASS_COL[1], label="S1 ha")
    ax.barh(br.name[::-1], br.S2_ha[::-1], left=br.S1_ha[::-1], color=CLASS_COL[2], label="S2 ha")
    ax.set_xlabel("Hectares of available land")
    ax.set_title(f"Blocks ranked by priority index — {d.dcfg['boundary_name']}", fontsize=11)
    ax.legend()
    fig.savefig(fd / "block_ranking.png", bbox_inches="tight")
    plt.close(fig)


def web_overlay(d: District, profile: str, res: dict):
    """RGBA PNG of the class map in EPSG:4326 + bounds, for the dashboard."""
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    g = load_grid(d)
    cls = res["cls"].copy()
    cls[~np.isin(res["status"], [1, 2, 3])] = 0
    tr, w, h = calculate_default_transform(g.crs, "EPSG:4326", g.width, g.height, *g.bounds())
    dst = np.zeros((h, w), "uint8")
    reproject(cls, dst, src_transform=g.transform, src_crs=g.crs, dst_transform=tr, dst_crs="EPSG:4326",
              resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    rgba = np.zeros((h, w, 4), "uint8")
    for k, hexc in CLASS_COL.items():
        rgb = [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]
        rgba[dst == k] = rgb + [200]
    fd = d.out / profile / "figures"
    plt.imsave(fd / "overlay_class_4326.png", rgba)
    west, north = tr.c, tr.f
    east, south = west + tr.a * w, north + tr.e * h
    (fd / "overlay_bounds.json").write_text(json.dumps([[south, west], [north, east]]))


def summary(d: District, profile: str, patches: gpd.GeoDataFrame):
    od = d.out / profile
    v = json.loads((od / "tables" / "validation.json").read_text())
    br = pd.read_csv(od / "tables" / "blocks_ranking.csv")
    lines = [f"# {d.dcfg['boundary_name']} — {d.cfg['profiles'][profile]['label']}", "",
             f"- Candidate land (vacant + long fallow): {v['model_vacant_plus_long_fallow_ha']:,} ha "
             f"(official DES 2020-21: {v.get('official_vacant_cultivable_ha') or 'n/a'} ha, "
             f"ratio {v.get('ratio_model_to_official', 'n/a')})",
             f"- Incl. rabi-fallow cropland: {v['model_all_candidate_incl_rabi_fallow_ha']:,} ha",
             f"- Priority patches (S1/S2, >= {d.cfg['availability']['min_patch_ha']} ha): {len(patches)}, "
             f"{patches.area_ha.sum():,.0f} ha" if len(patches) else "- No priority patches",
             f"- Weight sensitivity: min Spearman rho {v['sensitivity_min_rho']}, "
             f"mean top-5 block overlap {v['sensitivity_mean_top5_overlap']}/5", "",
             "## Top blocks", "", br.head(10)[["rank", "name", "S1_ha", "S2_ha", "mean_score", "main_limitation"]]
             .to_markdown(index=False), ""]
    if len(patches):
        lines += ["## Top 10 patches", "", patches.head(10)[["rank_district", "block", "area_ha", "mean_score",
                                                             "status_name", "reason"]].to_markdown(index=False)]
    (od / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
