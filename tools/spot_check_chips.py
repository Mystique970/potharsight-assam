"""Visual spot-check: draw a stratified random sample of priority patches over Esri World Imagery.

python tools/spot_check_chips.py kamrup field_crops 30
Writes outputs/<district>/<profile>/spot_check/chip_XX.png, a contact sheet and sample.csv
(column `verdict` is filled in after visual review).
"""
import io
import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
Z = 16


def deg2px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def chip(geom, size=768):
    c = geom.centroid
    cx, cy = deg2px(c.y, c.x, Z)
    x0, y0 = cx - size / 2, cy - size / 2
    img = Image.new("RGB", (size, size))
    s = requests.Session()
    s.headers["User-Agent"] = "d13-spot-check"
    for tx in range(int(x0 // 256), int((x0 + size) // 256) + 1):
        for ty in range(int(y0 // 256), int((y0 + size) // 256) + 1):
            try:
                r = s.get(TILE.format(z=Z, x=tx, y=ty), timeout=20)
                t = Image.open(io.BytesIO(r.content)).convert("RGB")
                img.paste(t, (int(tx * 256 - x0), int(ty * 256 - y0)))
            except Exception:
                pass
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    rings = []
    for p in polys:
        xy = [deg2px(lat, lon, Z) for lon, lat in p.exterior.coords]
        rings.append([(x - x0, y - y0) for x, y in xy])
    return img, rings


def main(dkey, profile, n):
    P = ROOT / "outputs" / dkey / profile
    g = gpd.read_file(P / "vectors" / "priority_patches.gpkg").to_crs(4326)
    rng = np.random.default_rng(42)
    # stratify by land status so vacant, long-fallow and rabi-fallow patches are all represented
    parts = []
    for stt, grp in g.groupby("land_status"):
        k = max(1, round(n * len(grp) / len(g)))
        parts.append(grp.sample(min(k, len(grp)), random_state=int(rng.integers(1e6))))
    s = gpd.GeoDataFrame(np.concatenate([p.values for p in parts]), columns=g.columns, geometry="geometry", crs=4326)
    s = s.head(n).reset_index(drop=True)
    od = P / "spot_check"
    od.mkdir(exist_ok=True)
    cols = 5
    rows = math.ceil(len(s) / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(cols * 4.2, rows * 4.75))
    for i, r in s.iterrows():
        img, rings = chip(r.geometry)
        f2, a2 = plt.subplots(figsize=(6, 6))
        for a in (axs.flat[i], a2):
            a.imshow(img)
            for ring in rings:
                xs, ys = zip(*ring)
                a.plot(xs, ys, color="#ff00ff", lw=1.2)
            a.set_axis_off()
        st = {1: "vacant", 2: "long fallow", 3: "rabi fallow"}[int(r.land_status)]
        axs.flat[i].set_title(f"#{i + 1}  {r.block}\n{st} · {r.area_ha:.1f} ha · score {r.mean_score:.0f}",
                              fontsize=12, pad=6)
        a2.set_title(f"#{i + 1} {r.block} · {st} · {r.area_ha:.1f} ha · score {r.mean_score:.0f} · rank {r.rank_district}")
        f2.savefig(od / f"chip_{i + 1:02d}.png", dpi=80, bbox_inches="tight")
        plt.close(f2)
    for a in axs.flat[len(s):]:
        a.set_axis_off()
    fig.suptitle(f"Spot-check sample – {dkey.title()}, {profile.replace('_', ' ')}\n"
                 f"magenta outline = model priority patch · imagery: Esri World Imagery (zoom {Z}, ~800 m across)",
                 fontsize=16, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.965], h_pad=1.6)
    fig.savefig(od / "contact_sheet.png", dpi=110)
    c = s.geometry.representative_point()
    out = s.drop(columns="geometry")[["pid", "rank_district", "block", "land_status", "status_name", "area_ha", "mean_score", "class_name"]]
    out.insert(0, "chip", range(1, len(s) + 1))
    out["lat"], out["lon"] = c.y.round(5).values, c.x.round(5).values
    out["verdict"] = ""
    out["note"] = ""
    # keep verdicts from an earlier review of the same patches (docs/spot_check.csv is the master record)
    master = ROOT / "docs" / "spot_check.csv"
    if master.exists():
        prev = pd.read_csv(master)
        prev = prev[prev.district == dkey].set_index("pid")
        out["verdict"] = out.pid.map(prev["verdict"]).fillna("")
        out["note"] = out.pid.map(prev["note"]).fillna("")
    out["district"] = dkey
    out.to_csv(od / "sample.csv", index=False)
    print("wrote", od)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30)
